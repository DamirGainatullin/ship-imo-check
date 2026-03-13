# Ship IMO Check

Telegram bot for checking IMO numbers in local `sources/` documents (`.pdf`, `.docx`, `.doxc`).

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create `.env` from `.env.example` and set `BOT_TOKEN`.

## Commands

```bash
python manage.py index
python manage.py check 9595321
python manage.py run-bot
```

## Notes

- `index` scans files from `SOURCES_DIR` and writes hits to SQLite (`DB_PATH`).
- Only text PDFs are supported in this MVP (no OCR for scanned PDFs).

