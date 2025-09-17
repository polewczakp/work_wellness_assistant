from __future__ import annotations

import sys
import threading
from datetime import datetime, timedelta
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, request, send_from_directory
from flask_cors import CORS
from pynput import keyboard, mouse

from config import (
    EXTEND_BLOCK_MIN,
    LOOK_FAR_EVERY_MIN,
    SERVER_PORT,
    STAND_UP_EVERY_MIN,
    STANDUP_RESET_IDLE_MIN,
    WORK_TARGET_MIN,
)
from notifier import LookFarWindow, StandUpWindow
from presence import in_call_via_graph
from storage import log_activity
from tracker import WorkTracker
from windows_lock import start_windows_session_monitor

app = Flask(__name__, static_folder="templates")
CORS(app)
tracker = WorkTracker()

sched = BackgroundScheduler()
last_lookfar: Optional[datetime] = None
last_standup_prompt: Optional[datetime] = None
last_standup_reset: datetime = datetime.now()
end_target_min = WORK_TARGET_MIN

last_input_ts = datetime.now()


def _on_any_input(_=None) -> None:
    global last_input_ts
    last_input_ts = datetime.now()


keyboard.Listener(on_press=_on_any_input).start()
mouse.Listener(on_move=_on_any_input, on_click=lambda *a, **k: _on_any_input()).start()


def _handle_lock() -> None:
    s = tracker.break_start()
    log_activity(
        "lock",
        details="windows",
        work_min=s["work_minutes"],
        break_min=s["break_minutes"],
        absence_min=s["absence_minutes"],
    )


def _handle_unlock() -> None:
    s = tracker.break_end()
    log_activity(
        "unlock",
        details="windows",
        work_min=s["work_minutes"],
        break_min=s["break_minutes"],
        absence_min=s["absence_minutes"],
    )


if sys.platform == "win32":
    start_windows_session_monitor(on_lock=_handle_lock, on_unlock=_handle_unlock)


def minute_tick() -> None:
    """Runs every minute."""
    global last_lookfar, last_standup_prompt, last_standup_reset, end_target_min
    now = datetime.now()

    # Count active minute if any input within last 60s and no break
    if (now - last_input_ts) <= timedelta(seconds=60):
        tracker.tick_active_minute()
        if tracker.state.in_break:
            tracker.break_end()
    else:
        tracker.break_start()

    # Heuristic: if in break for >= STANDUP_RESET_IDLE_MIN, treat as stood up
    if tracker.state.in_break and tracker.state.break_started:
        if (now - tracker.state.break_started) >= timedelta(
            minutes=STANDUP_RESET_IDLE_MIN
        ):
            last_standup_reset = now

    status = tracker.get_status()
    in_call = in_call_via_graph()

    # Look far
    if tracker.state.start_ts:
        due_look = (not last_lookfar) or (
            (now - last_lookfar) >= timedelta(minutes=LOOK_FAR_EVERY_MIN)
        )
        if due_look:
            last_lookfar = now
            log_activity(
                "lookfar_show",
                details="",
                work_min=status["work_minutes"],
                break_min=status["break_minutes"],
                absence_min=status["absence_minutes"],
            )
            if in_call:
                LookFarWindow().show_and_log(
                    minimized=True, reveal_when=lambda: not in_call_via_graph()
                )
            else:
                LookFarWindow().show_and_log()

    # Stand up
    if tracker.state.start_ts:
        need_stand = (now - last_standup_reset) >= timedelta(
            minutes=STAND_UP_EVERY_MIN
        )
        if need_stand and (
            not last_standup_prompt
            or (now - last_standup_prompt) >= timedelta(minutes=STAND_UP_EVERY_MIN)
        ):
            last_standup_prompt = now
            log_activity(
                "standup_show",
                details="",
                work_min=status["work_minutes"],
                break_min=status["break_minutes"],
                absence_min=status["absence_minutes"],
            )
            if in_call:
                StandUpWindow().show_and_log(
                    minimized=True, reveal_when=lambda: not in_call_via_graph()
                )
            else:
                StandUpWindow().show_and_log()

    # End-of-day
    worked = status["work_minutes"]
    if tracker.state.start_ts and worked >= end_target_min:
        def _ask_extend(
            worked_val: float, break_val: float, absence_val: float
        ) -> None:
            import tkinter as tk
            from tkinter import messagebox

            nonlocal end_target_min
            root = tk.Tk(); root.withdraw()
            yes = messagebox.askyesno(
                title="Koniec pracy",
                message=(
                    "Masz 8h pracy. Zakończyć na dziś? "
                    "Kliknij 'Nie' aby wydłużyć o 15 minut."
                ),
            )
            if yes:
                log_activity(
                    "end_work",
                    details="auto by target",
                    work_min=worked_val,
                    break_min=break_val,
                    absence_min=absence_val,
                )
                tracker.end_work()
            else:
                end_target_min += EXTEND_BLOCK_MIN
                log_activity(
                    "extend_day",
                    details=f"+{EXTEND_BLOCK_MIN} min",
                    work_min=worked_val,
                    break_min=break_val,
                    absence_min=absence_val,
                )
            root.destroy()

        threading.Thread(
            target=_ask_extend,
            args=(worked, status["break_minutes"], status["absence_minutes"]),
            daemon=True,
        ).start()


