# Work Wellness Assistant

Lokalny agent Python + skrypt Tampermonkey do higieny pracy wzrok/kręgosłup i rozliczania 8h.

## Szybki start

```bash
python -m venv .venv
# Linux/macOS
. .venv/bin/activate
# Windows (PowerShell)
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
python app.py
```

Otwórz `userscript.user.js` w przeglądarce i zainstaluj w Tampermonkey.

Panel: http://localhost:5600/panel

Pliki logów: `aktywnosc.xlsx` i `popatrz_w_dal.xlsx` na Pulpicie.

## Konfiguracja
Zmienne w `config.py` lub przez env:
- `DESKTOP_DIR` – ścieżka Pulpitu (domyślnie `~/Desktop`)
- `WORK_TARGET_MIN` – domyślnie 480
- `EXTEND_BLOCK_MIN` – domyślnie 15
- `LOOK_FAR_EVERY_MIN` – domyślnie 20
- `LOOK_FAR_UNCLOSEABLE_S` – domyślnie 20
- `STAND_UP_EVERY_MIN` – domyślnie 60
- `STANDUP_RESET_IDLE_MIN` – domyślnie 2 (uznajemy ≥2 min bezczynności jako „wstanie”)
- `GRAPH_TOKEN` – opcjonalny token Microsoft Graph Presence (Presence.Read)
