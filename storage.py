from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd

from config import ACTIVITY_XLSX, LOOK_FAR_XLSX

ACTIVITY_COLUMNS: List[str] = [
    "timestamp",
    "event",
    "details",
    "work_minutes_today",
    "break_minutes_today",
    "absence_minutes_today",
]

LOOKFAR_COLUMNS: List[str] = ["timestamp", "reaction_seconds", "comment"]


def _ensure_file(path: Path, columns: List[str]) -> None:
    if path.exists():
        return
    df = pd.DataFrame(columns=columns)
    df.to_excel(path, index=False)


def _append_row_xlsx(path: Path, columns: List[str], row: Dict) -> None:
    """Append a row to XLSX. If file is locked by Excel, write CSV sidecar."""
    _ensure_file(path, columns)
    try:
        old = pd.read_excel(path)
        new = pd.concat([old, pd.DataFrame([row])], ignore_index=True)
        new.to_excel(path, index=False)
    except (PermissionError, OSError):
        csv_path = path.with_suffix(".csv")
        pd.DataFrame([row]).to_csv(
            csv_path, mode="a", header=not csv_path.exists(), index=False
        )


def log_activity(event: str, details: str, work_min: float, break_min: float, absence_min: float) -> None:
    """
    event: start_work, end_work, lock, unlock, youtube_start, youtube_stop,
            break_start, break_end, lookfar_show, lookfar_close,
            standup_show, standup_close, extend_day
    """
    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "event": event,
        "details": details,
        "work_minutes_today": round(work_min, 1),
        "break_minutes_today": round(break_min, 1),
        "absence_minutes_today": round(absence_min, 1),
    }
    _append_row_xlsx(ACTIVITY_XLSX, ACTIVITY_COLUMNS, row)


def log_lookfar(reaction_seconds: float, comment: str) -> None:
    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "reaction_seconds": round(reaction_seconds, 1),
        "comment": comment,
    }
    _append_row_xlsx(LOOK_FAR_XLSX, LOOKFAR_COLUMNS, row)
