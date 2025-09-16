from pathlib import Path
import os

# Desktop path detection
DESKTOP_DIR = Path(os.environ.get("DESKTOP_DIR", Path.home() / "Desktop")).expanduser()
DESKTOP_DIR.mkdir(parents=True, exist_ok=True)

# Files
ACTIVITY_XLSX = DESKTOP_DIR / "aktywnosc.xlsx"
LOOK_FAR_XLSX = DESKTOP_DIR / "popatrz_w_dal.xlsx"

# Time rules
WORK_TARGET_MIN = int(os.environ.get("WORK_TARGET_MIN", 480))  # 8h
EXTEND_BLOCK_MIN = int(os.environ.get("EXTEND_BLOCK_MIN", 15))
LOOK_FAR_EVERY_MIN = int(os.environ.get("LOOK_FAR_EVERY_MIN", 20))
LOOK_FAR_UNCLOSEABLE_S = int(os.environ.get("LOOK_FAR_UNCLOSEABLE_S", 20))
STAND_UP_EVERY_MIN = int(os.environ.get("STAND_UP_EVERY_MIN", 60))
BREAK_FREE_MIN = int(os.environ.get("BREAK_FREE_MIN", 30))  # break portion counted as work
STANDUP_RESET_IDLE_MIN = int(os.environ.get("STANDUP_RESET_IDLE_MIN", 2))  # minutes of idle that count as standing up

# Optional Microsoft Graph token for presence (suppress popups during calls)
GRAPH_TOKEN = os.environ.get("GRAPH_TOKEN", None)
GRAPH_PRESENCE_URL = "https://graph.microsoft.com/v1.0/me/presence"

SERVER_PORT = int(os.environ.get("SERVER_PORT", 5600))
