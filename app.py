from __future__ import annotations
import threading

from datetime import datetime, timedelta
from typing import Optional

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from apscheduler.schedulers.background import BackgroundScheduler

from config import (
    SERVER_PORT,
    WORK_TARGET_MIN,
    EXTEND_BLOCK_MIN,
    LOOK_FAR_EVERY_MIN,
    STAND_UP_EVERY_MIN,
    STANDUP_RESET_IDLE_MIN,
)
from storage import log_activity
from tracker import WorkTracker
from notifier import LookFarWindow, StandUpWindow
from presence import in_call_via_graph

app = Flask(__name__, static_folder="templates")
CORS(app)
tracker = WorkTracker()

sched = BackgroundScheduler()
last_lookfar: Optional[datetime] = None
last_standup_prompt: Optional[datetime] = None
last_standup_reset: datetime = datetime.now()  # last time we consider the user "stood up"
end_target_min = WORK_TARGET_MIN  # can be extended by button

# Simple activity heuristic using keyboard/mouse events via pynput
from pynput import keyboard, mouse

last_input_ts = datetime.now()


def _on_input(_):
    global last_input_ts
    last_input_ts = datetime.now()


keyboard.Listener(on_press=_on_input).start()
mouse.Listener(on_move=_on_input, on_click=lambda *a, **k: _on_input(None)).start()


def minute_tick():
    """Runs every minute."""
    global last_lookfar, last_standup_prompt, last_standup_reset, end_target_min
    now = datetime.now()

    # Count active minute if any input within last 60s and no break
    if (now - last_input_ts) <= timedelta(seconds=60):
        tracker.tick_active_minute()
        # If we were in break, close it
        if tracker.state.in_break:
            tracker.break_end()
    else:
        # Start a generic break if not already in one
        tracker.break_start()

    # Heuristic: if in break for >= STANDUP_RESET_IDLE_MIN, treat as stood up
    if tracker.state.in_break and tracker.state.break_started:
        if (now - tracker.state.break_started) >= timedelta(minutes=STANDUP_RESET_IDLE_MIN):
            last_standup_reset = now

    _status = tracker.get_status()
    in_call = in_call_via_graph()

    # Look far popup every LOOK_FAR_EVERY_MIN
    if tracker.state.start_ts:
        need_look = (not last_lookfar) or ((now - last_lookfar) >= timedelta(minutes=LOOK_FAR_EVERY_MIN))
        if need_look:
            last_lookfar = now
            log_activity(event="lookfar_show",
                         details="",
                         work_min=_status["work_minutes"],
                         break_min=_status["break_minutes"],
                         absence_min=_status["absence_minutes"])
            if in_call:
                # show minimized and reveal after call ends
                LookFarWindow().show_and_log(minimized=True, reveal_when=lambda: not in_call_via_graph())
            else:
                LookFarWindow().show_and_log()

    # Stand up prompt if user hasn't stood up for STAND_UP_EVERY_MIN
    if tracker.state.start_ts:
        need_stand = (now - last_standup_reset) >= timedelta(minutes=STAND_UP_EVERY_MIN)
        if need_stand and (
                not last_standup_prompt or (now - last_standup_prompt) >= timedelta(minutes=STAND_UP_EVERY_MIN)):
            last_standup_prompt = now
            log_activity(event="standup_show",
                         details="",
                         work_min=_status["work_minutes"],
                         break_min=_status["break_minutes"],
                         absence_min=_status["absence_minutes"])
            if in_call:
                StandUpWindow().show_and_log(minimized=True, reveal_when=lambda: not in_call_via_graph())
            else:
                StandUpWindow().show_and_log()

    # End-of-day check
    worked = _status["work_minutes"]
    if tracker.state.start_ts and worked >= end_target_min:
        def _ask_extend(worked_val: float, break_val: float, absence_val: float):
            import tkinter as tk
            from tkinter import messagebox
            global end_target_min
            root = tk.Tk()
            root.withdraw()
            ans = messagebox.askyesno(
                title="Koniec pracy",
                message="Masz 8h pracy. Zakończyć na dziś? Kliknij 'Nie' aby wydłużyć o 15 minut.")
            if ans:
                log_activity(event="end_work",
                             details="auto by target",
                             work_min=worked_val,
                             break_min=break_val,
                             absence_min=absence_val)
                tracker.end_work()
            else:
                end_target_min += EXTEND_BLOCK_MIN
                log_activity(event="extend_day", details=f"+{EXTEND_BLOCK_MIN} min", work_min=worked_val,
                             break_min=break_val,
                             absence_min=absence_val)
            root.destroy()

        threading.Thread(target=_ask_extend, args=(worked, _status["break_minutes"], _status["absence_minutes"]),
                         daemon=True).start()


sched.add_job(minute_tick, "interval", minutes=1, next_run_time=datetime.now())
sched.start()


# ---- HTTP API ----

@app.get("/status")
def status():
    s = tracker.get_status()
    return jsonify({
        **s,
        "target_minutes": end_target_min,
        "remaining_minutes": max(0, round(end_target_min - s["work_minutes"], 1)),
    })


@app.post("/start")
def start_work():
    s = tracker.start_work()
    log_activity(event="start_work", details="manual", work_min=s["work_minutes"], break_min=s["break_minutes"],
                 absence_min=s["absence_minutes"])
    return jsonify({"ok": True})


@app.post("/end")
def end_work():
    s = tracker.end_work()
    log_activity(event="end_work", details="manual", work_min=s["work_minutes"], break_min=s["break_minutes"],
                 absence_min=s["absence_minutes"])
    return jsonify({"ok": True})


@app.post("/event")
def event():
    data = request.get_json(force=True, silent=True) or {}
    kind = data.get("type")
    if kind == "youtube_start":
        s = tracker.youtube_start()
        log_activity(event="youtube_start", details=data.get("url", ""), work_min=s["work_minutes"],
                     break_min=s["break_minutes"], absence_min=s["absence_minutes"])
    elif kind == "youtube_stop":
        s = tracker.youtube_stop()
        log_activity(event="youtube_stop", details=data.get("url", ""), work_min=s["work_minutes"],
                     break_min=s["break_minutes"], absence_min=s["absence_minutes"])
    elif kind == "break_start":
        s = tracker.break_start()
        log_activity(event="break_start", details=data.get("reason", ""), work_min=s["work_minutes"],
                     break_min=s["break_minutes"], absence_min=s["absence_minutes"])
    elif kind == "break_end":
        s = tracker.break_end()
        log_activity(event="break_end", details=data.get("reason", ""), work_min=s["work_minutes"],
                     break_min=s["break_minutes"], absence_min=s["absence_minutes"])
    return jsonify({"ok": True})


@app.get("/")
@app.get("/panel")
def panel():
    return send_from_directory("templates", "status.html")


if __name__ == "__main__":
    print(f"Starting server on http://localhost:{SERVER_PORT}")
    app.run(port=SERVER_PORT)
