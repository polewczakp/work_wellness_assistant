from __future__ import annotations

from json import JSONDecodeError

import requests

from config import GRAPH_PRESENCE_URL, GRAPH_TOKEN


def in_call_via_graph() -> bool:
    """
    True if Microsoft Graph presence indicates a call or meeting.
    Requires GRAPH_TOKEN env var with Presence.Read permission.
    """
    token = GRAPH_TOKEN
    if not token:
        return False
    try:
        r = requests.get(
            GRAPH_PRESENCE_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=3,
        )
        if r.status_code != 200:
            return False
        data = r.json()
    except (requests.RequestException, JSONDecodeError):
        return False

    activity = str(data.get("activity", ""))
    return activity in {"InACall", "InAMeeting"}
