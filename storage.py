from __future__ import annotations
from pathlib import Path
from datetime import datetime
import pandas as pd
from config import ACTIVITY_XLSX, LOOK_FAR_XLSX

ACTIVITY_COLUMNS = [
    "timestamp",  # ISO
    "event",
    "details",  # free text
    "work_minutes_today",
    "break_minutes_today",
    "absence_minutes_today",
]

LOOKFAR_COLUMNS = ["timestamp", "reaction_seconds", "comment"]


def _init_if_missing(path: Path, columns: list[str]):
    if not path.exists():
        df = pd.DataFrame(columns=columns)
        df.to_excel(path, index=False)


#
def log_activity(event: str, details: str, work_min: float, break_min: float, absence_min: float):
    """
    event: start_work, end_work, lock, unlock, youtube_start, youtube_stop,
            break_start, break_end, lookfar_show, lookfar_close,
            standup_show, standup_close, extend_day
    """
    _init_if_missing(ACTIVITY_XLSX, ACTIVITY_COLUMNS)
    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "event": event,
        "details": details,
        "work_minutes_today": round(work_min, 1),
        "break_minutes_today": round(break_min, 1),
        "absence_minutes_today": round(absence_min, 1),
    }
    try:
        old = pd.read_excel(ACTIVITY_XLSX)
        new = pd.concat([old, pd.DataFrame([row])], ignore_index=True)
        new.to_excel(ACTIVITY_XLSX, index=False)
    except Exception:
        # Fallback to CSV next to xlsx if file is locked by Excel
        csv_path = ACTIVITY_XLSX.with_suffix('.csv')
        pd.DataFrame([row]).to_csv(csv_path, mode='a', header=not csv_path.exists(), index=False)


def log_lookfar(reaction_seconds: float, comment: str):
    _init_if_missing(LOOK_FAR_XLSX, LOOKFAR_COLUMNS)
    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "reaction_seconds": round(reaction_seconds, 1),
        "comment": comment,
    }
    try:
        old = pd.read_excel(LOOK_FAR_XLSX)
        new = pd.concat([old, pd.DataFrame([row])], ignore_index=True)
        new.to_excel(LOOK_FAR_XLSX, index=False)
    except Exception:
        csv_path = LOOK_FAR_XLSX.with_suffix('.csv')
        pd.DataFrame([row]).to_csv(csv_path, mode='a', header=not csv_path.exists(), index=False)
