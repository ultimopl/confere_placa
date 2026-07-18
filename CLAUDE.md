# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
# Active version (monolithic, v1.3)
python confere.py

# Refactored version (MVC, build_IA/)
python build_IA/main.py

# Generate fake data for testing
python fake_data.py
```

No build step, no dependencies beyond stdlib (`tkinter` must be available).

## Architecture

Two parallel implementations exist:

**`confere.py`** — single-file monolith (v1.3, currently active). `App(tk.Tk)` does everything: UI layout, search logic, CSV I/O, history. Easier to run, harder to extend.

**`build_IA/`** — MVC refactor:
- `repository.py` — `Repository`: CSV load/save (atomic write via `tempfile`+`shutil.move`), in-memory dict `{placa: [detalhes, status, timestamp]}`, soft-delete (status `"excluido"`).
- `app.py` — `App`: controller, holds business logic and validation, event handlers called by UI, drives `Repository`.
- `ui.py` — `UI(tk.Tk)`: pure presentation, calls back into `App` via event methods (`on_search_requested`, etc.).
- `main.py` — entry point only.

## Data model

CSV format (semicolon-delimited, no header):
```
PLACA;detalhes;status;timestamp_iso
```

Valid statuses: `autorizado`, `não autorizado`, `para recepção`, `para entrega`, `autorizado_patio`, `excluido`.

Plate regex: `^[A-Z]{3}\d[A-Z0-9]\d{2}$` (covers old `ABC1234` and Mercosul `ABC1D23`).

`excluido` is a soft-delete flag — records stay in CSV but are filtered from display and search.

## Key constraints

- No database: CSV is the only persistence. Always open via file dialog before editing.
- Plates stored uppercase, hyphens stripped on input.
- `build_IA/repository.py` uses atomic writes (temp file + `shutil.move`) to avoid corruption on crash.
