# Jarvis

Personal AI assistant for Mohamed. Flask backend (Render) + static website (Netlify) + Chrome extension for browser control.

## Structure

- `backend/` — Flask API (deploy to Render)
- `frontend/` — website (deploy to Netlify)
- `extension/` — Chrome extension (load unpacked)

## Setup

1. **Render** — New Web Service → connect repo → root directory `backend` → build command `pip install -r requirements.txt` → start command `gunicorn app11:app`
2. **Environment variables (Render):** `CLAUDE_API_KEY` (required — from console.anthropic.com). Optional: `CLAUDE_MODEL` (default `claude-fable-5`; set `claude-opus-5` for max quality or `claude-haiku-4-5-20251001` for cheapest), `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `CANVAS_TOKEN`, `CANVAS_DOMAIN`, `OUTLOOK_EMAIL`, `OUTLOOK_PASSWORD`
3. **Netlify** — import the repo; `netlify.toml` already sets the base to `frontend`
4. **Chrome** — `chrome://extensions` → Developer mode → Load unpacked → select `extension/` → set the backend URL in the popup

## Browser control

Ask in chat (e.g. *"open Gmail, summarize the newest messages and draft replies"*) — Jarvis plans the browser steps, the extension executes them, and the result appears on the Browser page and Telegram.
