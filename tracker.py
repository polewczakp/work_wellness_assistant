from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock
from typing import Optional

from config import BREAK_FREE_MIN


@dataclass
class DayState:
    day: datetime.date
    start_ts: Optional[datetime] = None
    end_ts: Optional[datetime] = None
    work_effective: timedelta = timedelta(0)
    break_total: timedelta = timedelta(0)
    absence_total: timedelta = timedelta(0)
    in_break: bool = False
    break_started: Optional[datetime] = None
    youtube_on: bool = False
    yt_started: Optional[datetime] = None

    @staticmethod
    def _minutes(td: timedelta) -> float:
        return td.total_seconds() / 60.0

    def snapshot(self) -> dict:
        return {
            "work_minutes": round(self._minutes(self.work_effective), 1),
            "break_minutes": round(self._minutes(self.break_total), 1),
            "absence_minutes": round(self._minutes(self.absence_total), 1),
        }


class WorkTracker:
    """Per-day work accounting with break free portion logic."""

    def __init__(self) -> None:
        self.state = DayState(day=datetime.now().date())
        self._lock = Lock()

    def _rollover_if_needed(self) -> None:
        now = datetime.now().date()
        if self.state.day != now:
            self.state = DayState(day=now)

    def start_work(self) -> dict:
        with self._lock:
            self._rollover_if_needed()
            if not self.state.start_ts:
                self.state.start_ts = datetime.now()
            return self.state.snapshot()

    def end_work(self) -> dict:
        with self._lock:
            self._rollover_if_needed()
            self._close_open_sessions()
            self.state.end_ts = datetime.now()
            return self.state.snapshot()

    def _close_open_sessions(self) -> None:
        now = datetime.now()
        if self.state.in_break and self.state.break_started:
            self._finish_break(now)
        if self.state.youtube_on and self.state.yt_started:
            self._finish_youtube(now)

    def tick_active_minute(self) -> dict:
        with self._lock:
            self._rollover_if_needed()
            if not self.state.start_ts:
                return self.state.snapshot()
            if not self.state.in_break and not self.state.youtube_on:
                self.state.work_effective += timedelta(minutes=1)
            return self.state.snapshot()

    def break_start(self) -> dict:
        with self._lock:
            if not self.state.in_break:
                self.state.in_break = True
                self.state.break_started = datetime.now()
            return self.state.snapshot()

    def break_end(self) -> dict:
        with self._lock:
            if self.state.in_break and self.state.break_started:
                self._finish_break(datetime.now())
            return self.state.snapshot()

    def _finish_break(self, end: datetime) -> None:
        assert self.state.break_started is not None
        dur = end - self.state.break_started
        self.state.break_total += dur
        free = timedelta(minutes=BREAK_FREE_MIN)
        if dur > free:
            self.state.absence_total += (dur - free)
            self.state.work_effective += free
        else:
            self.state.work_effective += dur
        self.state.in_break = False
        self.state.break_started = None

    def youtube_start(self) -> dict:
        with self._lock:
            if not self.state.youtube_on:
                self.state.youtube_on = True
                self.state.yt_started = datetime.now()
            return self.state.snapshot()

    def youtube_stop(self) -> dict:
        with self._lock:
            if self.state.youtube_on and self.state.yt_started:
                self._finish_youtube(datetime.now())
            return self.state.snapshot()

    def _finish_youtube(self, end: datetime) -> None:
        assert self.state.yt_started is not None
        dur = end - self.state.yt_started
        free = timedelta(minutes=BREAK_FREE_MIN)
        if dur > free:
            self.state.absence_total += (dur - free)
            self.state.work_effective += free
        else:
            self.state.work_effective += dur
        self.state.break_total += dur
        self.state.youtube_on = False
        self.state.yt_started = None

    def get_status(self) -> dict:
        with self._lock:
            self._rollover_if_needed()
            s = self.state
            return {
                "day": str(s.day),
                "started": s.start_ts.isoformat() if s.start_ts else None,
                "work_minutes": round(s.work_effective.total_seconds() / 60, 1),
                "break_minutes": round(s.break_total.total_seconds() / 60, 1),
                "absence_minutes": round(s.absence_total.total_seconds() / 60, 1),
                "in_break": s.in_break,
                "youtube_on": s.youtube_on,
            }
