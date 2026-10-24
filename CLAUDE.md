# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
# Active version (monolithic, v1.3)
python confere.py

# Refactored version (MVC, build_IA/)
python build_IA/main.py

# WebApp version (FastAPI + SPA)
./run_web.sh
# ou:
.venv/bin/uvicorn web.main:app --port 8000 --reload

# Generate fake data for testing
python fake_data.py
```

## Architecture

Three implementations exist:

**`confere.py`** — single-file monolith (v1.3, currently active). `App(tk.Tk)` does everything: UI layout, search logic, CSV I/O, history. Easier to run, harder to extend.

**`build_IA/`** — MVC refactor (Tkinter):
- `repository.py` — `Repository`: CSV load/save (atomic write via `tempfile`+`shutil.move`), in-memory dict `{placa: [detalhes, status, timestamp, expires_at]}`, soft-delete (status `"excluido"`).
- `app.py` — `App`: controller, holds business logic and validation, event handlers called by UI, drives `Repository`.
- `ui.py` / `ui/` — `UI(tk.Tk)`: pure presentation with tabs (Search, Add, History, Config).
- `main.py` — entry point only.

**`web/`** — Modern WebApp (FastAPI + SPA):
- `web/main.py` — FastAPI application and static files mount.
- `web/repository.py` — Thread-safe atomic CSV operations, search, and temporary plate validation.
- `web/auth.py` — RBAC (Admin vs Operador/Portaria), password hashing (PBKDF2-SHA256) and session tokens.
- `web/chat_manager.py` — Real-time WebSocket connection hub, online user presence, chat history persistence, and plate event broadcasts.
- `web/routes/` — REST & WebSocket routers (`auth_routes.py`, `plate_routes.py`, `config_routes.py`, `chat_routes.py`).
- `web/static/` — Single Page Application (HTML5, responsive CSS, vanilla JS with real-time search, Web Audio alerts, floating chat drawer, and expiration badges).

## Data model

CSV format (semicolon-delimited, no header):
```
PLACA;detalhes;status;timestamp_iso;expires_at;cor;modelo
```

Backward compatibility:
- Files with 3, 4, or 5 columns (legacy) load seamlessly without errors (missing fields default to empty strings).
- Older implementations (`confere.py`, `build_IA`) ignore extra trailing columns.

Valid statuses: `autorizado`, `não autorizado`, `para recepção`, `para entrega`, `autorizado_patio`, `autorizado_temp`, `excluido`.

Plate regex: `^[A-Z]{3}\d[A-Z0-9]\d{2}$` (covers old `ABC1234` and Mercosul `ABC1D23`).

`excluido` is a soft-delete flag — records stay in CSV but are filtered from display and search.

## Key constraints

- No database: CSV is the only persistence. Always open via file dialog before editing.
- Plates stored uppercase, hyphens stripped on input.
- `build_IA/repository.py` uses atomic writes (temp file + `shutil.move`) to avoid corruption on crash.
