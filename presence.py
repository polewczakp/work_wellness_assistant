import requests
from config import GRAPH_TOKEN, GRAPH_PRESENCE_URL


def in_call_via_graph() -> bool:
    """Return True if Graph presence indicates a call/meeting, else False.
    Requires GRAPH_TOKEN env var with Presence.Read permission."""
    if not GRAPH_TOKEN:
        return False
    try:
        r = requests.get(GRAPH_PRESENCE_URL, headers={"Authorization": f"Bearer {GRAPH_TOKEN}"}, timeout=3)
        if r.status_code == 200:
            data = r.json()
            activity = str(data.get("activity", ""))
            return activity in {"InACall", "InAMeeting"}
    except Exception:
        return False
    return False
