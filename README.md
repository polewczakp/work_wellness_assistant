# Work Wellness Assistant

Python agent + Tampermonkey bridge. Windows 11 native lock/unlock. Microsoft Graph
presence-based suppression during Teams calls (optional).

## Setup (Windows 11)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Install `userscript.user.js` into Tampermonkey. Open http://localhost:5600/panel

### Microsoft Teams presence (optional)
Set env var `GRAPH_TOKEN` with a token that has `Presence.Read` scope for your account.
If present, reminders are minimized during calls and revealed when the call ends.

### Logs
- `aktywnosc.xlsx` – events with accumulated minutes
- `popatrz_w_dal.xlsx` – look-far reactions

### Hotkeys
- Ctrl+Alt+B – start break
- Ctrl+Alt+N – end break
