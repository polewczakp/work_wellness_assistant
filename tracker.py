from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from threading import Lock

from config import BREAK_FREE_MIN

@dataclass
class DayState:
    day: datetime.date
    start_ts: Optional[datetime] = None
    end_ts: Optional[datetime] = None
    work_effective: timedelta = timedelta(0)  # counts break portions up to BREAK_FREE_MIN
    break_total: timedelta = timedelta(0)
    absence_total: timedelta = timedelta(0)   # break beyond BREAK_FREE_MIN and explicit absences

    # current sessions
    in_break: bool = False
    break_started: Optional[datetime] = None

    youtube_on: bool = False
    yt_started: Optional[datetime] = None

    # derived
    def minutes(self, td: timedelta) -> float:
        return td.total_seconds() / 60.0

    def snapshot(self):
        return {
            "work_minutes": round(self.minutes(self.work_effective), 1),
            "break_minutes": round(self.minutes(self.break_total), 1),
            "absence_minutes": round(self.minutes(self.absence_total), 1),
        }

class WorkTracker:
    """Thread-safe day tracker."""
    def __init__(self):
        today = datetime.now().date()
        self.state = DayState(day=today)
        self.lock = Lock()

    def _rollover_if_needed(self):
        now = datetime.now()
        if self.state.day != now.date():
            self.state = DayState(day=now.date())

    def start_work(self):
        with self.lock:
            self._rollover_if_needed()
            if not self.state.start_ts:
                self.state.start_ts = datetime.now()
            return self.state.snapshot()

    def end_work(self):
        with self.lock:
            self._rollover_if_needed()
            self._close_open_sessions()
            self.state.end_ts = datetime.now()
            return self.state.snapshot()

    def _close_open_sessions(self):
        now = datetime.now()
        # Close break
        if self.state.in_break and self.state.break_started:
            self._finish_break(now)
        # Close YouTube
        if self.state.youtube_on and self.state.yt_started:
            self._finish_youtube(now)

    def tick_active_minute(self):
        """Call every minute while user is active. Increase effective work by 1 minute minus ongoing break logic."""
        with self.lock:
            self._rollover_if_needed()
            if not self.state.start_ts:
                return self.state.snapshot()
            if not self.state.in_break and not self.state.youtube_on:
                self.state.work_effective += timedelta(minutes=1)
            return self.state.snapshot()

    # Generic break (idle, lock, manual)
    def break_start(self):
        with self.lock:
            if not self.state.in_break:
                self.state.in_break = True
                self.state.break_started = datetime.now()
            return self.state.snapshot()

    def break_end(self):
        with self.lock:
            if self.state.in_break and self.state.break_started:
                self._finish_break(datetime.now())
            return self.state.snapshot()

    def _finish_break(self, end: datetime):
        dur = end - self.state.break_started
        self.state.break_total += dur
        free = timedelta(minutes=BREAK_FREE_MIN)
        if dur > free:
            self.state.absence_total += (dur - free)
            self.state.work_effective += free  # only first 30 min counted as work
        else:
            self.state.work_effective += dur  # whole short break counts as work
        self.state.in_break = False
        self.state.break_started = None

    # YouTube treated as food break with same 30 min free rule, excess = absence
    def youtube_start(self):
        with self.lock:
            if not self.state.youtube_on:
                self.state.youtube_on = True
                self.state.yt_started = datetime.now()
            return self.state.snapshot()

    def youtube_stop(self):
        with self.lock:
            if self.state.youtube_on and self.state.yt_started:
                self._finish_youtube(datetime.now())
            return self.state.snapshot()

    def _finish_youtube(self, end: datetime):
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

    def get_status(self):
        with self.lock:
            self._rollover_if_needed()
            s = self.state
            return {
                "day": str(s.day),
                "started": s.start_ts.isoformat() if s.start_ts else None,
                "work_minutes": round(s.work_effective.total_seconds()/60, 1),
                "break_minutes": round(s.break_total.total_seconds()/60, 1),
                "absence_minutes": round(s.absence_total.total_seconds()/60, 1),
                "in_break": s.in_break,
                "youtube_on": s.youtube_on,
            }
