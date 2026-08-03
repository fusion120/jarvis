# Jarvis

Personal AI assistant for Mohamed. Flask backend (Render) + static website (Netlify) + Chrome extension for browser control.

## Structure

- `backend/` — Flask API (deploy to Render)
- `frontend/` — website (deploy to Netlify)
- `extension/` — Chrome extension (load unpacked)

## Setup

1. **Render** — New Web Service → connect repo → root directory `backend` → build command `pip install -r requirements.txt` → start command `gunicorn app11:app`
2. **Environment variables (Render):** `GROQ_API_KEY` (required — from console.groq.com, free). Optional: `GROQ_MODEL` (default `llama-3.3-70b-versatile`), `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `CANVAS_TOKEN`, `CANVAS_DOMAIN`, `OUTLOOK_EMAIL`, `OUTLOOK_PASSWORD`, `DIGEST_TIME` (HH:MM, default `12:00` UTC), `DIGEST_TZ` (offset, e.g. `-05:00` for Houston)
3. **Netlify** — import the repo; `netlify.toml` already sets the base to `frontend`
4. **Chrome** — `chrome://extensions` → Developer mode → Load unpacked → select `extension/` → set the backend URL in the popup

## Browser control

Ask in chat (e.g. *"open Gmail, summarize the newest messages and draft replies"*) — Jarvis plans the browser steps, the extension executes them, and the result appears on the Browser page and Telegram. Each command runs exactly once (the backend hands each task to the extension a single time). **"Open <site>" commands open in a new tab** (e.g. *"open yt"* → YouTube in a new tab), with common short names like `yt`, `gmail`, `maps` mapped automatically.

## Voice control (wake word)

Open the dashboard in Chrome/Edge and click the mic icon in the topbar. Say **"wake up"** (or "Jarvis"), then give a command — Jarvis runs it and (unless **Silent mode** is on) reads the reply aloud. Clicking the mic while it's on captures one command immediately without the wake word. Voice works while the dashboard tab is open.

## OpenJarvis-style controls

- **Morning digest** — daily briefing of new Outlook email + upcoming Canvas deadlines + scheduled reminders + news, sent to Telegram and spoken. Runs at `DIGEST_TIME` or on demand via the ☀️ chip / "morning briefing" voice command.
- **Deep research** — the Research page (or "research …" voice command): Jarvis searches the web (Wikipedia + DuckDuckGo + article extraction) and returns a cited answer.
- **Scheduled reminders** — the Reminders page lets you schedule a task with a date/time; Jarvis alerts you on Telegram when it's due.
- **Canvas** — assignments auto-complete after the 2-hour window via the Telegram `CANVAS YES` → `SUBMIT` flow. The Canvas page's **Test Canvas** button confirms your token/domain are working.

## Browser superpowers

Jarvis can see and drive **all** your open tabs, not just the active one: `list_tabs`, `read_tab`/`switch_tab`/`close_tab` (by URL, title, or tab number), `go_back`/`go_forward`, `new_window`, `group_tabs` (auto-group tabs by topic), `save_session`/`restore_session` (save and reopen whole multi-tab sessions by voice), and `save_tab` (save the page you're on into the **Research Log**, shown on the Research page). Try: *"list my tabs"*, *"switch to the tab about X"*, *"group my tabs by project"*, *"save my session"*, or *"save this tab"*.

## Smarter + more human

- **Web-grounded answers** — for current-events/factual questions, Jarvis pulls fresh Google News + DuckDuckGo context before answering, with source links. No model change needed (still free `llama-3.3-70b-versatile`; swap via `GROQ_MODEL`).
- **Human tone** — warmer, more natural persona in every reply, and the voice uses varied, natural acknowledgments.