sched.add_job(minute_tick, "interval", minutes=1, next_run_time=datetime.now())
sched.start()


# ---- HTTP API ----

@app.get("/status")
def status() -> tuple[dict, int]:
    s = tracker.get_status()
    return (
        {
            **s,
            "target_minutes": end_target_min,
            "remaining_minutes": max(0, round(end_target_min - s["work_minutes"], 1)),
        },
        200,
    )


@app.post("/start")
def start_work() -> tuple[dict, int]:
    s = tracker.start_work()
    log_activity(
        "start_work",
        details="manual",
        work_min=s["work_minutes"],
        break_min=s["break_minutes"],
        absence_min=s["absence_minutes"],
    )
    return {"ok": True}, 200


@app.post("/end")
def end_work() -> tuple[dict, int]:
    s = tracker.end_work()
    log_activity(
        "end_work",
        details="manual",
        work_min=s["work_minutes"],
        break_min=s["break_minutes"],
        absence_min=s["absence_minutes"],
    )
    return {"ok": True}, 200


@app.post("/event")
def event() -> tuple[dict, int]:
    data = request.get_json(force=True, silent=True) or {}
    kind = data.get("type")
    if kind == "youtube_start":
        s = tracker.youtube_start()
        log_activity(
            "youtube_start",
            details=data.get("url", ""),
            work_min=s["work_minutes"],
            break_min=s["break_minutes"],
            absence_min=s["absence_minutes"],
        )
    elif kind == "youtube_stop":
        s = tracker.youtube_stop()
        log_activity(
            "youtube_stop",
            details=data.get("url", ""),
            work_min=s["work_minutes"],
            break_min=s["break_minutes"],
            absence_min=s["absence_minutes"],
        )
    elif kind == "break_start":
        s = tracker.break_start()
        log_activity(
            "break_start",
            details=data.get("reason", ""),
            work_min=s["work_minutes"],
            break_min=s["break_minutes"],
            absence_min=s["absence_minutes"],
        )
    elif kind == "break_end":
        s = tracker.break_end()
        log_activity(
            "break_end",
            details=data.get("reason", ""),
            work_min=s["work_minutes"],
            break_min=s["break_minutes"],
            absence_min=s["absence_minutes"],
        )
    return {"ok": True}, 200


@app.get("/")
@app.get("/panel")
def panel():
    return send_from_directory("templates", "status.html")


if __name__ == "__main__":
    print(f"Starting server on http://localhost:{SERVER_PORT}")
    app.run(port=SERVER_PORT)
