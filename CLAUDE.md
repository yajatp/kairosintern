# Kairos — Developer Notes for Claude

## Hard rules

- **No emojis anywhere.** Never use emoji characters (📄 📊 📱 🎯 🔄 ✓ ✗ etc.) in any Python file, HTML string, button label, markdown string, or comment. Use Streamlit Material icons (`:material/download:`, `:material/table_chart:`, `:material/phone:`, `:material/refresh:`, etc.) or plain text instead.
- **No comments explaining what code does.** Only add a comment when the WHY is non-obvious.
- **No new files unless required.** Prefer editing existing files.

## Stack

- Streamlit 1.50 multi-page app (`app.py` → `pages/`)
- Python 3.9, dotenv loaded in `app.py`
- Supabase (REST API via `requests`, not the Python SDK) for persistence
- Google Sheets via `gspread` + service account JSON in `GOOGLE_SERVICE_ACCOUNT_JSON` env var
- Folium + streamlit-folium for the sidebar map
- Outscraper API for deep review scans

## Audience

This is an **internal tool** used by the Kairos co-founders and early team. Everyone using it already knows what Kairos is and what the product does. Do NOT write copy that explains "what Kairos is" or treats the user like an outsider. Write for people who built the company.

## Color palette (from kairoshealthai.com)

- `#183e34` — dark forest green (primary brand, CTA buttons, accents)
- `#3abdaf` — teal mint (Streamlit primary, already in `.streamlit/config.toml`)
- `rgba(24, 62, 53, 0.05)` — subtle green tint for card backgrounds
- `rgba(24, 62, 53, 0.12)` — stronger green tint
- `#e5e7eb` — light gray border
- `#282a30` — primary text
- `#6b6f76` — secondary text
- `#ffffff` — white base

## Key session state keys

- `_pipeline` — dict tracking run state (running, progress, leads_df, etc.)
- `history_target_run` — run ID to auto-expand when switching to History page
- `history_target_lead_place_id` — place ID to scroll to in that run
- `_leads_{run_id}` — cached leads per run (lazy-loaded in history.py)
- `history_limit` — how many runs to load (default 50)

## Supabase schema notes

- `leads` table: `ALTER TABLE leads ADD COLUMN IF NOT EXISTS email TEXT;`
- `leads` table: `ALTER TABLE leads ADD COLUMN IF NOT EXISTS reviews_json TEXT;`
- Run these migrations before deploying email extraction.

## Local dev detection

`os.path.exists("/Users/yajatparmar")` is used throughout to gate local-only features (test run logging, etc.).

## Google Sheets

Spreadsheet ID: `1UlBdK2z7UsP-_IFYhxK5IImmHCOGFKKvaGHUDw_dXHs`  
Auto-sync runs on every pipeline completion. Use "Sync History" button in History page to backfill missed runs.
