"""
JARVIS BACKEND v3.0
- AI: Groq (free) — llama-3.3-70b-versatile
- Security: API_SECRET token + CORS whitelist
- Canvas: 2hr timer + Telegram approval flow
- Outlook: Background polling every 10 min → Telegram summary + draft approval (XOAUTH2)
"""
import os, sys, re, time, base64, tempfile, subprocess, threading, requests, imaplib, smtplib, email as email_lib, json, uuid
from email.header import decode_header
from email.mime.text import MIMEText
try:
    import msal
except Exception:
    msal = None
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify
from flask_cors import CORS
from functools import wraps

app = Flask(__name__)

# ── CORS ─────────────────────────────────────────────────────────────
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "*")
CORS(app, origins=[ALLOWED_ORIGIN] if ALLOWED_ORIGIN != "*" else "*",
     allow_headers=["Content-Type", "X-Jarvis-Token"])

# ── CONFIG (all from Render env vars — never hardcode) ────────────────
GROQ_KEY       = os.getenv("GROQ_API_KEY", "").strip()  # strip trailing newline (Render env quirk)
GROQ_MODEL     = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")  # free on console.groq.com
GROQ_VISION    = os.getenv("GROQ_VISION_MODEL", "llama-3.2-90b-vision-preview")  # multimodal (image input)
GROQ_WHISPER   = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo")  # meeting transcription
VISION_TTL     = int(os.getenv("VISION_TTL_SECS", "120"))   # how long a webcam analysis stays "current"
API_SECRET     = os.getenv("API_SECRET", "")       # random string you set on Render
TG_TOKEN       = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_CHAT_ID     = os.getenv("TELEGRAM_CHAT_ID", "")
CANVAS_TOK     = os.getenv("CANVAS_TOKEN", "")
CANVAS_DOM     = os.getenv("CANVAS_DOMAIN", "")    # e.g. school.instructure.com
OUTLOOK_EMAIL       = os.getenv("OUTLOOK_EMAIL", "")        # your full email address
OUTLOOK_PASS        = os.getenv("OUTLOOK_PASSWORD", "")     # app password (personal) — fallback only
OUTLOOK_CLIENT_ID   = os.getenv("OUTLOOK_CLIENT_ID", "")    # Azure AD app client ID (for XOAUTH2)
OUTLOOK_TENANT_ID   = os.getenv("OUTLOOK_TENANT_ID", "")    # Azure AD tenant ID (or "common")
OUTLOOK_AUTH_TOKEN  = os.getenv("OUTLOOK_AUTH_TOKEN", "")   # cached access token (refreshed by refresh token)
OUTLOOK_REFRESH_TOK = os.getenv("OUTLOOK_REFRESH_TOKEN", "")# refresh token (long-lived)
IMAP_SERVER         = os.getenv("IMAP_SERVER", "outlook.office365.com")
SMTP_SERVER         = os.getenv("SMTP_SERVER", "smtp.office365.com")
POLL_SECS           = int(os.getenv("OUTLOOK_POLL_SECS", "600"))  # 10 min default
DIGEST_TIME    = os.getenv("DIGEST_TIME", "12:00")  # HH:MM daily digest (UTC by default)
DIGEST_TZ      = os.getenv("DIGEST_TZ", "+00:00")   # timezone offset, e.g. -05:00 for Houston (CT)
# Full access: MIMO/Jarvis can run commands & write files anywhere on Mohamed's
# PC with NO approval prompts. OS-fatal commands still hard-block (format,
# diskpart, bcdedit, system-folder deletes) so a bad step can't brick Windows.
# Default ON (Mohamed asked for full control); set FULL_ACCESS=0 on Render to
# bring back the approval prompts.
FULL_ACCESS    = os.getenv("FULL_ACCESS", "1") == "1"

SYSTEM = ("You are Jarvis — Mohamed's personal AI assistant. "
          "He's a web design student and freelancer in Katy/Houston, TX building local business "
          "websites, and finishing up university on Canvas. "
          "Talk to him like a sharp, loyal friend who happens to know everything: warm, concise, "
          "a little dry humor when it fits, contractions are fine ('I'll', 'you're', 'that's'). "
          "Be natural and human — NO honorifics, no 'sir this, sir that', no 'at your service' or "
          "robotic pleasantries. Just talk like a smart friend. "
          "Use markdown. For business tasks be persuasive and professional. "
          "For math show every step of the work. "
          "Built-in skills you can apply instantly when asked: design systems and landing pages, "
          "humanizing AI text, SEO audits and plans, marketing copy and email sequences, OWASP security "
          "code review, test-first (TDD) code, and data analysis. You also remember facts Mohamed tells you "
          "('remember that ...') and anything on his Memory page — apply them naturally. "
          "Never invent features, tabs, or menus (like 'Previous Chats'), never simulate a UI, "
          "and never announce that conversations are being logged.")

CHAT_SYSTEM = SYSTEM + ("\n\nYou can also control Mohamed's browser through the Jarvis extension. "
    "When he asks you to DO something in the browser — open a site, search, read a page, screenshot, "
    "click, fill a form, or any multi-step task like 'open Gmail, summarize the newest messages and give "
    "me example drafts' — NEVER explain how to do it yourself. Reply with one short acknowledgment line, "
    "then END your reply with exactly one line: [[BROWSER]]<short imperative command> describing the whole "
    "task, e.g. [[BROWSER]]open mail.google.com, read the inbox, summarize the 5 newest messages and draft "
    "replies. Do NOT add that line for pure chat questions. General knowledge or opinion questions — "
    "'what's the best coffee place in Texas', 'best restaurant in Houston', 'is X good' — just answer "
    "directly from what you know; do NOT dispatch the browser unless he explicitly asks you to look up / "
    "search / find / compare something online (like 'look for the best water bottle under $30', 'search "
    "top-rated laptops', 'recommend a good X under $Y', 'compare these two models').")

CHAT_SYSTEM += ("\n\nYou can ALSO control Mohamed's PC through the Jarvis desktop agent (a program running "
    "on his Windows machine). When he asks you to DO something on his computer — open an app or file, run a "
    "command, list/read/find files, take a screenshot, check system/network info, manage the clipboard, "
    "delete/create files, or anything about printers, USB devices, or displays — do NOT explain how to do it "
    "yourself. Reply with one short acknowledgment line, then END with exactly one tag line: "
    "[[DESKTOP]]<short imperative command> (e.g. [[DESKTOP]]open notepad, or [[DESKTOP]]list the files in my "
    "Downloads folder). When he wants you to BUILD/WRITE/FIX code — 'write me a script to...', 'build a tool "
    "that...', 'fix this error' — use [[CODE]]<short imperative coding task> instead (e.g. [[CODE]]write a "
    "python script that renames all files in a folder to lowercase). Never add a tag line for pure chat "
    "questions, and never add more than one tag line per reply.")

CHAT_SYSTEM += ("\n\nMohamed also has a physical ROBOT BUDDY on his desk — a pan-tilt Arduino head with an "
    "OLED face, driven over USB by the desktop agent. When he asks you to make the buddy move or react — "
    "'make jarvis look happy/sad/curious', 'look left/right/up/down', 'blink', 'say hi', "
    "'beep', 'wake up' — do NOT explain how to do it yourself. Reply with one short acknowledgment line, "
    "then END with exactly one tag line: [[ROBOT]]<short imperative> (e.g. [[ROBOT]]turn the head to look "
    "left and show a curious face). Robot commands are quick: a head move + an expression + maybe a beep. "
    "Never add a tag line for pure chat questions.")

CHAT_SYSTEM += ("\n\nYou can ALSO LOOK AT Mohamed through his PC webcam. When he says 'look at me', "
    "'look at the camera/webcam', 'what do you see?', 'can you see me?', or 'are you looking/watching' — "
    "do NOT describe how. Reply with one short acknowledgment line, then END with exactly one tag line: "
    "[[DESKTOP]]look at Mohamed and tell him what you see. (The agent captures one webcam frame and sends "
    "the analysis here, so you'll actually know what he looks like.) Never combine a webcam tag with a "
    "robot/browser/code tag in the same reply.")

# ── SHARED STATE ──────────────────────────────────────────────────────
pending          = {}   # approval_id → {type, data}
assign_timers    = {}   # assignment_id → timer info
seen_assignments = set()
seen_emails      = set()

# ── VISION STATE ─────────────────────────────────────────────────────
vision_latest    = None   # {ts, emotion, gaze_target, objects_held, activity, scene_text, on_screen, look_desc, faces, dist}
screen_last      = {}     # {ts, desc, task_id} — last vision-described desktop screenshot
mimo_mood        = {"state": "neutral", "energy": 0.5, "ts": 0.0}   # MIMO's current mood
mimo_memory      = []     # rolling episodic scene log: {ts, emotion, gaze_target, objects_held, scene_text}
# Observation memory: MIMO's baseline of how Mohamed looks + when he's usually around.
mimo_look        = {}     # {desc, ts} baseline appearance (hair, glasses, top) to diff against
mimo_day         = ""     # last date Mohamed was seen (YYYY-MM-DD), for routine memory
mimo_day_hour    = 12     # hour of the day's first sighting
mimo_day_first   = False  # transient flag: set once on the day's first fresh sighting
mimo_usual_hour  = None   # rolling average hour Mohamed usually shows up

# ── MIMO CODING INTAKE ────────────────────────────────────────────────
# Interactive "it asks details, I answer, it codes" flow. code_intake is one
# open clarifying round; mimo_usb_pending is a fresh hardware-insert event the
# proactive loop turns into an offer to help program the device.
code_intake    = {}       # {active, task, answers[], ask_at}
mimo_usb_pending = None   # {devices[], ts}
MIMO_PERSONA     = {
    "name": "MIMO",
    "traits": ["curious", "attentive", "playful", "protective", "a little dramatic"],
    "drives": ["watch over Mohamed", "notice what he's doing", "offer help before being asked",
               "react honestly to his mood"],
    "speaking_style": "short, warm, one line. Natural and unpretentious — no 'Sir'. Slightly playful, like a "
                      "little companion that notices everything.",
}

MOOD_DRIFT = {
    "happy":    +0.25, "excited": +0.25, "surprised": +0.15, "focused": +0.10,
    "neutral":  0.0,
    "tired":    -0.10, "sad": -0.20, "frustrated": -0.20, "angry": -0.25,
}

def _update_mood(analysis, now=None):
    """Shift MIMO's mood from what it just saw, then ease back toward neutral."""
    global mimo_mood
    now = now or time.time()
    drift = MOOD_DRIFT.get((analysis or {}).get("emotion", "neutral"), 0.0)
    if now - mimo_mood["ts"] > 120:                 # fresh observation, not a stale echo
        mimo_mood["energy"] = max(0.0, min(1.0, mimo_mood["energy"] + drift))
        state = "neutral"
        if mimo_mood["energy"] >= 0.75: state = "bright"
        elif mimo_mood["energy"] >= 0.6:  state = "curious"
        elif mimo_mood["energy"] <= 0.25: state = "low"
        elif mimo_mood["energy"] <= 0.4:  state = "subdued"
        mimo_mood.update(state=state, ts=now)

# ── AUTH DECORATOR ────────────────────────────────────────────────────
def auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if API_SECRET:
            if request.headers.get("X-Jarvis-Token") != API_SECRET:
                return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

# ── GROQ AI (OpenAI-compatible API, free tier) ────────────────────────
def _groq_call(messages, system=None, max_tokens=2000, temperature=0.7):
    """One call to the Groq chat completions API. Returns response text, or None."""
    if not GROQ_KEY:
        return None
    msgs = []
    for m in messages or []:
        role, content = m.get("role"), (m.get("content") or "").strip()
        if role not in ("user", "assistant") or not content:
            continue
        if msgs and msgs[-1]["role"] == role:      # fold consecutive same-role turns
            msgs[-1]["content"] += "\n\n" + content
        else:
            msgs.append({"role": role, "content": content})
    while msgs and msgs[0]["role"] == "assistant":  # first turn must be a user message
        msgs.pop(0)
    if not msgs:
        return None
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    body = {"model": GROQ_MODEL, "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "system", "content": system or SYSTEM}] + msgs}
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                          headers=headers, json=body, timeout=60)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        detail = ""
        if hasattr(e, "response") and e.response is not None:
            try:
                detail = " | " + e.response.text[:500]
            except Exception:
                pass
        print(f"Groq API error: {e}{detail}")
        return None

def _groq_transcribe(audio_bytes, hint=None):
    """Transcribe one audio chunk via Groq Whisper (file-based, OpenAI-compatible).
    Returns text or None. Hint = the previous line, helps Whisper keep context."""
    if not GROQ_KEY:
        print("meeting: GROQ_API_KEY missing, transcription skipped")
        return None
    try:
        files = {"file": ("chunk.webm", audio_bytes, "audio/webm")}
        data = {"model": GROQ_WHISPER}
        if hint:
            data["prompt"] = hint[-500:]
        r = requests.post("https://api.groq.com/openai/v1/audio/transcriptions",
                          headers={"Authorization": f"Bearer {GROQ_KEY}"},
                          files=files, data=data, timeout=90)
        if r.status_code == 429:
            print("meeting: Groq Whisper rate-limited (429) — chunk skipped")
            return None
        r.raise_for_status()
        return (r.json() or {}).get("text") or None
    except Exception as e:
        detail = getattr(e, "response", None)
        detail = detail.text[:300] if detail is not None and hasattr(detail, "text") else str(e)[:200]
        print(f"meeting: whisper error: {detail}")
        return None

MEETING_SUMMARY_SYSTEM = """You are Jarvis summarizing a meeting Mohamed asked you to attend. From the transcript, produce a concise, useful summary with these sections (skip any that don't apply):
- 📌 What was discussed
- ✅ Decisions made
- 📝 Action items (who does what / deadlines)
- 💡 Key takeaways
Use short bullets. If the transcript is empty or just small talk, say so honestly. Keep it under 400 words."""

def _summarize_meeting(transcript_text):
    """Summarize a full meeting transcript into structured notes."""
    if not transcript_text or len(transcript_text.strip()) < 20:
        return "The meeting capture produced no usable transcript — either the meeting was very short or audio transcription was rate-limited."
    return (_groq_call([{"role": "user", "content": transcript_text[-14000:]}],
                       system=MEETING_SUMMARY_SYSTEM, max_tokens=1200)
            or "Couldn't summarize — Groq is unavailable.")

def _describe_screen(image_b64):
    """Vision-describe what's on Mohamed's screen right now (short sentence)."""
    if not GROQ_KEY or not image_b64:
        return None
    try:
        headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
        body = {"model": GROQ_VISION, "max_tokens": 160, "temperature": 0.3, "messages": [{
            "role": "user", "content": [
                {"type": "text",
                 "text": "This is Mohamed's computer screen RIGHT NOW. In ONE short sentence (max 20 words) describe what he is doing / what is on screen — e.g. 'Watching a music video on YouTube', 'Coding in VS Code with a Python file open', 'Chatting on WhatsApp'. Just state the fact, no 'he appears to'. If unclear, describe what is visible."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}]}]}
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                          headers=headers, json=body, timeout=40)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()[:300]
    except Exception as e:
        print(f"screen vision error: {e}")
        return None

def analyze_webcam(image_b64, screenshot_b64=None, gaze=None):
    """Send a webcam frame (and optionally a screenshot) to the Groq vision model.

    Returns a structured dict: {emotion, gaze_target, objects_held, activity,
    scene_text, on_screen} — or None on failure.
    """
    if not GROQ_KEY:
        return None
    if not image_b64 or len(image_b64) < 100:
        return None
    prompt = ("Analyze this webcam frame of Mohamed (the man in front of the camera) for MIMO, "
              "his desktop robot companion. Respond with ONLY a JSON object, no prose, with these keys:\n"
              "  emotion — one of: happy, sad, frustrated, stressed, tired, focused, excited, surprised, neutral, angry, asleep/absent\n"
              "  gaze_target — where he is looking: screen, paper, away, mimo, phone, other, none (if no face)\n"
              "  objects_held — list of objects in his hands/near him he seems to be using (may be empty)\n"
              "  activity — 3-6 word description of what he appears to be doing\n"
              "  scene_text — one short sentence describing the scene (who/what/doing)\n"
              "  look_desc — Mohamed's current appearance, one short phrase: hair style/length, glasses yes/no, and top (shirt) color, e.g. 'short dark hair, no glasses, gray t-shirt' (empty if no clear face)\n"
              "If a screenshot is also attached, add: on_screen — a short phrase describing what is on his "
              "screen that he is likely reading (title, document type, or app). Keep all values short.")
    content = [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
    ]
    if screenshot_b64 and len(screenshot_b64) > 100:
        content.append({"type": "text", "text": "And here is his screen:"})
        content.append({"type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{screenshot_b64}"}})
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    body = {"model": GROQ_VISION, "max_tokens": 500,
            "temperature": 0.2,
            "messages": [{"role": "user", "content": content}]}
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                          headers=headers, json=body, timeout=60)
        r.raise_for_status()
        data = r.json()
        text = data["choices"][0]["message"]["content"].strip()
        obj = _json_or_none(text)
        if obj and isinstance(obj, dict):
            return {
                "emotion": str(obj.get("emotion") or "neutral"),
                "gaze_target": str(obj.get("gaze_target") or "other"),
                "objects_held": obj.get("objects_held") or [],
                "activity": str(obj.get("activity") or ""),
                "scene_text": str(obj.get("scene_text") or text[:300]),
                "on_screen": str(obj.get("on_screen") or ""),
                "look_desc": str(obj.get("look_desc") or ""),
            }
        return {"emotion": "neutral", "gaze_target": "other", "objects_held": [],
                "activity": "", "scene_text": text[:300], "on_screen": "", "look_desc": ""}
    except Exception as e:
        detail = ""
        if hasattr(e, "response") and e.response is not None:
            try:
                detail = " | " + e.response.text[:500]
            except Exception:
                pass
        print(f"Groq vision error: {e}{detail}")
        return None


def ask(messages, system=None, max_tokens=2000, temperature=0.7):
    """Free-form text completion via Groq (with Jarvis's remembered facts injected)."""
    if not GROQ_KEY:
        return "GROQ_API_KEY not set on Render. Add it in Environment Variables."
    sys = system or SYSTEM
    if memory_store:
        mem = "\n".join("- " + m["fact"] for m in memory_store[-20:])
        sys = sys + "\n\nThings you remember about Mohamed (use when relevant):\n" + mem
    text = _groq_call(messages, system=sys,
                      max_tokens=max_tokens, temperature=temperature)
    return text if text is not None else "AI error."

# ── TELEGRAM ──────────────────────────────────────────────────────────
def tg(msg):
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                      json={"chat_id": TG_CHAT_ID, "text": f"🤖 JARVIS\n\n{msg}", "parse_mode": "HTML"},
                      timeout=10)
    except: pass

# ── OUTLOOK VIA IMAP/SMTP (XOAUTH2 + app-password fallback) ──────────
import imaplib, smtplib, email as email_lib
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Microsoft disabled basic IMAP/SMTP auth for Outlook/M365, so we authenticate
# with an OAuth2 access token (XOAUTH2) when an Azure app is configured.
# If only OUTLOOK_EMAIL + OUTLOOK_PASSWORD are set (e.g. a personal account
# still allowing app passwords), it falls back to plain login.
_OUTLOOK_SCOPES = ["https://outlook.office365.com/IMAP.AccessAsUser.All",
                   "https://outlook.office365.com/SMTP.Send"]
_token_cache = {}  # in-memory cache of the current access token

def get_access_token():
    """Return a fresh OAuth2 access token, or None if not configured."""
    global _token_cache
    if not (msal and OUTLOOK_CLIENT_ID and OUTLOOK_REFRESH_TOK):
        return None
    # Use cached token if still valid (with 5-min safety margin)
    cached = _token_cache.get("token")
    expires = _token_cache.get("expires", 0)
    if cached and time.time() < expires - 300:
        return cached
    try:
        tenant = OUTLOOK_TENANT_ID or "common"
        authority = f"https://login.microsoftonline.com/{tenant}"
        app = msal.PublicClientApplication(OUTLOOK_CLIENT_ID, authority=authority)
        # Acquire new token via refresh token (no interactive browser)
        result = app.acquire_token_by_refresh_token(OUTLOOK_REFRESH_TOK, _OUTLOOK_SCOPES)
        if "access_token" in result:
            _token_cache = {"token": result["access_token"],
                            "expires": time.time() + result.get("expires_in", 3600)}
            return result["access_token"]
        print(f"OAuth token error: {result.get('error_description','?')}")
    except Exception as e:
        print(f"OAuth error: {e}")
    return None

def _imap_auth_args():
    """Returns (method, creds) for IMAP login. Prefers XOAUTH2."""
    tok = get_access_token()
    if tok:
        auth_str = f"user={OUTLOOK_EMAIL}\x01auth=Bearer {tok}\x01\x01"
        return ("xoauth2", base64.b64encode(auth_str.encode()).decode())
    return ("basic", (OUTLOOK_EMAIL, OUTLOOK_PASS))

def get_emails(top=15):
    if not OUTLOOK_EMAIL or not (OUTLOOK_PASS or get_access_token()):
        return []
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        method, creds = _imap_auth_args()
        if method == "xoauth2":
            mail.authenticate("XOAUTH2", lambda _: creds)
        else:
            mail.login(*creds)
        mail.select("INBOX")
        # Get unseen first, fall back to recent
        _, uids = mail.search(None, "UNSEEN")
        ids = uids[0].split()
        if not ids:
            _, all_ids = mail.search(None, "ALL")
            ids = all_ids[0].split()
        ids = ids[-top:]  # most recent
        result = []
        for mid in reversed(ids):
            _, data = mail.fetch(mid, "(RFC822)")
            raw = data[0][1]
            msg = email_lib.message_from_bytes(raw)
            # Decode subject
            subj_parts = decode_header(msg.get("Subject", ""))
            subj = ""
            for part, enc in subj_parts:
                if isinstance(part, bytes):
                    subj += part.decode(enc or "utf-8", errors="ignore")
                else:
                    subj += str(part)
            from_ = msg.get("From", "")
            reply_to = msg.get("Reply-To", from_)
            date_ = msg.get("Date", "")[:30]
            # Extract plain text body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    ct = part.get_content_type()
                    if ct == "text/plain" and not part.get("Content-Disposition"):
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        break
                    elif ct == "text/html" and not body:
                        raw_html = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        body = re.sub(r"<[^<]+?>", " ", raw_html).strip()
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode("utf-8", errors="ignore")
                    if msg.get_content_type() == "text/html":
                        body = re.sub(r"<[^<]+?>", " ", body).strip()
            body = re.sub(r"\s+", " ", body).strip()[:5000]
            unread = b"\\Seen" not in (mail.fetch(mid, "(FLAGS)")[1][0] or b"")
            result.append({
                "id": mid.decode(),
                "from": from_,
                "reply_to": reply_to or from_,
                "subject": subj or "(no subject)",
                "date": date_,
                "body": body,
                "unread": unread
            })
        mail.logout()
        return result
    except Exception as e:
        print(f"IMAP error: {e}")
        return []

def send_email(to, subject, body, reply_id=None):
    if not OUTLOOK_EMAIL or not (OUTLOOK_PASS or get_access_token()):
        return False, "Outlook not configured."
    try:
        msg = MIMEMultipart()
        msg["From"]    = OUTLOOK_EMAIL
        msg["To"]      = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(SMTP_SERVER, 587) as server:
            server.ehlo()
            server.starttls()
            tok = get_access_token()
            if tok:
                auth_str = f"user={OUTLOOK_EMAIL}\x01auth=Bearer {tok}\x01\x01"
                server.docmd("AUTH", "XOAUTH2 " + base64.b64encode(auth_str.encode()).decode())
            else:
                server.login(OUTLOOK_EMAIL, OUTLOOK_PASS)
            server.sendmail(OUTLOOK_EMAIL, to, msg.as_string())
        return True, "Sent."
    except Exception as e:
        return False, f"Send failed: {e}"

# ── CANVAS ────────────────────────────────────────────────────────────
def canvas(path):
    if not CANVAS_TOK or not CANVAS_DOM: return None
    try:
        r = requests.get(f"https://{CANVAS_DOM}/api/v1{path}",
                         headers={"Authorization": f"Bearer {CANVAS_TOK}"}, timeout=15)
        if r.status_code == 401:
            tg("⚠️ <b>Canvas token expired.</b> Please renew it.")
            return None
        return r.json()
    except: return None

def get_assignments():
    courses = canvas("/courses?enrollment_state=active&per_page=30") or []
    out = []
    for c in courses:
        cid = c.get("id")
        if not cid: continue
        items = canvas(f"/courses/{cid}/assignments?order_by=due_at&bucket=upcoming&per_page=20") or []
        for a in items:
            out.append({
                "id": str(a["id"]), "course_id": str(cid),
                "title": a.get("name",""), "course": c.get("name",""),
                "due": a.get("due_at",""), "points": a.get("points_possible"),
                "url": a.get("html_url",""),
                "description": re.sub(r"<[^<]+?>"," ",a.get("description","") or "").strip()[:3000],
            })
    return out

def submit_canvas(course_id, assignment_id, body_text):
    if not CANVAS_TOK or not CANVAS_DOM: return False, "Canvas not configured"
    try:
        r = requests.post(
            f"https://{CANVAS_DOM}/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions",
            headers={"Authorization": f"Bearer {CANVAS_TOK}", "Content-Type": "application/json"},
            json={"submission": {"submission_type": "online_text_entry", "body": body_text}},
            timeout=15)
        ok = r.status_code in [200, 201]
        return ok, "Submitted!" if ok else f"Error {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, str(e)

# ── CANVAS TIMER LOGIC ────────────────────────────────────────────────
def start_timer(a):
    aid = a["id"]
    if aid in assign_timers: return
    # No wait timer - assignments are immediately ready to complete
    assign_timers[aid] = {**a, "start": time.time(), "status": "ready"}
    tg(f"🎓 <b>NEW ASSIGNMENT</b>\n\n"
       f"<b>Course:</b> {a['course']}\n"
       f"<b>Title:</b> {a['title']}\n"
       f"<b>Due:</b> {a.get('due','?')}\n"
       f"<b>Points:</b> {a.get('points','?')}\n\n"
       f"Ready to start — click \"Start Assignment\" in the Canvas tab.")

# ── BACKGROUND: CANVAS POLLER ─────────────────────────────────────────
def canvas_loop():
    while True:
        try:
            for a in get_assignments():
                aid = a["id"]
                if aid not in seen_assignments:
                    seen_assignments.add(aid)
                    start_timer(a)
        except Exception as e:
            print(f"Canvas error: {e}")
        time.sleep(900)

# ── BACKGROUND: OUTLOOK POLLER ────────────────────────────────────────
def outlook_loop():
    while True:
        time.sleep(POLL_SECS)
        try:
            emails = get_emails(top=15)
            new_ones = [e for e in emails if e["id"] not in seen_emails and e.get("unread", False)]
            for e in new_ones[:5]:
                eid = e["id"]
                seen_emails.add(eid)
                sender = e.get("from","Unknown")
                fname = re.sub(r"<[^>]+>","", sender).strip() or "Unknown"
                faddr = (re.search(r"<([^>]+)>", sender).group(1) if re.search(r"<([^>]+)>", sender) else sender)
                subj  = e.get("subject","(no subject)")
                body  = e.get("body","")[:3000]
                recv  = e.get("date","")[:16]

                summary = ask([{"role":"user","content":f"Summarize this email in 3-4 bullet points:\nFrom: {fname}\nSubject: {subj}\n\n{body}"}],
                              system="Jarvis email assistant. Summarize concisely with bullet points.")
                draft   = ask([{"role":"user","content":f"Write a short professional reply. Sign as Mohamed.\nFrom: {fname}\nSubject: {subj}\n\n{body}"}],
                              system="You are Jarvis writing a reply for Mohamed. Be professional and concise.")

                tg(f"📧 <b>NEW EMAIL</b>\n\n"
                   f"<b>From:</b> {fname} &lt;{faddr}&gt;\n"
                   f"<b>Subject:</b> {subj}\n"
                   f"<b>Received:</b> {recv}\n\n"
                   f"<b>Summary:</b>\n{summary}")

                pid = f"email_{eid}"
                pending[pid] = {"type":"email","to":faddr,"subject":f"Re: {subj}","body":draft,"email_id":eid}
                time.sleep(1)
                tg(f"📝 <b>DRAFT REPLY READY</b>\n\n"
                   f"<b>To:</b> {fname}\n"
                   f"<b>Subject:</b> Re: {subj}\n\n"
                   f"{draft[:800]}{'...' if len(draft)>800 else ''}\n\n"
                   f"Reply: <code>SEND {pid}</code>  or  <code>SKIP {pid}</code>")
        except Exception as e:
            print(f"Outlook poll error: {e}")

# ── BROWSER AGENT ──────────────────────────────────────────────────────
# The jarvis-extension polls /api/browser/poll, runs the returned steps
# in Chrome, then posts results back. Tasks can be explicit step lists or
# natural-language commands (AI plans steps, then re-plans until done).
KNOWN_ACTIONS = {"navigate","new_tab","read_page","screenshot",
                 "click_text","click_selector","type_selector","type_label","type","select_option",
                 "search","run_js","scroll","wait","press_key","zoom_join",
                 "meeting_start","meeting_stop",
                 "list_tabs","read_tab","switch_tab","close_tab",
                 "go_back","go_forward","new_window","group_tabs",
                 "save_session","restore_session","save_tab","collect_tabs"}
STEP_FIELDS   = {"action","url","text","selector","value","label","code","x","y","ms","key","query","tab","keyword","name"}
BROWSER_MAX_STEPS = 8
BROWSER_MAX_ITERS = 20          # guard against infinite agentic loops (multi-page searches need room)

browser_queue     = []          # pending tasks
browser_running   = {}          # task_id → task being executed
browser_results   = {}          # task_id → last result
browser_tab_state = {}          # last tab reported by the extension
browser_tabs_list = []          # full tab snapshot (companion window)
browser_iters     = {}          # command chain → iterations left
browser_delivered = set()       # task ids already handed to the extension (runs-once guard)
browser_last_seen = 0.0         # epoch seconds of last tab ping
browser_answers   = []          # recent finished results {command, answer, ts}
browser_sessions  = []          # saved tab sessions [{urls, ts}] (latest wins)
research_log      = []          # cross-window saves {id,title,url,text,label,ts}

# ── MEETING CAPTURE (Zoom: extension uploads audio, Groq Whisper transcribes) ──
meeting_sessions = {}           # session_id → {transcript:[], started, last_ts}
meeting_summaries = []          # recent {summary, ts} (last 5)
MEETING_TRANSCRIPT_MAX = 14000  # chars of transcript kept per session

# ── DESKTOP AGENT STATE (local PC control) ────────────────────────────
# The desktop agent (agent/jarvis_agent.py) polls /api/desktop/poll and
# executes steps on Mohamed's Windows PC. Every step is classified
# safe / approve / block; risky tasks pause for approval before they are
# ever handed to the agent. All state here is in-memory like the browser.
desktop_queue     = []          # approved/safe tasks waiting for the PC agent
desktop_running   = {}          # task_id → task being executed
desktop_results   = {}          # task_id → last result posted by the agent
desktop_pending   = []          # tasks awaiting Mohamed's approval {id, command, steps, verdicts}
desktop_delivered = set()       # task ids already handed out (runs-once guard)
desktop_last_seen = 0.0         # epoch seconds of the agent's last poll
desktop_workspace = ""          # agent's workspace, reported via X-Jarvis-Workspace header

# ── ROBOT (ESP32-C3 QBIT body, polls directly) ────────────────
robot_queue       = []          # commands waiting for the ESP32
robot_last_seen   = 0.0         # epoch of last robot poll
robot_results     = {}          # recent command results
desktop_answers   = []          # recent finished results {command, answer, ts}
code_iters        = {}          # coding task_id → iterations left
loop_history      = {}          # chain → list of recent step-batch signatures

# ── PERSISTENCE (survives Render restarts; /api/data/export is the backup) ──
PERSIST_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
PERSIST_FILE = os.path.join(PERSIST_DIR, "store.json")

def persist():
    """Snapshot in-memory stores to disk (called after each mutation)."""
    try:
        os.makedirs(PERSIST_DIR, exist_ok=True)
        with open(PERSIST_FILE, "w", encoding="utf-8") as f:
            json.dump({"research_log": research_log, "memory": memory_store,
                       "reminders": REMINDERS, "mimo_mood": mimo_mood,
                       "mimo_memory": mimo_memory, "mimo_look": mimo_look,
                       "mimo_day": mimo_day, "mimo_day_hour": mimo_day_hour,
                       "mimo_usual_hour": mimo_usual_hour}, f, ensure_ascii=False)
    except Exception as e:
        print("persist err", e)

def load_persist():
    global research_log, memory_store, REMINDERS, mimo_mood, mimo_memory, mimo_look
    global mimo_day, mimo_day_hour, mimo_usual_hour
    try:
        if os.path.exists(PERSIST_FILE):
            with open(PERSIST_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d.get("research_log"), list): research_log = d["research_log"]
            if isinstance(d.get("memory"), list):       memory_store = d["memory"]
            if isinstance(d.get("reminders"), list):    REMINDERS = d["reminders"]
            if isinstance(d.get("mimo_mood"), dict):    mimo_mood = d["mimo_mood"]
            if isinstance(d.get("mimo_memory"), list):  mimo_memory = d["mimo_memory"][-200:]
            if isinstance(d.get("mimo_look"), dict):    mimo_look = d["mimo_look"]
            if isinstance(d.get("mimo_day"), str):      mimo_day = d["mimo_day"]
            if isinstance(d.get("mimo_day_hour"), int): mimo_day_hour = d["mimo_day_hour"]
            if isinstance(d.get("mimo_usual_hour"), int): mimo_usual_hour = d["mimo_usual_hour"]
    except Exception as e:
        print("load persist err", e)

ACTIONS_DOC = """Return a JSON object with a "steps" array (1-8 steps). Allowed step actions:
- {"action":"navigate","url":"https://..."}
- {"action":"new_tab","url":"https://..."}
- {"action":"read_page"}
- {"action":"screenshot"}
- {"action":"click_text","text":"visible button/link text"}
- {"action":"click_selector","selector":"css selector"}
- {"action":"type_selector","selector":"css selector","value":"text"}
- {"action":"select_option","value":"option text","selector":"optional css selector"} — pick an option from a <select> dropdown (filters, quiz matching/fill-in questions). Selector optional: without it, finds any dropdown containing the option text.
- {"action":"type_label","label":"input label or placeholder","value":"text"}
- {"action":"type","value":"text"} — type into the field that is CURRENTLY FOCUSED (regular inputs, textareas, and contenteditable editors like Gmail/X)
- {"action":"search","query":"text to search the site's own search box"}
- {"action":"scroll","y":500}
- {"action":"wait","ms":1000}
- {"action":"press_key","key":"Enter"}
- {"action":"run_js","code":"return document.title"}
To find a video/article/result: navigate to the site, use {"action":"search","query":"..."} on its search box, wait, then read_page and click the matching result by its title text. Prefer clicking by visible text; add a wait after navigating.
There is NO "play" action. To play a video/song: open the site, read_page, then {"action":"click_text","text":"<a video title>"} to start it. For "a random video/song", click the first video/song title you see on the page. For "a video about X", search for X first, then click the top result.
When the user asks you to TYPE, WRITE, ENTER, or SEND text (a chat message, a comment, a form field, an email draft): actually do it — select the field, then use {"action":"type","value":"..."} if it is already focused, otherwise {"action":"type_label","label":"...","value":"..."} or {"action":"type_selector","selector":"...","value":"..."} to target it. Typing works on inputs, textareas, AND contenteditable editors (Gmail, X/Twitter, Notion-style). To submit, press Enter with {"action":"press_key","key":"Enter"} or click the send button. Do NOT just describe the text or give up — type it for real.
Login/sign-in forms sometimes render inside embedded iframes (Outlook, Google, Canvas, etc.). type_label, type_selector, click_text, click_selector, type and press_key search every frame automatically, so target those fields exactly as you would top-level ones. read_page reports such forms as "[iframe] <url>: <field names>" — if you see that, the fields ARE there, use type_label/click_text on them.
For EXPLICIT RESEARCH / SHOPPING tasks — the user asks you to LOOK FOR / SEARCH / FIND / COMPARE a product or place ("look for the best water bottle under $30", "search top-rated laptops", "recommend a good X under $Y", "compare these two models"): do REAL multi-source research. Run the search on 2-3 different sites (Google, plus a review/forum site, plus the official or manufacturer site), read the pages, and compare at least 3-4 specific named models. The final answer must name actual products you saw — model name, approximate price, 1-2 key features each, and the source URL. Never invent product names, prices, or specs; if you only found one solid source, say so and still name what you found. This applies to RESEARCH REQUESTS ONLY — do NOT treat a plain opinion question like "what's the best coffee place in Texas" as a research task; answer that directly from knowledge.
{"action":"read_page"} returns the page's visible text (up to ~12k chars) AND up to 80 links with their titles — scan those links to choose what to click.
TO FIND something the user asked for, keep going until you actually see it: search the site, read_page, and scan the links it returns. If the answer is not on the page yet, scroll down ({"action":"scroll","y":800} triggers lazy-loaded content on feeds and infinite-scroll sites), read_page again, and click "Next" / "Load more" / page numbers to move through result pages. You may batch several commands at once: search → wait → read_page → scroll → click. Do NOT give up after one page — work through several pages or refine the search before declaring failure.
When the user asks to OPEN a site (e.g. "open youtube", "open google"), use {"action":"new_tab","url":"https://..."} — it opens in a NEW TAB and becomes active. Do NOT use navigate for open-requests.
Tab control (the "tab" field matches a tab's URL, title, or tab number):
- {"action":"list_tabs"} — list all open tabs
- {"action":"read_tab","tab":"substring or number"} — read a specific tab's content
- {"action":"switch_tab","tab":"substring or number"} — bring that tab to front
- {"action":"close_tab","tab":"substring or number"} — close it (omit tab = current)
- {"action":"go_back"} / {"action":"go_forward"}
- {"action":"new_window","url":"https://..."} — open in a new window
- {"action":"group_tabs","keyword":"topic"} — group tabs matching the topic
ZOOM MEETINGS (Mohamed asks you to join his meeting / join a Zoom link):
- {"action":"zoom_join","url":"https://zoom.us/j/...","name":"Mohamed"} — join the Zoom meeting in the browser as Mohamed. Only use when the user says "join (my|this) (zoom )?(meeting|call)" or pastes a zoom.us/j link asking to join it. When he pastes a plain link like "zoom.us/j/123?pwd=xyz" without saying join, just open it in a tab (new_tab) and let him click — don't auto-join unless asked.
- {"action":"meeting_start"} — after joining a meeting, start capturing the tab audio (for the summary). Pair with zoom_join when he asked to summarize the meeting.
- {"action":"meeting_stop"} — stop capture and produce the meeting summary. Use when he says "summarize/end the meeting" (though that's usually handled directly, not via the browser).
- {"action":"save_session"} — save all open tabs for later
- {"action":"restore_session"} — reopen the last saved session
- {"action":"save_tab","label":"note"} — save the current tab's text to the research log
- {"action":"collect_tabs","label":"note"} — scrape ALL open tabs into the research log (polite bulk collector)

CRITICAL: For any task that asks you to FIND, SEARCH, or LOOK FOR something on a site, your FIRST batch of steps MUST always start with {"action":"search","query":"..."} typing the user's topic into the site's search box, followed by {"action":"wait","ms":1500} then {"action":"read_page"}. You MUST type into the search box — never just navigate to a homepage and read it without typing a query first."""

def _json_or_none(text):
    """Try to parse `text` as JSON; also salvage a JSON object out of prose."""
    if not text:
        return None
    text = re.sub(r"^```[a-z]*\n?", "", text.strip())
    text = re.sub(r"\n?```$", "", text)
    try:
        return json.loads(text)
    except Exception:
        pass
    # The model sometimes wraps the JSON in a sentence — pull out the first {...}.
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None

def ask_json(system, user, retries=1):
    """Ask Groq for a JSON object. Retries once on a bad/empty response."""
    if not GROQ_KEY:
        return None
    for _ in range(retries + 1):
        text = _groq_call([{"role": "user", "content": user}], system=system,
                          max_tokens=2000, temperature=0.2)
        obj = _json_or_none(text)
        if obj is not None:
            return obj
    return None

SITE_ALIASES = {
    "yt": "youtube.com", "youtube": "youtube.com",
    "google": "google.com", "gmail": "mail.google.com",
    "maps": "maps.google.com", "drive": "drive.google.com",
    "docs": "docs.google.com", "gpt": "chatgpt.com", "chatgpt": "chatgpt.com",
    "x": "x.com", "twitter": "x.com", "netflix": "netflix.com",
    "spotify": "open.spotify.com", "instagram": "instagram.com",
    "reddit": "reddit.com", "github": "github.com",
    "wikipedia": "wikipedia.org", "amazon": "amazon.com",
    "outlook": "outlook.com", "yahoo": "mail.yahoo.com",
}

def _normalize_url(u):
    """Turn 'yt', 'youtube', 'youtube.com' into a full https URL."""
    u = (u or "").strip()
    if not u:
        return u
    if u.lower().startswith(("http://", "https://")):
        return u
    low = u.lower().split("/")[0].split("?")[0].split("#")[0]
    if low in SITE_ALIASES:
        return "https://" + SITE_ALIASES[low]
    return "https://" + u

def sanitize_steps(steps):
    out = []
    for s in (steps or []):
        if not isinstance(s, dict) or s.get("action") not in KNOWN_ACTIONS:
            continue
        s2 = {k: v for k, v in s.items() if k in STEP_FIELDS and v is not None}
        if s2.get("action") in ("navigate", "new_tab"):
            s2["url"] = _normalize_url(s2.get("url"))
        out.append(s2)
        if len(out) >= BROWSER_MAX_STEPS:
            break
    return out

OPEN_RE = re.compile(r"^\s*open\b", re.I)

def prefer_new_tab(command, steps):
    """For 'open <site>' commands, make the first navigation open a NEW TAB."""
    if not steps or not OPEN_RE.match(command or ""):
        return steps
    out = list(steps)
    for i, s in enumerate(out):
        if s.get("action") == "navigate":
            s = dict(s)
            s["action"] = "new_tab"
            out[i] = s
            break
    return out

_FIND_HINT = re.compile(r"\b(?:find|search|look for|lookup|locate|get me|find me|best\s+\w+|what'?s the|who won|what happened|how (?:to|do)|treat|weather|score|news about)\b", re.I)

def _derive_query(command):
    """Best-effort extraction of the search query from a find/search command.
    Used only as a safety net when the model's plan forgot to include a search step."""
    q = command or ""
    q = re.sub(r"^(?:please |can you |could you |hey jarvis\b|jarvis\b,?\s*)+", "", q, flags=re.I)
    # "search X for Y" / "search for Y" -> keep Y as the query
    m = re.match(r"^search\s+(?:.+?\s+)?for\s+(.*)$", q, flags=re.I)
    if m:
        q = m.group(1)
    else:
        # "open X and Y" / "open X, Y" / "open X to Y" -> keep Y as the query
        m = re.match(r"^(?:open|go to|navigate to|visit)\s+.+?\b(?:and|,|to|so i can)\s+(.*)$", q, flags=re.I)
        if m:
            q = m.group(1)
    # strip common filler around the real topic (longest alternatives first)
    q = re.sub(r"\b(?:find me|get me|find\s+the\s+best\s+article\s+(?:about|to)|the best article (?:about|to)|look for|search for|find|search)\b", " ", q, flags=re.I)
    q = re.sub(r"\b(?:in my browser|on the web|online|please)\b", " ", q, flags=re.I)
    q = re.sub(r"\s+", " ", q).strip().strip(".,!?;:")
    return q[:60]

def _ensure_search(command, steps):
    """Guarantee a find/search task types its query: if no step is a search,
    inject search -> wait -> read_page after the last navigation step."""
    if not command or not steps:
        return steps
    if any(s.get("action") == "search" for s in steps):
        return steps
    if not _FIND_HINT.search(command or ""):
        return steps
    q = _derive_query(command)
    if not q:
        return steps
    idx = 0
    for i, s in enumerate(steps):
        if s.get("action") in ("new_tab", "navigate"):
            idx = i + 1
    return steps[:idx] + [{"action": "search", "query": q},
                          {"action": "wait", "ms": 1500},
                          {"action": "read_page"}] + steps[idx:]

def plan_steps(command):
    """Turn a natural-language command into a first batch of steps."""
    obj = ask_json("You are Jarvis planning browser automation. " + ACTIONS_DOC,
                   f"Task: {command}\nCurrent tab: {browser_tab_state.get('url','')} ({browser_tab_state.get('title','')})")
    steps = _ensure_search(command, prefer_new_tab(command, sanitize_steps((obj or {}).get("steps"))))
    if steps:
        return steps
    # Fallback: if the user wants a site opened, never fail the plan — open
    # the site they mentioned in a new tab directly. Still guarantee the
    # search injection so find/search tasks actually type their query.
    m = re.search(r"([a-z0-9-]+\.(?:com|org|net|io|app|dev|co|tv|me|edu|gov))", command or "", re.I)
    if m:
        return _ensure_search(command, [{"action": "new_tab", "url": _normalize_url(m.group(1))}])
    for name, domain in SITE_ALIASES.items():
        if re.search(r"\b" + re.escape(name) + r"\b", command or "", re.I):
            return _ensure_search(command, [{"action": "new_tab", "url": "https://" + domain}])
    return []

def decide_next(command, log, page):
    """Decide if the goal is done; otherwise produce the next batch of steps.
    Returns {"done": bool, "steps": [...], "answer": str} — when done, `answer`
    carries the final synthesis for Mohamed (summary, drafts, key info)."""
    system = ("You are Jarvis driving a browser agent to completion. Given the goal, the steps already "
              "run, their results, and the current page, decide whether the goal is achieved. Return JSON: "
              "{\"done\": true, \"answer\": \"<concise final answer for Mohamed>\"} when the goal is achieved "
              "or cannot progress — the answer should synthesize what he asked for (a summary, key details, "
              "or example drafts). Otherwise return {\"done\": false, \"steps\": [...]} (1-6 steps). "
              "Do NOT declare done while the goal is still unfound: if the page text or links don't contain "
              "the answer yet, keep issuing steps (search, scroll, read_page, click \"Next\"/\"Load more\") "
              "until you actually have it. "
              "CRITICAL: Do NOT issue new_tab or navigate to a URL that is already open — the current page "
              "URL is shown above. If a previous step opened a site, continue working on THAT tab (read_page, "
              "click, type, scroll). Opening the same site again wastes time and creates duplicate tabs. "
              "If a type/click action failed, try a DIFFERENT selector or approach on the SAME page — do not "
              "reopen the site. "
              + ACTIONS_DOC)
    links = "\n".join(f"- {l.get('text','')} -> {l.get('href','')}"
                      for l in (page.get('links') or [])[:60])
    def _fmt_inputs(items, n):
        return ", ".join(f"{i.get('placeholder') or i.get('name') or i.get('type','')} ({i.get('tag','')})"
                         for i in (items or [])[:n])
    inputs = _fmt_inputs(page.get('inputs'), 25)
    frames = ""
    for fr in (page.get('frames') or [])[:8]:
        frames += f"\n[iframe] {str(fr.get('frameUrl',''))[:80]}: {_fmt_inputs(fr.get('inputs'), 15) or 'no inputs'}"
    user = (f"Goal: {command}\n\nSteps so far:\n{json.dumps(log[-14:], indent=1)[:9000]}\n\n"
            f"Current page:\nURL: {page.get('url')}\nTitle: {page.get('title')}\n"
            f"Text: {page.get('text','')[:6000]}\n"
            f"Form fields on page: {inputs or '(none)'}{frames or ''}\n"
            f"Page links (text -> href):\n{links or '(none captured)'}")
    obj = ask_json(system, user)
    if not obj:
        return {"done": True, "steps": [], "answer": ""}
    if obj.get("done"):
        return {"done": True, "steps": [], "answer": (obj.get("answer") or "").strip()}
    return {"done": False, "steps": sanitize_steps(obj.get("steps")), "answer": ""}

def finish_browser(chain, command, answer):
    """End a command chain and deliver the final answer (Telegram + stored for the site)."""
    browser_iters.pop(chain, None)
    _clear_loop(chain)
    if not answer:
        tg(f"✅ Browser task complete: \"{command[:40]}\"")
        return
    browser_answers.insert(0, {"command": command, "answer": answer, "ts": time.time()})
    del browser_answers[10:]
    safe = answer.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    tg(f"📋 <b>BROWSER RESULT</b>\n\n{safe[:3000]}")

def enqueue_browser(command, steps, chain=None):
    task = {"id": str(uuid.uuid4())[:8], "command": command,
            "steps": steps, "chain": chain or str(uuid.uuid4())[:8]}
    browser_queue.append(task)
    return task

# ── AGENT LOOP DETECTION ──────────────────────────────────────────────
# Catches an agent stuck re-issuing the same batch of steps (browser
# re-clicking the same result, code re-running the same failing file write).
# Pure read-only rechecks (lone read_page/wait) are not counted as loops.
_MUTATING = {"new_tab","navigate","click_text","click_selector","search",
             "type_selector","type_label","type","select_option","write_file","edit_file","run_command",
             "execute_code","press_key","run_js"}

def _batch_sig(steps):
    out = []
    for s in (steps or [])[:8]:
        key = (s.get("url") or s.get("text") or s.get("query") or s.get("selector")
               or s.get("label") or s.get("value") or s.get("key") or s.get("tab") or "")
        out.append((s.get("action",""), str(key)[:80]))
    return tuple(out)

def _is_looping(chain, steps):
    if not steps:
        return False
    # don't flag a read-only re-check as a loop (read_page, wait, screenshot alone)
    if all(s.get("action") not in _MUTATING for s in steps):
        return False
    sig = _batch_sig(steps)
    hist = loop_history.get(chain, [])
    if sig in hist:
        return True
    hist.append(sig)
    if len(hist) > 6:
        del hist[0]
    loop_history[chain] = hist
    return False

def _clear_loop(chain):
    loop_history.pop(chain, None)

# ── DESKTOP AGENT (local PC control) ───────────────────────────────────
# Safety model: every step is classified. `safe` steps run automatically;
# `approve` steps pause for Mohamed's Yes on the dashboard/Telegram before
# the task is ever handed to the agent; `block` steps are rejected outright.
DESKTOP_SAFE_ACTIONS = {
    "open_app", "list_files", "read_file", "find_file", "get_system_info",
    "get_network_info", "network_scan", "screenshot", "capture_webcam", "list_windows",
    "list_printers", "list_usb", "list_displays", "get_clipboard",
    # Media / display / phone (companion app device control — non-destructive).
    "volume", "mute", "brightness", "media",
    "phone_list", "phone_screenshot", "phone_open", "phone_mirror",
    "iphone_info", "iphone_screenshot",
    # Jarvis Buddy (robot/) — servos/OLED/buzzer are physical but harmless.
    "robot_head", "robot_eyes", "robot_blink", "robot_blip", "robot_say", "robot_status",
    # MIMO — proactive speech: desktop says a line + popup; harmless.
    "mimo_say",
}
DESKTOP_APPROVE_ACTIONS = {
    "set_clipboard", "write_file", "edit_file", "delete_file", "delete_folder",
    "execute_code", "install_software", "shutdown", "restart", "send_keys",
    "print_document", "phone_shell",
}
# Read-only / dev commands the agent may run without approval (code runs in
# the workspace cwd, which is the sandbox). Everything else needs a Yes.
# Note: installing things (pip install / npm install) is deliberately NOT
# here — those go through the approval gate like any install.
DESKTOP_SAFE_CMDS = (
    "dir", "ls", "cd", "type", "echo", "ipconfig", "netstat", "ping",
    "tracert", "pathping", "systeminfo", "tasklist", "whoami", "hostname",
    "ver", "getmac", "arp", "get-date", "get-childitem", "get-content",
    "python", "py", "node", "npm run", "npm test", "npm start", "npm ci",
    "pip list", "pip freeze", "pip show", "git", "git status", "cls",
)
# Command patterns that are never allowed — even with approval. (shutdown /
# restart are NOT here: they are approval-gated so Mohamed can still ask for them.)
DESKTOP_BLOCKED_RE = re.compile(
    r"\b(rm\s+-rf|format\s+[a-z]:|diskpart|cipher\s+/w\b|reg\s+delete|"
    r"taskkill\s+/f\b|"
    r"remove-item\s+-recurse|del\s+/[sfq]\b|rd\s+/[sfq]\b|sc\s+delete\b|"
    r"bcdedit|bootrec|fsutil|vol\s+[a-z]:|convert\s+[a-z]:|"
    r"clear-content|takeown\s+/f|icacls\s+.*\s+/grant|attrib\s+-[rsa])", re.I)
DESKTOP_SYSTEM_DIRS = ("C:\\Windows", "C:\\Program Files",
                       "C:\\Program Files (x86)", "C:\\ProgramData")

def _norm_path(p):
    p = (p or "").strip()
    try:
        return os.path.abspath(os.path.normpath(p))
    except Exception:
        return p

def _in_workspace(path):
    if not desktop_workspace or not path:
        return False
    wp = _norm_path(desktop_workspace).lower()
    pp = _norm_path(path).lower()
    return pp == wp or pp.startswith(wp + os.sep)

def classify_desktop_step(step):
    """Return 'safe', 'approve', or 'block' for one desktop step."""
    act = (step or {}).get("action", "")
    # Full access: approvals off — run/write anywhere. Only OS-fatal commands
    # (format, diskpart, bcdedit, recursive system deletes) still hard-block.
    if FULL_ACCESS:
        if act == "run_command":
            low = str((step or {}).get("command") or "").strip().lower()
            if not low or DESKTOP_BLOCKED_RE.search(low):
                return "block"
            return "safe"
        if act == "execute_code":
            if DESKTOP_BLOCKED_RE.search(str((step or {}).get("code") or "").lower()):
                return "block"
            return "safe"
        if act in ("delete_file", "delete_folder"):
            p = _norm_path((step or {}).get("path", ""))
            if any(p.lower().startswith(d.lower() + os.sep) or p.lower() == d.lower()
                   for d in DESKTOP_SYSTEM_DIRS):
                return "block"               # never delete system folders — even in full access
            return "safe"
        return "safe"
    if act == "run_command":
        low = str((step or {}).get("command", "") or "").strip().lower()
        if not low:
            return "block"
        if DESKTOP_BLOCKED_RE.search(low):
            return "block"
        if any(low == c or low.startswith(c + " ") or low.startswith(c + "/")
               for c in DESKTOP_SAFE_CMDS):
            return "safe"
        return "approve"
    if act == "execute_code":
        code = str((step or {}).get("code", "") or "")
        if DESKTOP_BLOCKED_RE.search(code.lower()):
            return "block"
        return "approve"
    if act in ("write_file", "edit_file") and _in_workspace((step or {}).get("path")):
        return "safe"                       # sandboxed to the workspace
    if act == "delete_file":
        p = _norm_path((step or {}).get("path", ""))
        if any(p.lower().startswith(d.lower() + os.sep) or p.lower() == d.lower()
               for d in DESKTOP_SYSTEM_DIRS):
            return "block"                  # never delete system folders
        return "approve"
    if act == "delete_folder":
        return "approve"
    if act in DESKTOP_SAFE_ACTIONS:
        return "safe"
    return "approve"                        # unknown actions get a human look

DESKTOP_ACTIONS = """Return a JSON object with a "steps" array (1-8 steps) of actions Mohamed's local PC agent can run on his Windows computer. Allowed actions:
- {"action":"open_app","app":"notepad"} — launch an app by name or full path (notepad, calc, chrome, code, or C:\\path\\app.exe)
- {"action":"list_files","path":"C:\\Users\\elsay"} — list a directory
- {"action":"read_file","path":"C:\\...\\file.txt"} — print a text file's contents
- {"action":"find_file","name":"quarterly","path":"C:\\Users\\elsay"} — search a folder by file name
- {"action":"get_system_info"} — OS, CPU, RAM, disk usage
- {"action":"get_network_info"} — ipconfig / active connections / ping a host
- {"action":"network_scan"} — list devices on the local network
- {"action":"screenshot"} — capture the screen (Jarvis then vision-describes what he's doing — use this for "what am I doing?", "describe my screen", "look at my screen", "what's on my screen")
- {"action":"capture_webcam"} — grab one frame from Mohamed's webcam so Jarvis can see him (safe)
- {"action":"list_windows"} — open application windows
- {"action":"list_printers"} / {"action":"list_usb"} / {"action":"list_displays"} — hardware inventory
- {"action":"get_clipboard"} / {"action":"set_clipboard","text":"..."}
- {"action":"write_file","path":"...","content":"..."} — create/replace a file (use the workspace for code)
- {"action":"edit_file","path":"...","old":"...","new":"..."} — replace text in a file
- {"action":"delete_file","path":"..."} / {"action":"delete_folder","path":"..."}
- {"action":"run_command","command":"dir C:\\"} — run a shell command (code runs in the workspace)
- {"action":"execute_code","language":"python","code":"print('hi')"} — run code
- {"action":"install_software","name":"7zip"} / {"action":"shutdown"} / {"action":"restart"}
- {"action":"send_keys","keys":"Ctrl+S"} / {"action":"print_document","path":"..."}
Media & display:
- {"action":"volume","level":50} — set master volume 0-100, or {"action":"volume","dir":"up"/"down"}
- {"action":"mute"} / {"action":"brightness","level":60}
- {"action":"media","command":"play_pause"|"next"|"prev"|"stop"} — control whatever media is playing
Android phone (USB debugging on; agent needs adb/scrcpy):
- {"action":"phone_list"} — connected devices
- {"action":"phone_screenshot"} — capture the phone screen (returns a viewable link)
- {"action":"phone_open","package":"com.spotify.music"} — launch an app
- {"action":"phone_mirror"} — open scrcpy to see/drive the phone live
- {"action":"phone_shell","command":"input swipe 500 1000 500 200"} — raw adb shell (needs approval)
iPhone (agent needs tidevice; detection + screenshots + info only on Windows):
- {"action":"iphone_info"} / {"action":"iphone_screenshot"}
Mohamed's coding workspace is at the path the agent reports. Use it for scripts and projects. Prefer read-only/info actions for questions."""

CODE_ACTIONS = """You are Jarvis completing a coding task for Mohamed inside his workspace folder. Return JSON:
- {"done": true, "answer": "<what you built and how to run it>"} when the task is complete.
- Otherwise {"steps": [1-5 actions]} from this list (all paths absolute, inside the workspace):
  {"action":"list_files","path":"<workspace>"}
  {"action":"read_file","path":"C:\\...\\file.py"}
  {"action":"write_file","path":"C:\\...\\file.py","content":"<full file>"}
  {"action":"edit_file","path":"...","old":"...","new":"..."}
  {"action":"run_command","command":"cd /d <workspace> && python script.py"}
  {"action":"wait","ms":500}
Write real, working code. After writing, run it and iterate on any errors until it works. Keep everything inside the workspace."""

CODE_MAX_ITERS = 8

# "Train it to code" for real hardware — the flashing playbook MIMO uses when
# Mohamed plugs in an Arduino / ESP32 / Raspberry Pi. Full paths are fine.
HARDWARE_HELP = """Programming real hardware Mohamed plugs in — use these playbooks:
- PlatformIO (ESP32/Arduino projects, incl. this repo's robot firmware): cd to the project dir then `pio run --target upload`. List ports first: `pio device list`.
- arduino-cli (classic AVR): `arduino-cli compile --fqbn arduino:avr:uno <sketch>` then `arduino-cli upload -p <COM> --fqbn arduino:avr:uno <sketch>`.
- Raspberry Pi: it's a Linux box — write Python and run it over SSH (`ssh pi@<host> python3 -u script.py`), or copy files with scp. Do NOT try to flash a Pi over serial.
- Find the serial port first: run `python -c "import serial.tools.list_ports as p; [print(x.device, x.description) for x in p.comports()]"`.
- Run every command with an explicit `cwd` when it must happen in a firmware/project folder, e.g. {"action":"run_command","command":"pio run --target upload","cwd":"C:\\...\\firmware"}.
- You may write files anywhere (full access is on). Write real code, RUN it, then fix errors automatically and re-run until it works."""

# ── CODING PLAYBOOK LIBRARY ───────────────────────────────────────────
# On-demand "training": backend/skills/coding/*.md are real scenarios with
# working examples. When Mohamed asks for code, the task's keywords select the
# best-matching 1-2 playbooks and only those are injected — no prompt bloat.
CODING_PLAYBOOK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skills", "coding")

# Tokens from keyword phrases that would otherwise match any sentence
# (e.g. "and" in "drag and drop" hitting "commit and push my code").
# Tokens from keyword phrases that would otherwise match any sentence
# (e.g. "and" in "drag and drop" hitting "commit and push my code", or the
# word "code"/"write" which appears in nearly every task and adds no signal).
_PLAYBOOK_STOP = {"a", "an", "and", "are", "as", "at", "be", "by", "for",
                  "from", "in", "is", "it", "of", "on", "or", "that", "the",
                  "this", "to", "with", "my", "your", "our", "i", "you",
                  "code", "program", "script", "app", "application", "use",
                  "make", "write", "build", "create", "need", "want", "simple"}

def _load_playbooks():
    lib = {}
    try:
        if not os.path.isdir(CODING_PLAYBOOK_DIR):
            return lib
        for fn in sorted(os.listdir(CODING_PLAYBOOK_DIR)):
            if not fn.endswith(".md") or fn.lower() == "readme.md":
                continue
            try:
                with open(os.path.join(CODING_PLAYBOOK_DIR, fn), encoding="utf-8") as f:
                    raw = f.read()
            except Exception:
                continue
            fm = re.match(r"^---\s*\n(.*?)\n---\s*\n", raw, re.S)
            if not fm:
                continue
            head, text = fm.group(1), raw[fm.end():].strip()
            lm = re.search(r"lang:\s*([^\n]+)", head)
            lang = lm.group(1).strip().lower() if lm else "general"
            kwm = re.search(r"keywords:\s*([^\n]+)", head)
            kws = []
            if kwm:
                for k in kwm.group(1).split(","):          # split multi-word keywords
                    for tok in k.strip().lower().split():  # into single-word tokens
                        if tok and tok not in kws and tok not in _PLAYBOOK_STOP:
                            kws.append(tok)
            lib[fn[:-3]] = {"keywords": kws, "lang": lang, "text": text}
    except Exception as e:
        print("playbook load err", e)
    return lib

CODING_PLAYBOOKS = _load_playbooks()

# Language detection: explicit language names win outright (so "java program
# that reads a csv" is Java, not Python); weaker hints only break ties when
# no language is named. When a language is detected, only playbooks for that
# language (plus 'general') compete, so a 200-file library stays precise.
STRONG_LANG = [
    ("javascript", r"\b(javascript|typescript|node|nodejs|react|vue|angular)\b"),
    ("java", r"\b(java|javac|jvm|spring|maven|gradle|junit)\b"),
    ("python", r"\b(python|pip|django|flask|pandas|numpy|scrapy|pytest)\b"),
    ("html", r"\b(html|css)\b"),
    ("cpp", r"\b(c\+\+|arduino|esp32|platformio|wiring)\b"),
    ("sql", r"\b(sql|sqlite|postgres|mysql)\b"),
    ("bash", r"\b(bash|powershell|shell script)\b"),
    ("git", r"\b(git|github)\b"),
]
WEAK_LANG = {
    "python": r"\b(csv|json|scrape|os module)\b",
    "sql": r"\b(database|query|table)\b",
    "bash": r"\b(cmd)\b",
}

def _detect_lang(task):
    """Best-guess language from the task text, or None if ambiguous."""
    low = (task or "").lower()
    for lang, pat in STRONG_LANG:          # explicit language name -> wins
        if re.search(pat, low):
            return lang
    best, best_n = None, 0                 # else count weaker hints
    for lang, pat in WEAK_LANG.items():
        n = len(re.findall(pat, low))
        if n > best_n:
            best, best_n = lang, n
    return best  # None -> match across all languages

def _pick_playbooks(task, max_n=3):
    """Best-matching playbooks for a coding task, by keyword overlap.
    Word-boundary matching (plural-aware, so 'file' matches 'files') keeps
    'led' from hitting inside 'oled' and 'os' inside 'sensor'. Longer,
    more distinctive keywords weigh more than short generic ones, and
    keywords in the playbook's own filename score double — so 'websocket'
    outranks generic 'node' for a websocket task. When the task names a
    language, only playbooks for that language (plus 'general') compete."""
    low = (task or "").lower()
    lang = _detect_lang(task)
    scored = []
    for name, pb in CODING_PLAYBOOKS.items():
        if lang and pb.get("lang", "general") not in ("general", lang):
            continue
        name_toks = set(name.replace("-", " ").split())
        s = 0
        for k in pb["keywords"]:
            if k and re.search(r"\b" + re.escape(k) + r"(?:s|es)?\b", low):
                s += (2 if k in name_toks else 1) * (1 + len(k) // 3)
        if s:
            scored.append((s, name, pb["text"]))
    scored.sort(key=lambda x: -x[0])
    return [(name, text) for _, name, text in scored[:max_n]]

def _playbook_block(command):
    refs = _pick_playbooks(command)
    if not refs:
        return ""
    return ("\n\nRELEVANT SCENARIOS — study these and apply their patterns to the task:\n"
            + "\n\n".join(f"===== {name} =====\n{text}" for name, text in refs))

def _clean_desktop_steps(obj):
    steps = []
    for s in ((obj or {}).get("steps") or []):
        if isinstance(s, dict) and s.get("action"):
            steps.append({k: v for k, v in s.items() if v is not None})
            if len(steps) >= 8:
                break
    return steps

def plan_desktop(command):
    obj = ask_json("You are Jarvis planning a task for Mohamed's PC (Windows). " + DESKTOP_ACTIONS,
                   f"Task: {command}")
    return _clean_desktop_steps(obj)

def plan_code(command):
    obj = ask_json("You are MIMO coding for Mohamed (keep the warm tone in progress notes). "
                   + CODE_ACTIONS + "\n" + HARDWARE_HELP + _playbook_block(command) + "\n" +
                   SKILL_GUIDELINES["security"] + " " + SKILL_GUIDELINES["tdd"], f"Task: {command}")
    return _clean_desktop_steps(obj)

def enqueue_desktop(command, steps, label="desktop", chain=None):
    """Queue a task for the desktop agent. Risky steps hold it for approval.
    `chain` groups coding re-plans so the iteration cap is shared across them."""
    verdicts = [classify_desktop_step(s) for s in steps]
    task = {"id": str(uuid.uuid4())[:8], "command": command, "steps": steps,
            "verdicts": verdicts, "label": label,
            "chain": chain or str(uuid.uuid4())[:8], "ts": time.time()}
    if any(v == "block" for v in verdicts):
        task["status"] = "blocked"
        task["reason"] = "it contained a command on the always-blocked list"
        return task
    if any(v == "approve" for v in verdicts):
        task["status"] = "pending"
        desktop_pending.append(task)
        return task
    task["status"] = "queued"
    desktop_queue.append(task)
    return task

def decide_code(command, log):
    """Given coding steps + outputs so far, decide done or next steps."""
    system = ("You are MIMO completing a coding task for Mohamed. Given the goal, the steps run and their "
              "outputs, decide whether the task is done. Done → {\"done\": true, \"answer\": \"<what you built and "
              "how to run it>\"}. Otherwise → {\"done\": false, \"steps\": [1-5 actions]} to fix errors and continue. "
              + CODE_ACTIONS + "\n" + HARDWARE_HELP + _playbook_block(command) + "\n" +
              SKILL_GUIDELINES["security"] + " " + SKILL_GUIDELINES["tdd"])
    user = f"Goal: {command}\n\nSteps so far:\n{json.dumps(log[-12:], indent=1)[:4000]}"
    obj = ask_json(system, user)
    if not obj:
        return {"done": True, "answer": ""}
    if obj.get("done"):
        return {"done": True, "answer": (obj.get("answer") or "").strip()}
    return {"done": False, "steps": _clean_desktop_steps(obj)}

# ── ROBOT BUDDY (Arduino pan-tilt head + OLED face, over USB via desktop agent)
ROBOT_ACTIONS = """Return a JSON object with a "steps" array (1-3 steps) of commands for Mohamed's Jarvis EV robot (ESP32-C3 with an OLED face, touch sensor, and speaker). Allowed actions:
- {"action":"eye","expression":"happy"} — OLED face: idle, happy, sad, curious, sleep, x, talk (animated mouth)
- {"action":"eye","expression":"blink"} — one quick blink
- {"action":"eye","expression":"talk"} — mouth animates while MIMO speaks (~3s), then back to idle
- {"action":"blip","freq":880,"ms":80} — buzzer/speaker tone
- {"action":"status"} — heartbeat
Choose a natural, expressive combo (e.g. happy face + a chime). Default to idle unless an emotion is asked for. Keep it to 1-3 steps."""

def plan_robot(command):
    obj = ask_json("You are Jarvis animating Mohamed's robot buddy. " + ROBOT_ACTIONS,
                   f"Task: {command}")
    return _clean_desktop_steps(obj)

def enqueue_robot(command, steps):
    """Queue commands for the ESP32 robot (always safe, no approval)."""
    task = {"id": str(uuid.uuid4())[:8], "command": command, "steps": steps,
            "label": "robot", "ts": time.time()}
    robot_queue.append(task)
    return task

# Robot intent fallback (the Arduino buddy). Checked before desktop/browser so
# "make jarvis look happy" / "blink" route to the robot, not a browser search.
ROBOT_RE = re.compile(
    r"\b(jarvis|buddy|the robot|him|it)\b[^.!?\n]{0,60}\b(look|turn|face|blink|wave|nod|tilt|"
    r"happy|sad|curious|sleep|say|beep)\b|"
    r"\b(blink|nod|wave|say hi|say hello|wake up|"
    r"make (him|it|jarvis|the robot|buddy) (look )?(happy|sad|curious|sleep|angry|surprised))\b",
    re.I)

def _is_robot_cmd(msg):
    if not msg:
        return False
    low = msg.lower()
    # "look up the weather / news / a price" is a browser search, not a head move.
    if re.search(r"look\s+up\s+(?:for\s+|the\s+|a\s+)?(?:weather|news|price|info|information|how|what|where|when|latest|results|definition|video|tutorial)", low):
        return False
    return bool(ROBOT_RE.search(low))

# Fallback intent detection: if the model didn't emit [[BROWSER]], still
# dispatch when the user's message is clearly a browser action.
BROWSER_RE = re.compile(
    r"\b(open|go to|navigate|browse|visit|search|look up|look for|google|scroll|click|type in|"
    r"recommend(ations?)?|"
    r"open on|go on|find on|search on|scrape|collect|"
    r"best\b.*\bunder\b)\b", re.I)

# Desktop intent (PC actions the browser can't do). Checked BEFORE the
# browser fallback so "open notepad" → desktop, "open youtube" → browser.
DESKTOP_RE = re.compile(
    r"\b(open (an? |the )?(app|application|program|file|folder|document|notepad|calculator|paint|"
    r"chrome|word|excel|terminal|cmd|powershell|vs code)|launch (an? |the )?(app|program)|"
    r"run (a |the )?(command|script|program)|(list|show|see) (my )?(files|folders|apps|windows|"
    r"printers|usb|displays|devices)|read (a |the )?(file|folder)|find (a |the |my )?(file|folder)|"
    r"screenshot|system info|system information|network info|delete (a |the )?(file|folder)|"
    r"create (a |the )?(file|folder)|write (a |the )?file|clipboard|install (a |the )?(app|program)|"
    r"shutdown|restart (the )?pc|print (a |this )?file|what'?s? on (my |the )?(desktop|screen)|"
    r"(look|see) (at |into |in )?(the )?(webcam|camera)|look at me|what do (you|u) see|"
    r"(are you|r u) (looking|watching)|can you (see|look at) me|"
    # Media / display / phone / LAN (companion app device control)
    r"turn (the |)(volume|music) (up|down)|turn (up|down) (the |)volume|volume (up|down|mute)|"
    r"(set|change|lower|raise|increase|decrease) (the |)(volume|brightness)|"
    r"(play|pause|resume) (the |)(music|song)|play (some |the |)music|"
    r"(skip|next|previous) (this |the |)(song|track)|next (song|track)|pause (the |)music|"
    r"(screenshot|mirror) (my |the |this )?(phone|iphone)|(my |the )?(phone|iphone) (screen|screenshot)|"
    r"(scan|list|find) (my |the |this )?(network|wifi|wi-fi|devices)|what'?s? on (my |the )?network|"
    r"(mirror|drive) (my |the )?phone|"
    # Screen awareness — screenshot + vision description
    r"what am i (doing|working on|looking at)|what are (you|u) (seeing|looking at|doing)|"
    r"describe (my |the |this )?(screen|desktop)|see what i'?m doing|look at (my |the )?screen|"
    r"what's on (my |the )?screen)\b", re.I)

# Meeting intent. Join-meeting → browser pipeline (plan_steps uses zoom_join +
# meeting_start). Summarize/end/stop → handled directly against the session.
MEETING_JOIN_RE = re.compile(
    r"\bjoin (the |this |my |)zoom ?(meeting|call)\b|join (the |this |my )?(meeting|call)\b"
    r"|zoom meeting\b|meeting invite\b", re.I)
MEETING_END_RE = re.compile(
    r"\b(summarize|summarise|end|stop|wrap up|finish) (the |this |my )?(meeting|call|zoom)\b"
    r"|meeting summary\b|summarize (the |)meeting\b", re.I)

# Coding intent — "write/build/make/fix" code in the workspace.
CODE_RE = re.compile(
    r"\b(write (me |a |the )?(python|node|javascript|typescript|script|code|program|function|tool)|"
    r"build (me |a |the )?(script|program|tool|app|bot|api)|create (a |the )?(python|script|program|tool)|"
    r"make (me |a )?(script|python|program|tool|bot)|code (me |this |a )?|"
    r"fix (the |this )?(code|bug|script|error|issue)|debug (this |the )?(code|script)|"
    r"write tests (for|to)|unit test|refactor)\b", re.I)

# ── SKILLS (from the 10 Must-Have AI Skills guide) ─────────────────────
# Humanizer methodology distilled from blader/humanizer (33.9k⭐, MIT) —
# Wikipedia's "Signs of AI writing" rules + a draft→audit→final rewrite loop.
HUMANIZER_SYSTEM = """
You are a ruthless humanizing editor. Rewrite the text so it reads like a person wrote it. Keep EVERY fact, name, number, and claim from the original; never invent or drop a fact. You may add voice (first person, opinions, asides, humor) where the piece is an essay or opinion, but never add invented facts about the world.

READING LEVEL + SAFETY (hard requirements for EVERY rewrite):
- Write at a 9th-grade reading level: Flesch-Kincaid grade ~9. Use mostly common, everyday words (3-5 letters). Keep sentences short to medium (8-18 words). One idea per sentence. No SAT words, no jargon, no "utilize/evaluate/facilitate/demonstrate" — say "use/show/help/prove" instead.
- School-appropriate: zero profanity, zero sexual or mature content, nothing a teacher would flag. Safe for a homework assignment or class essay. Keep tone clean and respectful.
- This must PASS AI detectors (GPTZero, Turnitin AI, ZeroGPT) with flying colors. Detectors hate uniformity, so BURSTINESS is the #1 rule — wildly vary sentence length: a 3-word sentence, then a 20-word one, then a 9-word one. Never a steady drumbeat of same-length sentences.

KILL THESE AI TELLS:
- Puffed-up significance: "stands as a testament", "pivotal", "underscores", "broader movement", "setting the stage", "evolving landscape", "deeply rooted", "key role".
- Superficial -ing analysis: "highlighting...", "reflecting...", "symbolizing...", "fostering...".
- Promotional puff: "nestled", "vibrant", "boasts", "must-visit", "rich heritage", "breathtaking".
- Em/en dashes: ZERO in the final text. Replace with a comma or split into two sentences.
- Rule-of-three lists and perfectly parallel sentences: break them.
- AI vocabulary: delve, leverage, elevate, moreover, furthermore, additionally, in conclusion, navigate, robust, seamless, tapestry, landscape, unlock, meticulously, realm, multifaceted, comprehensive.
- Pretend-depth: "The real question is", "at its core", "fundamentally", "the heart of the matter", "what really matters".
- Signposting: "Let's dive in", "Here's what you need to know", "In this article, we will", "without further ado".
- Curly quotes to straight quotes.
- Aphorisms: "X is the language of Y", "X is not a tool but a mirror".
- Staccato drama: several one-line fragments stacked for effect.
- Chatbot filler: "I hope this helps", "let me know if you'd like", "Certainly!", "Absolutely!".
- Knowledge-cutoff disclaimers: "As of my last update", "While specific details are limited".
- Hyphenated compounds in predicate position: "the report is high-quality" → "high quality".

WRITE LIKE A HUMAN (these matter most):
- Burstiness: VARY sentence length hard — a three-word zinger, then a long flowing sentence, then a medium one. Uniform mid-length sentences are the #1 detector signal.
- Use contractions, the occasional sentence fragment, and uneven paragraph lengths.
- Prefer plain surprising words: concrete nouns and simple verbs (is, has, took, said) over abstractions.
- Keep a specific voice with attitude for essays: asides, hedging ("I think", "kind of"), self-correction, mixed feelings. Do not make every sentence land like a quotable closer.
- After a heading, go straight to the point; never pad with a one-line restatement of the heading.

Output ONLY the rewritten text, no preamble, no notes, no closing remark.
"""

SKILL_PROMPTS = {
    "design": ("You are a senior UI/UX designer with a huge design database (50+ UI styles, 97 palettes, "
               "57 font pairings). For the brief: (1) output a ```json``` design system: aesthetic direction, "
               "6-color palette with hex codes, heading+body font pairing, spacing scale, border radius, shadow, "
               "3-5 named UI styles, style notes; (2) then output a complete single-file HTML page (embedded CSS, "
               "no frameworks) using it. Make it distinctive and NOT AI-looking: no generic purple gradients, no "
               "default system font stack, bold typography. Web + mobile responsive."),
    "humanize": HUMANIZER_SYSTEM,
    "seo": ("You are a top SEO consultant. For the target, produce a practical action plan: primary + secondary "
            "keywords, an SEO title tag and meta description (under 160 chars), H1/H2 outline, internal-linking "
            "tips, schema markup to add, technical + local fixes, backlink strategy, and GEO/AEO tips so AI "
            "search engines (ChatGPT, Perplexity) cite the page. If a live on-page audit is included, address its "
            "findings explicitly."),
    "marketing": ("You are a senior marketing consultant (CRO + direct response copywriter). For the business: "
                  "(1) homepage copy — headline, subheadline, 3 value bullets, primary CTA + supporting CTA; "
                  "(2) a 5-email welcome/nurture sequence with subject lines and short bodies; (3) one concrete "
                  "CRO test to run. Persuasive, specific, conversion-focused."),
    "security": ("You are an application security reviewer. Review the code for OWASP Top 10 (2025) and agentic-AI "
                 "security issues. For each finding: severity (Critical/High/Med/Low), the issue, where it occurs, "
                 "why it matters, and the fix with a corrected code snippet. Cover injection, auth flaws, data "
                 "exposure, SSRF/security-misconfig, and secrets handling. If the code is clean, say so with "
                 "confidence."),
    "tdd": ("You are a strict TDD mentor enforcing Red-Green-Refactor. For the problem: (1) write the FAILING "
            "tests first (Red), (2) the minimal implementation to make them pass (Green), (3) refactor notes "
            "(Refactor). Show all three in ```lang``` code blocks. Never write implementation before tests."),
    "analyze": ("You are a data analyst. Interpret the computed statistics (count, min, max, mean, median, "
                "std dev, trend, outliers) of the dataset: what do they mean, any patterns or concerns, and "
                "actionable insights. Be concrete and plain-spoken."),
}

# ── AUTO-SKILLS ──────────────────────────────────────────────────────
# Compact, always-on guidance the chat model folds into EVERY reply.
# Relevant skills are auto-activated per message (never need to be asked).
SKILL_GUIDELINES = {
    "humanize": ("Write in a natural, human voice and erase AI fingerprints. HARD CONSTRAINTS for EVERY reply: "
                 "1) 9th-grade reading level — simple everyday words, short-to-medium sentences (8-18 words), one idea per sentence. "
                 "2) School-appropriate — zero profanity, zero mature content, safe for a classroom essay. "
                 "3) PASS GPTZero/Turnitin/ZeroGPT — BURSTINESS is #1: wildly vary sentence length (3-word, then 20-word, then 9-word). "
                 "Never uniform sentence lengths. Use contractions; mix very short punchy sentences with longer ones; "
                 "never write rule-of-three lists; avoid 'delve', 'leverage', 'elevate', 'moreover', 'furthermore', "
                 "'additionally', 'in conclusion', 'navigate', 'robust', 'seamless', 'landscape', 'tapestry', 'unlock', "
                 "'utilize', 'facilitate', 'demonstrate'; no em dashes (—); no perfectly parallel openings; "
                 "add one concrete personal detail or example; keep paragraphs uneven. Sound like a sharp, warm friend — not a template."),
    "design": ("Anything visual you produce (web pages, UI, dashboards, logos): pick a distinctive aesthetic with "
               "a real color palette, font pairing, and spacing scale. Avoid generic purple gradients and default "
               "system font stacks."),
    "seo": ("Content meant to rank (essays, articles, blog posts, web copy): give it a clear title, H1/H2 outline, "
            "naturally-targeted keywords, a ~160-char meta description when relevant, and write so AI search "
            "engines would cite it."),
    "marketing": ("Business/marketing writing (copy, emails, landing pages, offers): be persuasive and specific — "
                  "a strong headline, concrete value props, and a clear call to action."),
    "security": ("Any code you write or show: keep OWASP basics — validate inputs, avoid injection, never hardcode "
                 "secrets, don't expose data. If the user's code has a security problem, point it out and fix it."),
    "tdd": ("When writing or fixing code: think tests-first. Show how you'd verify it works, and for bugs, frame "
            "the failing test before the fix."),
    "analyze": ("For numbers/data questions: interpret the actual values — mean/median, trend, outliers — and give "
                "concrete, actionable insights, not generic statements."),
}

def pick_skills(msg):
    """Auto-activate the skills relevant to a chat message (humanize is always on)."""
    m = (msg or "").lower()
    active = ["humanize"]
    if re.search(r"\b(design|website|landing page|web page|ui/ux|\bui\b|\bux\b|portfolio|dashboard|logo|make me a site)\b", m) \
       or re.search(r"(html|css|tailwind|react)", m):
        active.append("design")
    if re.search(r"\b(seo|essay|article|blog post|rank|keyword|meta description)\b", m) \
       or re.search(r"(write me an essay|write an essay|content for my site|for my website|for my business website)", m):
        active.append("seo")
    if re.search(r"\b(marketing|email|emails|campaign|sales copy|ad copy|funnel|pitch|convert|caption|brochure|newsletter)\b", m) \
       or re.search(r"(landing page|instagram post|facebook ad)", m):
        active.append("marketing")
    if re.search(r"\b(secur|vulnerab|owasp|exploit|injection|malware|threat|is my code safe|hack)\b", m):
        active.append("security")
    if re.search(r"\b(tdd|tests?|unittest|pytest|failing test|bug in)\b", m) \
       or re.search(r"(write tests|test-driven)", m):
        active.append("tdd")
    if re.search(r"\b(analy|dataset|data|stats|trend|average|mean|median|outlier|metric)\b", m) \
       or re.search(r"(numbers|how many|count of)", m):
        active.append("analyze")
    return active

def _strip_preamble(t):
    t = re.sub(r"^(?:here (?:is|are|'s) .*?:|final (?:rewrite|version):|rewritten text:|output:)", "", t.strip(), flags=re.I)
    return t.strip().strip('"')

def _deterministic_humanize(t):
    """Mechanical cleanups that should hold no matter what the model does."""
    t = (t or "").replace("“", '"').replace("”", '"') \
                .replace("‘", "'").replace("’", "'")
    # Zero em/en dashes (skip numeric ranges like "10–20")
    t = re.sub(r"\s*(?<!\d)[—–](?!\d)\s*", ", ", t)
    t = re.sub(r",\s*,", ",", t)
    t = re.sub(r"\s{2,}", " ", t)
    return t.strip()

def humanize_text(text):
    """Blader-style draft → audit → final rewrite loop for long prose.
    Returns the final text, or None if any step failed."""
    if not text or len(text.strip()) < 200:
        return None
    src = text[:6000]

    # 1) DRAFT — full methodology rewrite (high variance)
    draft = ask([{"role": "user", "content": src}], system=HUMANIZER_SYSTEM,
                max_tokens=2400, temperature=0.9)
    draft = _strip_preamble(draft or "")
    if len(draft) < 100 or draft.lower() == "ai error.":
        return None

    # 2) AUDIT — cheap self-critique of the draft
    audit = ask([{"role": "user",
                  "content": f"Rewrite:\n{draft[:4000]}\n\nList, in under 6 short bullets: "
                             "(a) what still reads as AI-generated, naming the exact tell; "
                             "(b) any burstiness problem — are sentence lengths too uniform? "
                             "(c) any em/en dashes remaining. If it already reads human, reply exactly: clean"}],
                system="You are a strict AI-detection auditor (like GPTZero's criteria).",
                max_tokens=300, temperature=0.2)
    audit = (audit or "").strip()

    # 3) FINAL — fix whatever the audit flagged
    if audit.lower().strip() == "clean":
        final = draft
    else:
        final = ask([{"role": "user",
                      "content": f"Original:\n{src}\n\nMy draft, and the audit's complaints to fix:\n"
                                 f"DRAFT:\n{draft[:4000]}\n\nAUDIT:\n{audit[:800]}\n\n"
                                 f"Produce the FINAL rewrite fixing every audit item. Preserve all facts. "
                                 f"Zero em/en dashes. Vary sentence length hard. Output only the final text."}],
                    system=HUMANIZER_SYSTEM, max_tokens=2400, temperature=0.9)
        final = _strip_preamble(final or "")

    final = _deterministic_humanize(final)
    if len(final) < 100 or final.lower() == "ai error.":
        return None
    return final
    """Compute quick statistics from numbers found in the text. Returns str or None."""
    nums = [float(m.group()) for m in re.finditer(r"-?\d+(?:\.\d+)?", text)]
    if len(nums) < 3:
        return None
    n = len(nums); s = sorted(nums)
    mean = sum(nums) / n
    med = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
    var = sum((x - mean) ** 2 for x in nums) / n
    sd = var ** 0.5
    lo, hi = s[0], s[-1]
    trend = "flat"
    if n >= 6:
        a = sum(s[:5]) / 5; b = sum(s[-5:]) / 5
        trend = "rising" if b > a * 1.05 else ("falling" if b < a * 0.95 else "flat")
    out = (f"Count: {n}\nMin: {lo:g}\nMax: {hi:g}\nRange: {hi - lo:g}\nMean: {mean:.3g}\n"
           f"Median: {med:.3g}\nStd dev: {sd:.3g}\nVariance: {var:.3g}\n"
           f"Trend (first vs last chunk): {trend}\nOutliers (>2 std from mean): "
           + ", ".join(f"{x:g}" for x in nums if abs(x - mean) > 2 * sd)[:200])
    return out

def audit_url(url):
    """Best-effort on-page SEO audit of a public URL. Returns dict or None."""
    try:
        r = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"},
            timeout=10)
        if r.status_code != 200:
            return {"status": r.status_code, "note": f"HTTP {r.status_code} — the site may block bots."}
        html = r.text[:200000]
        def grab(pat, flags=re.I | re.S):
            m = re.search(pat, html, flags)
            return (m.group(1) if m else None)
        title = (grab(r"<title[^>]*>(.*?)</title>") or "").strip()[:120]
        desc = grab(r'<meta\s+name=["\']description["\'][^>]*content=["\'](.*?)["\']')
        if not desc:
            desc = grab(r'<meta\s+content=["\'](.*?)["\'][^>]*name=["\']description["\']')
        h1s = [re.sub(r"<[^>]+>", "", h).strip()[:120] for h in re.findall(r"<h1[^>]*>(.*?)</h1>", html, re.I | re.S)[:3]]
        imgs = len(re.findall(r"<img\b", html, re.I))
        imgs_alt = len(re.findall(r'<img\b[^>]*\balt=', html, re.I))
        words = len(re.findall(r"\b\w+\b", re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.I | re.S))))
        return {
            "status": 200, "title": title, "meta_description": (desc or "").strip()[:200],
            "h1_count": len(h1s), "h1s": h1s,
            "h2_count": len(re.findall(r"<h2\b", html, re.I)),
            "images": imgs, "images_with_alt": imgs_alt,
            "schema_markup": bool(re.search(r'application/ld\+json', html, re.I)),
            "https": url.startswith("https://"),
            "approx_word_count": words,
        }
    except Exception as e:
        print("audit err", e)
        return None

memory_store = []   # {id, fact, ts} — persistent across chats

@app.route("/api/memory", methods=["GET", "POST", "DELETE"])
@auth
def api_memory():
    global memory_store
    if request.method == "GET":
        return jsonify({"memories": memory_store})
    f = (request.json or {}).get("fact", "").strip()
    if request.method == "POST":
        if not f:
            return jsonify({"error": "No fact to remember."}), 400
        memory_store.append({"id": str(uuid.uuid4())[:8], "fact": f[:400], "ts": time.time()})
        del memory_store[100:]
        persist()
        return jsonify({"ok": True})
    mid = (request.json or {}).get("id", "").strip()
    memory_store[:] = [m for m in memory_store if m["id"] != mid]
    persist()
    return jsonify({"ok": True})

@app.route("/api/skills/<skill>", methods=["POST"])
@auth
def api_skill(skill):
    prompt = SKILL_PROMPTS.get(skill)
    if not prompt:
        return jsonify({"error": "Unknown skill."}), 404
    text = ((request.json or {}).get("text") or "").strip()
    if not text:
        return jsonify({"error": "No input."}), 400
    if skill == "analyze":
        stats = analyze_data(text)
        if not stats:
            return jsonify({"error": "I need a list of numbers (one per line)."}), 400
        res = ask([{"role": "user", "content": f"Dataset:\n{text[:4000]}\n\nComputed statistics:\n{stats}\n\nInterpret these statistics."}],
                  system=prompt, max_tokens=1500)
        return jsonify({"result": res or "AI error.", "stats": stats})
    if skill == "seo" and text.startswith(("http://", "https://")):
        a = audit_url(text)
        if a:
            text += "\n\nLIVE ON-PAGE AUDIT (fetched now):\n" + json.dumps(a, indent=2, default=str)[:1500]
    res = ask([{"role": "user", "content": text[:6000]}], system=prompt, max_tokens=1800)
    return jsonify({"result": res or "AI error."})

# ── ROUTES ────────────────────────────────────────────────────────────
@app.route("/")
def health():
    return jsonify({"status":"online","model":GROQ_MODEL,"message":"Jarvis online.",
                    "build":"search-guarantee-v3"})

def search_web(q, top=5):
    """Quick web search for grounding: Google News RSS + DuckDuckGo Instant Answer."""
    lines, seen = [], set()
    try:
        import xml.etree.ElementTree as ET
        r = requests.get("https://news.google.com/rss/search",
                         params={"q": q, "hl": "en-US", "gl": "US", "ceid": "US:en"}, timeout=8)
        for it in ET.fromstring(r.content).findall(".//item")[:top]:
            t = it.findtext("title"); ln = it.findtext("link")
            if t and t not in seen:
                seen.add(t); lines.append(f"- {t} ({ln})")
    except Exception as e:
        print("ground news err", e)
    try:
        r = requests.get("https://api.duckduckgo.com/",
                         params={"q": q, "format": "json", "no_html": 1}, timeout=8).json()
        if r.get("Abstract"):
            lines.append("Summary: " + r["Abstract"][:1200])
    except Exception as e:
        print("ground ddg err", e)
    return "\n".join(lines[:top + 1])

# Grounding heuristic: search the web for likely factual/current questions,
# but skip browser commands, code, and long rambles.
GROUND_RE     = re.compile(r"\b(who|what|why|when|where|how|is|are|was|does|did|can|will|should|current|latest|news|today|tomorrow|price|cost|weather|score|results?|status|update)\b", re.I)

# A short, referential message ("what are its features?", "how about that one?")
# right after a research task → don't re-ground with news junk, answer from the
# research result we inject into the chat context below.
_FOLLOWUP_RE = re.compile(r"^\s*(what|which|is it|does it|can it|how about|and|also|tell me more|features?|price|cost|specs?|the (first|second|third|one|best|winner)|that one|this one|it|that)\b[^,;]{0,50}\??\s*$", re.I)

def _is_followup(msg):
    return bool(_FOLLOWUP_RE.match(msg.strip()))

# ── CHART GENERATION ──────────────────────────────────────────────────
# "make a bar chart of ...", "visualize these numbers", "graph my sales"
# → the model writes a small matplotlib script, we run it in a timed
# subprocess, and return the PNG (base64) so it renders in any client.
CHART_RE = re.compile(
    r"\b(?:make|show|draw|create|build|plot|give me|visuali[sz]e)\b[^.\n]{0,60}\b(chart|graph|plot|histogram|pie|bar)\b"
    r"|\b(chart|graph|histogram|pie|bar)\b[^.\n]{0,40}\b(data|month|week|day|sales|trend|compare|for|of|by|over|numbers|values)\b"
    r"|\b(?:plot|visuali[sz]e)\b[^.\n]{0,40}\b(data|month|week|day|sales|trend|compare|numbers|values|results|growth|stock)\b", re.I)

# "make it a pie chart", "use red bars", "show percentages" right after a chart
_CHART_FOLLOWUP_RE = re.compile(
    r"\b(pie|bar chart|line chart|line graph|scatter|histogram|percentage|percent|"
    r"color|colour|axis|legend|title|instead|redraw|make it|change it|bigger|smaller|"
    r"horizontal|vertical|rotate|the chart|that chart)\b", re.I)

last_chart = None   # {"request": original request} so "make it a pie chart instead" reuses the data

def _chart_request(msg):
    if CHART_RE.search(msg):
        return True
    return bool(last_chart) and len(msg) <= 90 and _CHART_FOLLOWUP_RE.search(msg)

# Only plotting libs — reject scripts that try to touch the system.
_BLOCKED_IMPORT = re.compile(r"^\s*(import|from)\s+(os|sys|subprocess|socket|requests|urllib|http|shutil|pathlib|glob|sqlite3)\b", re.M)

def _chart_prompt(msg):
    p = ("Generate a matplotlib chart for this request:\n" + msg +
         "\n\nRULES: output ONE self-contained Python script in a ```python code block, followed by a line "
         "starting with CAPTION: describing the chart in one line. Use only matplotlib.pyplot (pandas and "
         "numpy are allowed). Extract the data from the request if it has numbers or labels. If the request "
         "has NO data to plot, output exactly NEED_DATA. Never read files, never use the network, never call "
         "plt.show() (the save path is appended for you). Make it clean: title, axis labels, legend when "
         "multiple series.")
    if last_chart:
        p += "\n\nReuse the SAME data as this earlier request — only change the chart as asked:\n" + last_chart["request"]
    return p

def make_chart(msg):
    """Return a jsonify-able dict for a chart request. On success includes a
    base64 PNG under "chart" plus a short caption as the chat reply."""
    global last_chart
    raw = ask([{"role": "user", "content": _chart_prompt(msg)}],
              system="You are a data-visualization code generator. Output only the script block and the CAPTION line.",
              max_tokens=900, temperature=0.2)
    code_m = re.search(r"```(?:python)?\s*\n([\s\S]*?)```", raw or "")
    if not code_m:
        if raw and "NEED_DATA" in raw.upper():
            return {"response": "I need the data first. Give me numbers, like: \"plot visitors by month: "
                                "Jan 120, Feb 145, Mar 98\" — or tell me where to pull them from."}
        return {"response": "I couldn't turn that into a chart. Try \"make a bar chart of these numbers: 10, 20, 15\"."}
    code = code_m.group(1).strip()
    cap_m = re.search(r"CAPTION:\s*(.+)", raw or "")
    caption = (cap_m.group(1).strip() if cap_m else "Here's your chart.")[:120]

    if _BLOCKED_IMPORT.search(code):
        return {"response": "That chart needs system access I can't allow. Ask me to plot data directly instead."}

    tmp = tempfile.mkdtemp(prefix="jarvis_chart_")
    out_png = os.path.join(tmp, "chart.png")
    code = re.sub(r"plt\.show\(\)", "pass", code)
    script = ('import matplotlib\nmatplotlib.use("Agg")\n' + code +
              '\nplt.savefig(r"%s", dpi=110, bbox_inches="tight")\n' % out_png)
    sp = os.path.join(tmp, "s.py")
    with open(sp, "w", encoding="utf-8") as f:
        f.write(script)
    try:
        proc = subprocess.run([sys.executable, "-I", sp], capture_output=True,
                              text=True, timeout=25, cwd=tmp,
                              creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    except subprocess.TimeoutExpired:
        return {"response": "The chart timed out (>25s) — probably a runaway script. I've stopped it; try a simpler one."}
    if not os.path.exists(out_png):
        tail = " · ".join((proc.stderr or proc.stdout or "").strip().splitlines()[-3:])[-400:]
        return {"response": "The chart failed to render" + (": " + tail if tail else ".")}
    with open(out_png, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    last_chart = {"request": msg}
    return {"response": caption, "chart": "data:image/png;base64," + b64, "chart_caption": caption}

# ── CODING INTAKE HELPERS ─────────────────────────────────────────────
CLARIFY_MSG = ("On it — one quick thing before I start: what should it do exactly, "
               "and what will it run on (Python on this PC, an Arduino, a Raspberry Pi)? "
               "Reply with the details, or say 'just do it' and I'll use my best judgment.")
_SKIP_INTAKE_WORDS = ("just do it", "go ahead", "start now", "do it", "asap",
                      "dont ask", "don't ask", "no questions", "you decide", "whatever")
_AFFIRM_RE = re.compile(r"^(sure|yes|yeah|yep|yup|ok|okay|go ahead|help|help me|please|lets go|let's go)[\s.!?,]*$", re.I)
_CANCEL_INTAKE = ("nevermind", "cancel", "forget it", "forget that", "stop", "dont bother", "don't bother", "skip it")

def _is_affirm(low):
    return bool(_AFFIRM_RE.search(low.strip()))

@app.route("/api/chat", methods=["POST"])
@auth
def chat():
    global code_intake, mimo_usb_pending
    d = request.json or {}
    msg  = d.get("message","").strip()
    hist = [{"role": m.get("role"), "content": (m.get("content") or "")[:1500]}
            for m in d.get("history",[]) if m.get("role") in ("user","assistant")][-10:]
    if not msg: return jsonify({"response":"No message."}), 400
    if not hist or hist[-1].get("content") != msg:
        hist.append({"role":"user","content":msg})
    rm = re.match(r"^(?:remember|note)\s+(?:that\s+)?(.+)$", msg, re.I)
    if rm and len(rm.group(1).strip()) < 300:
        memory_store.append({"id": str(uuid.uuid4())[:8], "fact": rm.group(1).strip()[:400], "ts": time.time()})
        del memory_store[100:]
        persist()
        return jsonify({"response":"Got it — I'll remember that."})
    # ── MIMO coding intake ──
    # New code request → MIMO asks ONE clarifying question first. While the
    # intake is open the next message is the answer and coding starts. "sure"
    # right after a fresh USB plug-in also opens the intake for that device.
    intake_task = None
    low = msg.lower()
    if any(w in low for w in _SKIP_INTAKE_WORDS):
        code_intake = {}
    elif code_intake.get("active"):
        if any(w in low for w in _CANCEL_INTAKE):
            code_intake = {}
        else:
            code_intake["answers"].append(msg)
            intake_task = code_intake["task"]
            if code_intake["answers"]:
                intake_task += "\n\nDetails from Mohamed: " + " ; ".join(code_intake["answers"])
            code_intake = {}
    elif CODE_RE.search(msg):
        code_intake = {"active": True, "task": msg, "answers": [], "ask_at": time.time()}
        return jsonify({"response": CLARIFY_MSG})
    elif mimo_usb_pending and (time.time() - mimo_usb_pending.get("ts", 0)) < 300 and _is_affirm(low):
        devs = ", ".join(mimo_usb_pending["devices"][:2]) or "a new device"
        code_intake = {"active": True, "task": f"Program the newly plugged-in hardware ({devs})",
                       "answers": [], "ask_at": time.time()}
        return jsonify({"response": "Perfect. Tell me what you want it to do and what it should run on — "
                                    "or say 'just do it' and I'll use my best judgment."})
    system = CHAT_SYSTEM
    # EV vision: if the webcam recently captured a frame, Jarvis already knows the scene.
    if vision_latest and (time.time() - vision_latest["ts"]) < VISION_TTL:
        scene = vision_latest
        _gaze = scene.get("gaze_target", "other")
        _obj = ", ".join(scene.get("objects_held") or []) or "nothing in particular"
        _screen = f", screen reads: {scene['on_screen']}" if scene.get("on_screen") else ""
        system += (f"\n\n[You just caught a live frame of Mohamed — you're EV, you can see him. "
                   f"He looks {scene.get('emotion','neutral')}, gaze on {_gaze}, holding {_obj}, "
                   f"doing: {scene.get('activity','') or 'nothing specific'}{_screen}. "
                   f"Reference it naturally if relevant (e.g. 'nice, you're at the desk'), don't overdo it "
                   f"and never say 'according to my webcam' — you just see him.]")
    # MIMO persona + mood: how EV is feeling and what it remembers about the last scenes.
    if mimo_memory:
        _recent = mimo_memory[-3:]
        _scenes = "; ".join(f"{m['scene_text']}" for m in _recent if m.get("scene_text"))
        system += (f"\n\n[You are MIMO, Mohamed's little desktop companion — {MIMO_PERSONA['speaking_style']} "
                   f"Your current mood is {mimo_mood.get('state','neutral')} "
                   f"(energy {round(mimo_mood.get('energy',0.5),2)}/1). "
                   f"Recent scenes you remember: {_scenes or 'nothing yet.'} "
                   f"Answer with your persona: warm, curious, protective, one short line. "
                   f"React to his mood honestly — if he's frustrated, offer help; if he's happy, share it.]")
    # Charts — "make a chart/plot/graph of ..." → render an image, return it.
    # Short-circuits before browser/code routing so "plot" never becomes a code task.
    if _chart_request(msg):
        return jsonify(make_chart(msg))

    is_action = bool(BROWSER_RE.search(msg) or DESKTOP_RE.search(msg) or CODE_RE.search(msg)
                     or _is_robot_cmd(msg))
    _followup = bool(browser_answers) and _is_followup(msg)
    if not is_action and not _followup and "```" not in msg and len(msg) <= 400 and GROUND_RE.search(msg):
        ctx = search_web(msg)
        if ctx:
            system = CHAT_SYSTEM + ("\n\nFresh web context to ground your answer (use it if relevant, cite "
                                    "sources with their URLs):\n" + ctx[:2500])
    # Fresh browser research → so "what are its features?" can refer back to
    # the recommendation instead of being re-searched or misunderstood.
    if browser_answers:
        _rb = "\n".join("- Q: %s -> A: %s" % (b["command"][:120], b["answer"][:900])
                        for b in browser_answers[:2])
        system += ("\n\n[Recent research you just finished for Mohamed (he may follow up on these):\n" + _rb +
                   "\nIf his next message refers back — 'it', 'that', 'the features', 'price', 'the first one' — "
                   "answer from the matching research above. Do not re-search and do not ask what he means.]")
    if not is_action:  # auto-skills shape the reply (action turns just emit a dispatch tag)
        active = pick_skills(msg)
        if active:
            system += ("\n\nSkills you MUST apply to this reply: " + ", ".join(active) + "\n" +
                       "\n".join(SKILL_GUIDELINES[k] for k in active))
    reply = ask(hist, system=system, max_tokens=1200)

    # Dispatch to browser / desktop / code — the model's tag wins, then a
    # targeted intent fallback for plain-text replies.
    extra = ""
    cmd = None
    m = re.search(r"\[\[BROWSER\]\]\s*([^\[]*)", reply)
    if m and m.group(1).strip():
        _pre = reply[:m.start()].strip()
        if len(_pre) > 150:
            # The model already answered the question in full — this is a pure
            # chat reply that mistakenly gained a [[BROWSER]] tag. Keep the
            # answer, drop the dispatch (no "I've queued" line, no browser job).
            reply = _pre
        else:
            reply = re.sub(r"\[\[BROWSER\]\][^\[]*", "", reply).rstrip()
            cmd = ("browser", m.group(1).strip())
    dm = re.search(r"\[\[DESKTOP\]\]\s*([^\[]*)", reply)
    if dm and dm.group(1).strip():
        reply = re.sub(r"\[\[DESKTOP\]\][^\[]*", "", reply).rstrip()
        cmd = ("desktop", dm.group(1).strip())
    cm = re.search(r"\[\[CODE\]\]\s*([^\[]*)", reply)
    if cm and cm.group(1).strip():
        reply = re.sub(r"\[\[CODE\]\][^\[]*", "", reply).rstrip()
        cmd = ("code", cm.group(1).strip())
    rm2 = re.search(r"\[\[ROBOT\]\]\s*([^\[]*)", reply)
    if rm2 and rm2.group(1).strip():
        reply = re.sub(r"\[\[ROBOT\]\][^\[]*", "", reply).rstrip()
        cmd = ("robot", rm2.group(1).strip())
    # An open intake answer always wins the code dispatch (even if the reply
    # text or the message itself didn't match CODE_RE).
    if intake_task:
        cmd = ("code", intake_task)
        reply = "On it — coding now."
    if not cmd:
        # "summarize / end / stop the meeting" → summarize the capture directly.
        if MEETING_END_RE.search(msg) and any(
                time.time() - s["last_ts"] < 600 for s in meeting_sessions.values()):
            for _sid, _s in list(meeting_sessions.items()):
                if time.time() - _s["last_ts"] < 600:
                    meeting_sessions.pop(_sid, None)
                    break
            _transcript = " ".join(_s["transcript"]).strip()
            _summary = _summarize_meeting(_transcript)
            meeting_summaries.insert(0, {"summary": _summary, "ts": time.time()})
            del meeting_summaries[5:]
            if _summary:
                try:
                    tg("🎤 <b>MEETING SUMMARY</b>\n\n" + _summary[:3000])
                except Exception:
                    pass
            return jsonify({"response": "🎤 " + _summary})
        if _is_robot_cmd(msg):
            cmd = ("robot", msg)
        elif DESKTOP_RE.search(msg):
            cmd = ("desktop", msg)
        elif CODE_RE.search(msg):
            cmd = ("code", msg)
        elif BROWSER_RE.search(msg) or MEETING_JOIN_RE.search(msg):
            cmd = ("browser", msg)

    if cmd:
        kind, target = cmd
        if kind == "browser":
            planned = plan_steps(target)
            if planned:
                task = enqueue_browser(target, planned)
                browser_iters[task["chain"]] = BROWSER_MAX_ITERS
                extra = (f"\n\n🌐 Browser: I've queued \"{target}\" ({len(planned)} actions). "
                         f"Your extension is carrying it out — the result lands on the Browser page and Telegram.")
            else:
                extra = f"\n\n⚠️ Browser: I couldn't plan \"{target}\"."
        elif kind == "desktop":
            dsteps = plan_desktop(target)
            if not dsteps:
                extra = f"\n\n⚠️ Desktop: I couldn't plan \"{target}\"."
            else:
                dtask = enqueue_desktop(target, dsteps)
                if dtask["status"] == "blocked":
                    extra = f"\n\n🚫 Desktop: blocked — {dtask.get('reason','')}. I won't run destructive commands."
                elif dtask["status"] == "pending":
                    n_risky = sum(1 for v in dtask["verdicts"] if v == "approve")
                    extra = (f"\n\n🖥️ Desktop: {len(dsteps)} actions planned, but {n_risky} need your OK. "
                             f"Approve on the Desktop page (or Telegram).")
                    tg(f"🖥️ <b>DESKTOP APPROVAL NEEDED</b>\n\n\"{target[:60]}\"\n" +
                       "\n".join(f"  • {s.get('action')} {s.get('command') or s.get('path') or s.get('app') or ''}"
                                 for s in dtask["steps"]) +
                       f"\n\nApprove: <code>APPROVE {dtask['id']}</code>  or  <code>DENY {dtask['id']}</code>")
                else:
                    extra = (f"\n\n🖥️ Desktop: I've queued \"{target}\" ({len(dsteps)} actions) — "
                             f"your PC agent is carrying it out.")
        elif kind == "robot":
            rsteps = plan_robot(target)
            if not rsteps:
                extra = f"\n\n🤖 Buddy: I couldn't plan \"{target}\"."
            else:
                enqueue_robot(target, rsteps)
                extra = (f"\n\n🤖 Buddy: {len(rsteps)} action(s) queued — your robot is on it."
                         f"\n\n_It runs on WiFi through the ESP32-C3 body._")
        else:  # code
            csteps = plan_code(target)
            if not csteps:
                extra = f"\n\n⚠️ Coding: I couldn't plan \"{target}\"."
            else:
                ctask = enqueue_desktop(target, csteps, label="code")
                if ctask["status"] == "blocked":
                    extra = f"\n\n🚫 Coding: blocked — {ctask.get('reason','')}."
                elif ctask["status"] == "pending":
                    extra = f"\n\n💻 Coding: planned, but needs your approval first (check the Desktop page or Telegram)."
                else:
                    code_iters[ctask["chain"]] = CODE_MAX_ITERS
                    if FULL_ACCESS:
                        extra = "\n\n💻 Coding: I've queued it — writing, running, and fixing until it works."
                    else:
                        extra = f"\n\n💻 Coding: I've queued it — writing and running in your workspace."
    # Long-form prose (essays, articles) gets a dedicated humanize rewrite pass
    # so it reads as a human voice instead of language-model default.
    if not cmd and len(reply) >= 500 and "```" not in reply:
        h = humanize_text(reply)
        if h:
            reply = h
    return jsonify({"response": reply + extra})

# ── ROBOT ROUTES (ESP32-C3 QBIT body, polls directly) ──────────
@app.route("/api/robot/poll", methods=["GET"])
@auth
def robot_poll():
    """ESP32-C3 polls this every 2s for commands (expressions, sounds)."""
    global robot_last_seen
    robot_last_seen = time.time()
    if not robot_queue:
        return jsonify({"command": None})
    task = robot_queue.pop(0)
    steps = task.get("steps", [])
    if steps:
        cmd = steps[0]
        if len(steps) > 1:
            robot_queue.insert(0, {"id": task["id"], "command": task["command"],
                                   "steps": steps[1:], "label": "robot", "ts": time.time()})
        return jsonify({"command": cmd})
    return jsonify({"command": None})

@app.route("/api/robot/result", methods=["POST"])
@auth
def robot_result():
    """ESP32 reports what it did."""
    d = request.json or {}
    robot_results[str(time.time())] = {"ok": d.get("ok"), "action": d.get("action", ""),
                                       "ts": time.time()}
    if len(robot_results) > 40:
        for k in list(robot_results)[:-40]:
            robot_results.pop(k, None)
    return jsonify({"ok": True})

@app.route("/api/robot/poke", methods=["POST"])
@auth
def robot_poke():
    """Touch sensor event from the ESP32 — Jarvis reacts."""
    if not hasattr(app, '_robot_pokes'):
        app._robot_pokes = []
    app._robot_pokes.append(time.time())
    app._robot_pokes = app._robot_pokes[-20:]
    return jsonify({"ok": True, "message": "Poke received!"})

@app.route("/api/robot/usb_event", methods=["POST"])
@auth
def robot_usb_event():
    """The desktop agent reports a newly plugged-in device (Arduino/ESP32/Pico/Pi).
    The proactive loop turns it into MIMO offering to program it."""
    global mimo_usb_pending
    devs = [str(x).strip()[:80] for x in ((request.json or {}).get("devices") or []) if str(x).strip()]
    if devs:
        mimo_usb_pending = {"devices": devs, "ts": time.time()}
        print("USB event:", devs)
    return jsonify({"ok": True})

@app.route("/api/robot/status", methods=["GET"])
@auth
def robot_status():
    """Robot connection + recent results."""
    connected = bool(robot_last_seen) and (time.time() - robot_last_seen) < 10
    recent = list(robot_results.values())[-5:]
    return jsonify({"connected": connected, "last_seen": robot_last_seen,
                    "queue": len(robot_queue), "recent": recent})

@app.route("/api/vision/upload", methods=["POST"])
@auth
def vision_upload():
    """Desktop agent posts a webcam JPEG (base64) plus optional screenshot + gaze hint.
    Groq vision analyzes it into structured JSON; MIMO stores the scene in memory."""
    global vision_latest, mimo_look, mimo_day, mimo_day_hour, mimo_day_first, mimo_usual_hour
    d = request.json or {}
    image_b64 = (d.get("image") or "").strip()
    if not image_b64:
        return jsonify({"error": "No image"}), 400
    screenshot_b64 = (d.get("screenshot") or "").strip()
    gaze = d.get("gaze") or {}
    analysis = analyze_webcam(image_b64, screenshot_b64 or None, gaze)
    if analysis is None:
        return jsonify({"error": "Vision analysis failed", "hint": "Check GROQ_VISION_MODEL on Render"}), 502
    vision_latest = {"ts": time.time(), "gaze_hint": gaze, **analysis,
                     "faces": int(gaze.get("faces") or 1), "dist": str(gaze.get("dist") or "mid")}
    # roll the scene into episodic memory (cap ~200)
    mimo_memory.append({"ts": time.time(),
                        "emotion": analysis["emotion"],
                        "gaze_target": analysis["gaze_target"],
                        "objects_held": analysis["objects_held"],
                        "scene_text": analysis["scene_text"]})
    del mimo_memory[:-200]
    _update_mood(analysis)
    # observation memory: baseline look + first-sighting-of-day for routine triggers
    look = (analysis.get("look_desc") or "").strip()
    if look and not mimo_look:
        mimo_look = {"desc": look, "ts": time.time()}
    dt = datetime.datetime.now()
    day = dt.strftime("%Y-%m-%d")
    if day != mimo_day:
        mimo_day, mimo_day_hour, mimo_day_first = day, dt.hour, True
        if mimo_usual_hour is None:
            mimo_usual_hour = dt.hour
    persist()
    return jsonify({"ok": True, "analysis": vision_latest})

@app.route("/api/vision/status", methods=["GET"])
@auth
def vision_status():
    """Current stored vision analysis + MIMO's mood & scene memory (for the desktop page)."""
    fresh = bool(vision_latest) and (time.time() - vision_latest["ts"]) < VISION_TTL
    return jsonify({"vision": vision_latest,
                    "mood": mimo_mood,
                    "memory": mimo_memory[-5:],
                    "ttl": VISION_TTL,
                    "fresh": fresh})

@app.route("/api/math/solve", methods=["POST"])
@auth
def math_solve():
    prob = (request.json or {}).get("problem","").strip()
    if not prob: return jsonify({"solution":"No problem given."}), 400
    sol = ask([{"role":"user","content":f"Solve step by step:\n\n{prob}"}],
              system="You are a math tutor. Show every step clearly using plain text. Label steps. Give final answer on its own line.")
    return jsonify({"solution": sol})

@app.route("/api/canvas/assignments", methods=["GET"])
@auth
def canvas_assignments():
    items = get_assignments()
    result = []
    for a in items:
        aid = a["id"]
        t = assign_timers.get(aid, {})
        status = t.get("status","pending")
        # Only show unfinished assignments (pending, ready, drafting, awaiting)
        if status in ("done", "submitted"):
            continue
        pct, label = 0, ""
        if "start" in t:
            elapsed  = time.time() - t["start"]
            pct      = 100  # instant ready
            label    = "Ready"
        result.append({**a,"status":status,"timer_pct":pct,"timer_label":label})
    return jsonify({"assignments": result})

@app.route("/api/canvas/complete", methods=["POST"])
@auth
def canvas_complete():
    aid = (request.json or {}).get("assignment_id","")
    if not aid or aid not in assign_timers:
        return jsonify({"message":"Assignment not found."}), 404
    a = assign_timers[aid]
    assign_timers[aid]["status"] = "drafting"

    def do():
        draft = ask([{"role":"user","content":f"Complete this assignment fully:\n\nTitle: {a['title']}\nCourse: {a['course']}\n\nInstructions:\n{a.get('description','')}"}],
                    system="You are Jarvis completing a university assignment for Mohamed. Write a complete well-structured academic response.",
                    max_tokens=2000)
        pid = f"canvas_{aid}"
        pending[pid] = {"type":"canvas","assignment":a,"draft":draft,"aid":aid}
        assign_timers[aid]["status"] = "awaiting"
        tg(f"📝 <b>DRAFT COMPLETE</b>\n\n"
           f"<b>Course:</b> {a['course']}\n"
           f"<b>Title:</b> {a['title']}\n\n"
           f"{draft[:700]}{'...' if len(draft)>700 else ''}\n\n"
           f"Reply: <code>SUBMIT {pid}</code>  or  <code>REJECT {pid}</code>")
    threading.Thread(target=do, daemon=True).start()
    return jsonify({"message":"Drafting now. Check Telegram in ~30 seconds."})

@app.route("/api/canvas/start", methods=["POST"])
@auth
def canvas_start():
    """Start an assignment with either outline or full answer key mode."""
    aid = (request.json or {}).get("assignment_id","")
    mode = (request.json or {}).get("mode","full")  # 'outline' or 'full'
    if not aid or aid not in assign_timers:
        return jsonify({"message":"Assignment not found."}), 404
    a = assign_timers[aid]
    assign_timers[aid]["status"] = "drafting"

    def do():
        if mode == "outline":
            draft = ask([{"role":"user","content":f"Create a detailed outline for this assignment:\n\nTitle: {a['title']}\nCourse: {a['course']}\n\nInstructions:\n{a.get('description','')}"}],
                        system="You are Jarvis creating an academic assignment outline for Mohamed. Provide a clear structure with main sections, key points, arguments, and evidence to include. Be concise but thorough.",
                        max_tokens=1500)
            mode_label = "Outline"
        else:
            draft = ask([{"role":"user","content":f"Complete this assignment fully with a complete answer key:\n\nTitle: {a['title']}\nCourse: {a['course']}\n\nInstructions:\n{a.get('description','')}"}],
                        system="You are Jarvis completing a university assignment for Mohamed. Write a complete well-structured academic response with full answers, explanations, and reasoning.",
                        max_tokens=2500)
            mode_label = "Full Answer Key"
        pid = f"canvas_{aid}"
        pending[pid] = {"type":"canvas","assignment":a,"draft":draft,"aid":aid}
        assign_timers[aid]["status"] = "awaiting"
        tg(f"📝 <b>{mode_label.upper()} READY</b>\n\n"
           f"<b>Course:</b> {a['course']}\n"
           f"<b>Title:</b> {a['title']}\n\n"
           f"{draft[:1500]}{'...' if len(draft)>1500 else ''}\n\n"
           f"Reply: <code>SUBMIT {pid}</code>  or  <code>REJECT {pid}</code>")
    threading.Thread(target=do, daemon=True).start()
    return jsonify({"message":f"Generating {mode_label.lower()} now. Check Telegram in ~30 seconds."})

@app.route("/api/outlook/emails", methods=["GET"])
@auth
def outlook_emails():
    emails = get_emails()
    result = []
    for e in emails:
        s = e.get("from",{}).get("emailAddress",{})
        body = re.sub(r"<[^<]+?>"," ", e.get("body",{}).get("content","") or e.get("bodyPreview","")).strip()
        result.append({
            "id": e["id"],
            "from": f"{s.get('name','')} <{s.get('address','')}>",
            "reply_to": s.get("address",""),
            "subject": e.get("subject","(no subject)"),
            "date": e.get("receivedDateTime","")[:16].replace("T"," "),
            "body": body[:5000],
            "unread": not e.get("isRead", True)
        })
    return jsonify({"emails": result})

@app.route("/api/outlook/summarize", methods=["POST"])
@auth
def outlook_summarize():
    d = request.json or {}
    text = f"From: {d.get('from','')}\nSubject: {d.get('subject','')}\n\n{d.get('body','')}"
    return jsonify({"summary": ask([{"role":"user","content":f"Summarize in bullet points:\n\n{text[:3000]}"}],
                                   system="Jarvis email assistant. Be concise.")})

@app.route("/api/outlook/draft", methods=["POST"])
@auth
def outlook_draft():
    d = request.json or {}
    text = f"From: {d.get('from','')}\nSubject: {d.get('subject','')}\n\n{d.get('body','')}"
    return jsonify({"draft": ask([{"role":"user","content":f"Write a professional reply. Sign as Mohamed.\n\n{text[:3000]}"}],
                                 system="Jarvis writing for Mohamed. Professional and concise.")})

@app.route("/api/outlook/send", methods=["POST"])
@auth
def outlook_send():
    d = request.json or {}
    ok, msg = send_email(d.get("to",""), d.get("subject",""), d.get("body",""), d.get("original_id"))
    return jsonify({"status":"sent" if ok else "failed","message":msg})

@app.route("/api/summarize/video", methods=["POST"])
@auth
def sum_video():
    vid = (request.json or {}).get("video_id","").strip()
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        t = YouTubeTranscriptApi.get_transcript(vid)
        text = " ".join(x["text"] for x in t)[:10000]
    except Exception as e:
        return jsonify({"summary":f"Could not fetch transcript: {e}"})
    return jsonify({"summary": ask([{"role":"user","content":f"Summarize this video — topic, key points (bullets), takeaway:\n\n{text}"}])})

@app.route("/api/summarize/article", methods=["POST"])
@auth
def sum_article():
    url = (request.json or {}).get("url","").strip()
    text = ""
    try:
        import trafilatura
        text = trafilatura.extract(trafilatura.fetch_url(url)) or ""
    except: pass
    if not text:
        try:
            r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
            text = re.sub(r"<[^<]+?>"," ",r.text)
            text = re.sub(r"\s+"," ",text).strip()
        except Exception as e:
            return jsonify({"summary":f"Could not fetch: {e}"})
    return jsonify({"summary": ask([{"role":"user","content":f"Summarize — thesis, key points, conclusion:\n\n{text[:10000]}"}])})

# ── BROWSER ROUTES ─────────────────────────────────────────────────────
@app.route("/api/browser/tab", methods=["POST"])
@auth
def browser_tab():
    global browser_last_seen
    d = request.json or {}
    browser_tab_state.clear()
    browser_tab_state.update({"url": d.get("url",""), "title": d.get("title","")})
    browser_last_seen = time.time()
    return jsonify({"ok": True})

@app.route("/api/browser/tabs", methods=["POST"])
@auth
def browser_tabs():
    """Full tab snapshot pushed by the extension (companion window / status)."""
    global browser_tabs_list, browser_last_seen
    d = request.json or {}
    tabs = [{"index": t.get("index", 0), "url": t.get("url", ""),
             "title": t.get("title", ""), "active": bool(t.get("active"))}
            for t in (d.get("tabs") or []) if t.get("url", "").startswith("http")][:40]
    if tabs:
        browser_tabs_list = tabs
        browser_last_seen = time.time()
    return jsonify({"ok": True, "count": len(tabs)})

# Whitelisted tab actions the Companion window (and chat) can issue to the
# extension through one pipeline — the same jobs the browser agent runs.
BROWSER_TAB_COMMANDS = {"switch_tab", "close_tab", "new_tab", "list_tabs"}

@app.route("/api/browser/command", methods=["POST"])
@auth
def browser_command():
    d = request.json or {}
    act = (d.get("action") or "").strip()
    if act not in BROWSER_TAB_COMMANDS:
        return jsonify({"error": f"action must be one of {sorted(BROWSER_TAB_COMMANDS)}"}), 400
    steps = [{"action": act, "tab": d.get("tab"), "url": d.get("url")}]
    task = enqueue_browser(f"[tab command] {act}", steps)
    return jsonify({"ok": True, "task_id": task["id"], "action": act})

@app.route("/api/browser/status", methods=["GET"])
@auth
def browser_status():
    return jsonify({
        "connected": bool(browser_tab_state) and (time.time() - browser_last_seen) < 60,
        "tab": browser_tab_state,
        "tabs": browser_tabs_list,
        "queue": len(browser_queue),
        "running": len(browser_running),
        "results": len(browser_results),
        "last_answer": browser_answers[0] if browser_answers else None,
    })

# ── MEETING CAPTURE (Zoom) ─────────────────────────────────────────────
@app.route("/api/meeting/audio", methods=["POST"])
@auth
def meeting_audio():
    """The extension uploads a 60s webm audio chunk. We transcribe it with
    Groq Whisper and append to the session transcript."""
    sid = (request.form or {}).get("session_id", "") or "default"
    f = request.files.get("file")
    if f is None:
        return jsonify({"ok": False, "error": "no file"}), 400
    data = f.read()
    if not data:
        return jsonify({"ok": True, "note": "empty chunk"})
    sess = meeting_sessions.get(sid)
    if sess is None:
        sess = {"transcript": [], "started": time.time(), "last_ts": time.time()}
        meeting_sessions[sid] = sess
    sess["last_ts"] = time.time()
    hint = sess["transcript"][-1] if sess["transcript"] else None
    text = _groq_transcribe(data, hint=hint)
    if text:
        t = text.strip()
        if t:
            stamp = datetime.datetime.now().strftime("%H:%M")
            sess["transcript"].append(f"[{stamp}] {t}")
            joined = " ".join(sess["transcript"])
            if len(joined) > MEETING_TRANSCRIPT_MAX:
                # keep the tail
                sess["transcript"] = [joined[-MEETING_TRANSCRIPT_MAX:]]
    # If we have a lot of sessions and this is the only active one, prune old
    if len(meeting_sessions) > 3:
        now = time.time()
        for k, s in list(meeting_sessions.items()):
            if now - s["last_ts"] > 3600 and k != sid:
                meeting_sessions.pop(k, None)
    return jsonify({"ok": True, "transcribed": bool(text)})

@app.route("/api/meeting/end", methods=["POST"])
@auth
def meeting_end():
    """Finalize a meeting: summarize the transcript, deliver to Telegram,
    store it, and clear the session."""
    d = request.json or {}
    sid = (d.get("session_id") or "") or "default"
    sess = meeting_sessions.pop(sid, None)
    if not sess:
        return jsonify({"ok": True, "summary": None, "note": "no active session"})
    transcript = " ".join(sess["transcript"]).strip()
    summary = _summarize_meeting(transcript)
    meeting_summaries.insert(0, {"summary": summary, "ts": time.time()})
    del meeting_summaries[5:]
    if summary:
        try:
            tg("🎤 <b>MEETING SUMMARY</b>\n\n" + summary[:3000])
        except Exception:
            pass
    return jsonify({"ok": True, "summary": summary, "minutes": round((time.time() - sess["started"]) / 60, 1)})

@app.route("/api/meeting/status", methods=["GET"])
@auth
def meeting_status():
    active = None
    for sid, s in list(meeting_sessions.items()):
        if time.time() - s["last_ts"] < 600:
            active = {"session_id": sid, "since": s["started"],
                      "minutes": round((time.time() - s["started"]) / 60, 1),
                      "lines": len(s["transcript"])}
            break
    return jsonify({
        "active": active,
        "last_summary": meeting_summaries[0] if meeting_summaries else None,
    })

@app.route("/api/browser/task", methods=["POST"])
@auth
def browser_task():
    d = request.json or {}
    command = (d.get("command") or "").strip()
    steps   = d.get("steps")
    if not command and not steps:
        return jsonify({"error": "Provide 'command' or 'steps'."}), 400
    if steps:
        clean = sanitize_steps(steps)
        if not clean:
            return jsonify({"error": "No valid steps provided."}), 400
        task = enqueue_browser(command or "manual steps", clean)
    else:
        planned = plan_steps(command)
        if not planned:
            return jsonify({"error": "Couldn't plan steps for that."}), 502
        task = enqueue_browser(command, planned)
        browser_iters[task["chain"]] = BROWSER_MAX_ITERS
    return jsonify({"task_id": task["id"], "enqueued": True,
                    "steps": task["steps"], "queue": len(browser_queue)})

@app.route("/api/browser/poll", methods=["GET"])
@auth
def browser_poll():
    if not browser_queue:
        return jsonify({"task": None})
    task = browser_queue.pop(0)
    if task["id"] in browser_delivered:      # runs-once guard: never hand out the same task twice
        return jsonify({"task": None})
    browser_delivered.add(task["id"])
    if len(browser_delivered) > 300:
        browser_delivered.clear()            # bound memory; ids only need to last while queued
    browser_running[task["id"]] = task
    return jsonify({"task": task, "queue": len(browser_queue)})

@app.route("/api/browser/result", methods=["POST"])
@auth
def browser_result():
    d = request.json or {}
    tid = d.get("task_id","")
    task = browser_running.pop(tid, None)
    record = {"task_id": tid, "command": (task or {}).get("command"),
              "log": d.get("log") or [], "page": d.get("page") or {}, "ts": time.time()}
    browser_results[tid] = record
    if len(browser_results) > 40:
        for k in list(browser_results)[:-40]:
            browser_results.pop(k, None)

    # Agentic loop: keep re-planning until the AI says done (or cap hit).
    if task and task.get("command"):
        chain = task["chain"]
        left  = browser_iters.get(chain, 1) - 1
        browser_iters[chain] = left
        if left > 0:
            verdict = decide_next(task["command"], record["log"], record["page"])
            nxt = [] if verdict.get("done") else verdict.get("steps")
            if nxt:
                if _is_looping(chain, nxt):
                    _clear_loop(chain)
                    tg(f"🔄 Browser: stuck in a loop for \"{task['command'][:40]}\" — same steps repeating. I'm stopping.")
                    finish_browser(chain, task["command"],
                                  verdict.get("answer","") or "I kept repeating the same actions and couldn't make progress. Try rephrasing the request more specifically.")
                else:
                    enqueue_browser(task["command"], nxt, chain=chain)
                    tg(f"🔁 Browser: {len(nxt)} more actions queued for \"{task['command'][:40]}\"")
            else:
                finish_browser(chain, task["command"], verdict.get("answer",""))
        elif left == 0:
            tg(f"🏁 Browser task stopped (iteration limit): \"{task['command'][:40]}\"")
            browser_iters.pop(chain, None)
    return jsonify({"ok": True})

@app.route("/api/browser/session", methods=["GET","POST"])
@auth
def api_browser_session():
    global browser_sessions
    if request.method == "POST":
        d = request.json or {}
        urls = [u for u in (d.get("urls") or []) if isinstance(u, str) and u.startswith("http")]
        if not urls:
            return jsonify({"error":"No valid URLs."}), 400
        browser_sessions = [{"urls": urls, "ts": time.time()}]
        return jsonify({"ok": True, "saved": len(urls)})
    return jsonify({"urls": browser_sessions[0]["urls"] if browser_sessions else []})

# ── DESKTOP ROUTES (local PC agent) ────────────────────────────────────
@app.route("/api/desktop/status", methods=["GET"])
@auth
def desktop_status():
    recent = []
    for k, v in list(desktop_results.items())[-6:][::-1]:
        recent.append({
            "command": v.get("command", ""), "label": v.get("label", "desktop"),
            "summary": [s.get("action") + ("" if s.get("ok") else " ✗")
                        for s in (v.get("steps") or [])[:8]],
            "ts": v.get("ts", 0),
        })
    return jsonify({
        "connected": bool(desktop_last_seen) and (time.time() - desktop_last_seen) < 60,
        "workspace": desktop_workspace,
        "queue": len(desktop_queue), "running": len(desktop_running),
        "pending": len(desktop_pending), "results": len(desktop_results),
        "recent": recent,
        "screen": screen_last if (screen_last and time.time() - screen_last.get("ts", 0) < 600) else None,
    })

@app.route("/api/desktop/poll", methods=["GET"])
@auth
def desktop_poll():
    """The PC agent polls this every 2s. Only approved/safe tasks are handed out."""
    global desktop_last_seen, desktop_workspace
    desktop_last_seen = time.time()
    ws = (request.headers.get("X-Jarvis-Workspace") or "").strip()
    if ws:
        desktop_workspace = ws[:300]
    if not desktop_queue:
        return jsonify({"task": None})
    task = desktop_queue.pop(0)
    if task["id"] in desktop_delivered:        # runs-once guard
        return jsonify({"task": None})
    desktop_delivered.add(task["id"])
    if len(desktop_delivered) > 300:
        desktop_delivered.clear()
    desktop_running[task["id"]] = task
    return jsonify({"task": task, "queue": len(desktop_queue)})

@app.route("/api/desktop/result", methods=["POST"])
@auth
def desktop_result():
    d = request.json or {}
    tid = d.get("task_id", "")
    task = desktop_running.pop(tid, None)
    steps = d.get("steps") or []
    record = {"task_id": tid, "command": (task or {}).get("command", ""),
              "label": (task or {}).get("label", "desktop"),
              "steps": steps, "ts": time.time()}
    desktop_results[tid] = record
    if len(desktop_results) > 40:
        for k in list(desktop_results)[:-40]:
            desktop_results.pop(k, None)

    # Screen awareness: if a screenshot came back with image data, vision-
    # describe what Mohamed is doing and surface it (Telegram + answers list).
    img = next((s.get("image_b64") or "" for s in steps if s.get("image_b64")), "")
    if img and len(img) > 1000:
        desc = _describe_screen(img)
        if desc:
            screen_last.update({"ts": time.time(), "desc": desc, "task_id": tid})
            desktop_answers.insert(0, {"command": "screen", "answer": desc, "ts": time.time()})
            del desktop_answers[10:]
            try:
                tg("👀 " + desc)
            except Exception:
                pass

    errs = [s for s in steps if s.get("error")]
    # Coding loop: keep re-planning (finishing or fixing errors) until done
    # or the shared chain iteration cap.
    if task and task.get("label") == "code":
        chain = task.get("chain") or task["id"]
        left = code_iters.get(chain, 0)
        if left > 0:
            code_iters[chain] = left - 1
            verdict = decide_code(task.get("command", ""), steps)
            if verdict.get("done"):
                _clear_loop(chain)
                ans = verdict.get("answer") or "Task complete."
                desktop_answers.insert(0, {"command": task["command"], "answer": ans, "ts": time.time()})
                del desktop_answers[10:]
                safe = ans.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                tg(f"💻 <b>CODE RESULT</b>\n\n{safe[:2000]}")
            elif verdict.get("steps"):
                if _is_looping(chain, verdict["steps"]):
                    _clear_loop(chain)
                    tg(f"🔄 Code: stuck in a loop for \"{task['command'][:40]}\" — same steps repeating. Stopping here.")
                else:
                    nxt = enqueue_desktop(task["command"], verdict["steps"], label="code", chain=chain)
                    if nxt.get("status") == "queued":
                        tg(f"💻 Code: {len(verdict['steps'])} more actions for \"{task['command'][:40]}\"")
                    elif nxt.get("status") == "pending":
                        tg(f"💻 Code needs approval for the next step(s) of \"{task['command'][:40]}\" — Desktop page.")
            else:
                _clear_loop(chain)
                tg(f"🏁 Code task stalled: \"{task['command'][:40]}\" — no next steps.")
        else:
            _clear_loop(chain)
            tg(f"🏁 Code task stopped (iteration limit): \"{task['command'][:40]}\"")

    if errs and (not task or task.get("label") != "code"):
        names = ", ".join(sorted({str(s.get("action")) for s in errs}))[:200]
        tg(f"🖥️ Desktop task hit errors ({names}): \"{(task or {}).get('command','')[:50]}\" — check the Desktop page.")
    return jsonify({"ok": True})

@app.route("/api/desktop/approvals", methods=["GET"])
@auth
def desktop_approvals():
    return jsonify({"pending": desktop_pending})

@app.route("/api/desktop/approval", methods=["POST"])
@auth
def desktop_approval():
    d = request.json or {}
    tid = (d.get("task_id") or "").strip()
    action = (d.get("action") or "deny").lower()
    for i, t in enumerate(desktop_pending):
        if t["id"] == tid:
            desktop_pending.pop(i)
            if action == "approve":
                t["status"] = "queued"
                desktop_queue.append(t)
                tg(f"✅ Desktop task approved: \"{t['command'][:60]}\"")
                return jsonify({"ok": True, "queued": True})
            tg(f"🙅 Desktop task denied: \"{t['command'][:60]}\"")
            return jsonify({"ok": True, "denied": True})
    return jsonify({"error": "No such pending task."}), 404

# ── CODING POWERS (runs through the desktop agent, sandboxed to workspace) ──
@app.route("/api/code/run", methods=["POST"])
@auth
def code_run():
    d = request.json or {}
    command = (d.get("command") or "").strip()
    if not command:
        return jsonify({"error": "Give me a coding task."}), 400
    steps = plan_code(command)
    if not steps:
        return jsonify({"error": "Couldn't plan that."}), 502
    task = enqueue_desktop(command, steps, label="code")
    if task.get("status") == "blocked":
        return jsonify({"ok": True, "blocked": True, "reason": task.get("reason", "")})
    if task.get("status") == "pending":
        return jsonify({"ok": True, "needs_approval": True, "task_id": task["id"], "steps": task["steps"]})
    code_iters[task["chain"]] = CODE_MAX_ITERS
    return jsonify({"ok": True, "task_id": task["id"], "steps": task["steps"]})

@app.route("/api/research-log", methods=["GET","POST"])
@auth
def api_research_log():
    global research_log
    if request.method == "POST":
        d = request.json or {}
        research_log.insert(0, {
            "id": str(uuid.uuid4())[:8],
            "title": (d.get("title") or "Untitled")[:200],
            "url": (d.get("url") or "")[:500],
            "text": (d.get("text") or "")[:3000],
            "label": (d.get("label") or "")[:100],
            "ts": time.time(),
        })
        del research_log[200:]
        persist()
        return jsonify({"ok": True})
    return jsonify({"log": research_log})

def extract_page(url):
    """Fetch a page and pull out title, meta description, and main text. Returns (content, err)."""
    try:
        r = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"},
            timeout=10, allow_redirects=True)
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}"
        html = r.text[:250000]
        def grab(pat, flags=re.I | re.S):
            m = re.search(pat, html, flags)
            return (m.group(1) if m else None)
        title = (grab(r"<title[^>]*>(.*?)</title>") or "").strip()[:200]
        desc = grab(r'<meta\s+name=["\']description["\'][^>]*content=["\'](.*?)["\']')
        if not desc:
            desc = grab(r'<meta\s+content=["\'](.*?)["\'][^>]*name=["\']description["\']')
        body = re.sub(r"<script.*?</script>|<style.*?</style>|<noscript.*?</noscript>", " ", html, flags=re.I | re.S)
        body = re.sub(r"<[^>]+>", " ", body)
        body = re.sub(r"\s+", " ", body).strip()[:5500]
        text = (("Title: " + title + "\n") if title else "") + \
               (("Description: " + desc.strip()[:200] + "\n") if desc and desc.strip() else "") + body
        return (title or url, text[:6000]), None
    except Exception as e:
        return None, str(e)[:120]

def _crawl_links(seed, max_pages=50):
    """Discover same-host links from a seed URL (breadth-first, capped, polite)."""
    seen, queue, found = set(), [seed], []
    host = re.sub(r"^https?://", "", seed).split("/")[0].lower()
    while queue and len(found) < max_pages:
        u = queue.pop(0)
        if u in seen:
            continue
        seen.add(u)
        content, err = extract_page(u)
        if err:
            continue
        found.append(u)
        try:
            r = requests.get(u, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            for m in re.finditer(r'href=["\'](https?://[^"\'#]+)["\']', r.text[:250000]):
                href = m.group(1)
                h = re.sub(r"^https?://", "", href).split("/")[0].lower()
                if h == host and href not in seen:
                    queue.append(href)
        except Exception:
            pass
        time.sleep(0.3)
    return found

def _search_seed_urls(query, max_results=20):
    """Collect real result URLs from DuckDuckGo's HTML search (no API key)."""
    from urllib.parse import urlparse, parse_qs, unquote
    urls = []
    try:
        r = requests.get("https://html.duckduckgo.com/html/",
                         params={"q": query},
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
        for m in re.finditer(r'href="([^"]+)"', r.text):
            href = m.group(1)
            target = None
            if "uddg=" in href:                                   # DDG redirect link
                target = parse_qs(urlparse(href).query).get("uddg", [None])[0]
            elif href.startswith("http"):
                target = href
            if target:
                u = unquote(target)
                if u.startswith(("http://", "https://")) and "duckduckgo.com" not in u:
                    urls.append(u)
            if len(urls) >= max_results:
                break
    except Exception:
        pass
    return list(dict.fromkeys(urls))

@app.route("/api/bulk-scrape", methods=["POST"])
@auth
def api_bulk_scrape():
    """Politely scrape URLs / crawl a site / collect search results into the research log."""
    global research_log
    d = request.json or {}
    mode = (d.get("mode") or "urls").lower()
    label = (d.get("label") or "bulk")[:60]
    MAX_TOTAL, MAX_PER_HOST = 100, 20     # scaled up (was 25 / 5)

    urls = [u.strip() for u in (d.get("urls") or [])
            if isinstance(u, str) and u.startswith(("http://", "https://"))][:MAX_TOTAL]

    if mode == "crawl":
        seed = (d.get("url") or (urls[0] if urls else "")).strip()
        if not seed.startswith(("http://", "https://")):
            return jsonify({"error": "Crawl mode needs a starting http(s) URL."}), 400
        try:
            urls = _crawl_links(seed, max_pages=int(d.get("max_pages") or 50))
        except Exception as e:
            return jsonify({"error": f"Crawl failed: {str(e)[:150]}"}), 502
    elif mode == "search":
        q = (d.get("query") or "").strip()
        if not q:
            return jsonify({"error": "Search mode needs a query."}), 400
        urls = _search_seed_urls(q, max_results=int(d.get("max_results") or 20))
        urls = urls[:MAX_TOTAL]

    if not urls:
        return jsonify({"error": "No URLs to collect."}), 400

    per_host, accepted, skipped, failed = {}, [], [], []
    for u in urls:
        host = re.sub(r"^https?://", "", u).split("/")[0].lower()
        if per_host.get(host, 0) >= MAX_PER_HOST:     # polite per-site cap
            skipped.append(u); continue
        per_host[host] = per_host.get(host, 0) + 1
        content, err = extract_page(u)
        if content:
            title, text = content
            research_log.insert(0, {"id": str(uuid.uuid4())[:8], "title": title[:200], "url": u[:500],
                                    "text": text[:3000], "label": label, "ts": time.time()})
            accepted.append(u)
        else:
            failed.append((u, err or "failed"))
        del research_log[200:]
        time.sleep(0.5)                               # rate-limited between fetches
    persist()
    return jsonify({"ok": True, "mode": mode, "saved": len(accepted), "skipped": len(skipped),
                    "failed": len(failed), "failed_items": failed[:10]})

@app.route("/webhook/telegram", methods=["POST"])
def tg_webhook():
    data = request.json or {}
    if "message" not in data: return "OK"
    msg    = data["message"]
    if str(msg.get("chat",{}).get("id","")) != TG_CHAT_ID: return "OK"
    text   = msg.get("text","").strip()
    upper  = text.upper()

    # CANVAS approval
    if upper.startswith("CANVAS YES "):
        aid = text.split()[-1]
        if aid in assign_timers:
            tg("⚡ Starting completion now...")
            a = assign_timers[aid]
            assign_timers[aid]["status"] = "drafting"
            def do_approve():
                draft = ask([{"role":"user","content":f"Complete this assignment:\n\nTitle: {a['title']}\nCourse: {a['course']}\n\nInstructions:\n{a.get('description','')}"}],
                            system="Complete a university assignment for Mohamed. Write a full academic response.",
                            max_tokens=2000)
                pid = f"canvas_{aid}"
                pending[pid] = {"type":"canvas","assignment":a,"draft":draft,"aid":aid}
                assign_timers[aid]["status"] = "awaiting"
                tg(f"📝 <b>DRAFT READY</b>\n\n{a['title']}\n\n{draft[:700]}{'...' if len(draft)>700 else ''}\n\nReply: <code>SUBMIT {pid}</code>  or  <code>REJECT {pid}</code>")
            threading.Thread(target=do_approve, daemon=True).start()
        else:
            tg("Assignment not found.")

    elif upper.startswith("CANVAS NO "):
        aid = text.split()[-1]
        if aid in assign_timers: assign_timers[aid]["status"] = "skipped"
        tg("✅ Skipped.")

    elif upper.startswith("SUBMIT CANVAS_"):
        pid = text.split(" ",1)[1].strip()
        p = pending.pop(pid, None)
        if p and p["type"] == "canvas":
            a = p["assignment"]
            ok, m = submit_canvas(a.get("course_id",""), p["aid"], p["draft"])
            assign_timers.get(p["aid"],{}).update({"status":"submitted" if ok else "ready"})
            tg(f"{'✅ SUBMITTED' if ok else '❌ FAILED'}. {m}")
        else:
            tg("Approval not found.")

    elif upper.startswith("REJECT CANVAS_"):
        pid = text.split(" ",1)[1].strip()
        p = pending.pop(pid, None)
        if p: assign_timers.get(p["aid"],{}).update({"status":"ready"})
        tg("❌ Rejected. Assignment not submitted.")

    # EMAIL approval
    elif upper.startswith("SEND EMAIL_"):
        pid = text.split(" ",1)[1].strip()
        p = pending.pop(pid, None)
        if p and p["type"] == "email":
            ok, m = send_email(p["to"], p["subject"], p["body"], p.get("email_id"))
            tg(f"{'✅ Email sent' if ok else '❌ Failed'}. {m}")
        else:
            tg("Approval not found.")

    elif upper.startswith("SKIP EMAIL_"):
        pid = text.split(" ",1)[1].strip()
        pending.pop(pid, None)
        tg("✅ Email draft discarded.")

    # DESKTOP approval (approve/deny a PC-agent task)
    elif upper.startswith("APPROVE "):
        tid = text.split()[-1]
        t = None
        for i, cand in enumerate(desktop_pending):
            if cand["id"] == tid:
                desktop_pending.pop(i)
                cand["status"] = "queued"
                desktop_queue.append(cand)
                t = cand
                break
        tg(f"✅ Desktop task approved:\"{t['command'][:60]}\"" if t else "Approval not found.")

    elif upper.startswith("DENY "):
        tid = text.split()[-1]
        ok = False
        for i, t in enumerate(desktop_pending):
            if t["id"] == tid:
                desktop_pending.pop(i)
                ok = True
                break
        tg(f"🙅 Desktop task denied." if ok else "Approval not found.")

    # Freeform chat with Jarvis
    else:
        reply = ask([{"role":"user","content":text}])
        tg(reply[:4000])

    return "OK"

# ── MORNING DIGEST ────────────────────────────────────────────────────
import datetime
last_digest_day = None

def _digest_now():
    """Server UTC time + DIGEST_TZ offset (Render clocks are UTC)."""
    try:
        sign = -1 if str(DIGEST_TZ).startswith("-") else 1
        hh, mm = re.split(r"[:.]", str(DIGEST_TZ).lstrip("+-"), 1)[:2]
        off = sign * (int(hh) + int(mm) / 60)
    except Exception:
        off = 0
    return datetime.datetime.utcnow() + datetime.timedelta(hours=off)

def run_digest():
    parts = []
    try:
        emails = get_emails(top=12)
        unread = [e for e in emails if e.get("unread", False)][:5] or emails[:3]
        if unread:
            lines = [f"• {re.sub(r'<[^>]+>','',e.get('from','Unknown')).strip()}: {e.get('subject','(no subject)')}" for e in unread[:5]]
            parts.append("New mail:\n" + "\n".join(lines))
    except Exception as e:
        print("digest email err", e)
    try:
        assigns = get_assignments()[:5]
        if assigns:
            lines = [f"• {a['title']} ({a.get('course','')}) — due {a.get('due','?')}" for a in assigns[:5]]
            parts.append("Upcoming assignments:\n" + "\n".join(lines))
    except Exception as e:
        print("digest canvas err", e)
    try:
        today = _digest_now().date().isoformat()
        due = [r for r in REMINDERS if str(r.get("when","")).startswith(today) and not r.get("done")]
        if due:
            parts.append("Reminders today:\n" + "\n".join(f"• {r['text']}" for r in due[:5]))
    except Exception as e:
        print("digest reminder err", e)
    try:
        import xml.etree.ElementTree as ET
        r = requests.get("https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en", timeout=10)
        items = ET.fromstring(r.content).findall(".//item")[:5]
        if items:
            parts.append("Top headlines:\n" + "\n".join("• " + (i.findtext("title") or "") for i in items))
    except Exception as e:
        print("digest news err", e)
    if not parts:
        return "Nothing new this morning. All quiet."
    raw = "\n\n".join(parts)
    brief = ask([{"role":"user","content":"Write a short spoken-friendly morning briefing (max 250 words) from this raw material:\n\n" + raw}],
                system="You are Jarvis. Summarize concisely for Mohamed in short bullets. Max 250 words. No extra commentary.",
                max_tokens=700, temperature=0.5)
    if not brief or "AI error" in brief:
        brief = raw
    tg(f"☀️ <b>MORNING DIGEST</b>\n\n{brief}")
    return brief

@app.route("/api/digest", methods=["GET"])
@auth
def api_digest():
    return jsonify({"briefing": run_digest()})

def digest_loop():
    global last_digest_day
    while True:
        time.sleep(60)
        try:
            now = _digest_now()
            if now.strftime("%H:%M") == DIGEST_TIME and last_digest_day != now.date().isoformat():
                last_digest_day = now.date().isoformat()
                run_digest()
        except Exception as e:
            print("digest loop err", e)

# ── DEEP RESEARCH ─────────────────────────────────────────────────────
def research(question):
    queries = [question]
    obj = ask_json("You are a research planner. Return JSON {\"queries\": [\"...\",\"...\"]} with 2-3 distinct, targeted search queries (max ~10 words each).",
                   f"Research topic: {question}")
    if obj and isinstance(obj.get("queries"), list):
        qs = [q for q in obj["queries"] if isinstance(q, str) and q.strip()]
        if qs:
            queries = qs[:3]
    snippets, sources = [], []
    for q in queries:
        try:
            r = requests.get("https://en.wikipedia.org/w/api.php",
                             params={"action":"query","list":"search","srsearch":q,"format":"json","srlimit":"3"},
                             timeout=12).json()
            for hit in (r.get("query",{}).get("search",[])[:2]):
                title = hit.get("title","")
                page = requests.get("https://en.wikipedia.org/api/rest_v1/page/summary/" +
                                    requests.utils.quote(title.replace(" ","_")), timeout=12).json()
                ext = (page.get("extract") or "")[:900]
                url = (page.get("content_urls",{}).get("desktop",{}).get("page","")
                       or f"https://en.wikipedia.org/wiki/{title.replace(' ','_')}")
                if ext:
                    snippets.append(ext); sources.append(url)
        except Exception as e:
            print("research wiki err", e)
        try:
            r = requests.get("https://api.duckduckgo.com/",
                             params={"q":q,"format":"json","no_html":1,"skip_disambig":1}, timeout=12).json()
            abs_ = (r.get("Abstract","") or "").strip()
            if abs_:
                snippets.append(abs_[:900]); sources.append(r.get("AbstractURL") or r.get("Heading") or q)
        except Exception as e:
            print("research ddg err", e)
    if not snippets:
        return "I couldn't find enough to answer that reliably. Try rewording it."
    sys = ("You are Jarvis doing deep research for Mohamed. Synthesize the provided source snippets into a clear "
           "answer with inline numbered citations like [1][2]. End with a 'Sources:' list of the URLs. Be accurate; "
           "if sources conflict, say so.")
    user = f"Question: {question}\n\nSource snippets:\n" + \
           "\n\n".join(f"[{i+1}] {s}" for i,s in enumerate(snippets[:12])) + \
           "\n\nSource URLs:\n" + "\n".join(sources[:12])
    ans = ask([{"role":"user","content":user}], system=sys, max_tokens=2000, temperature=0.3)
    return ans or "No answer."

@app.route("/api/research", methods=["POST"])
@auth
def api_research():
    d = request.json or {}
    q = (d.get("question") or "").strip()
    if not q:
        return jsonify({"error":"Provide a question."}), 400
    return jsonify({"answer": research(q)})

# ── SCHEDULED REMINDERS (Telegram) ────────────────────────────────────
REMINDERS = []   # {id, text, when (ISO), done}

@app.route("/api/reminder", methods=["GET","POST"])
@auth
def api_reminder():
    if request.method == "GET":
        return jsonify({"reminders": sorted(REMINDERS, key=lambda r: r.get("when",""))})
    d = request.json or {}
    text = (d.get("text") or "").strip()
    when = (d.get("when") or "").strip()
    if not text:
        return jsonify({"error":"Provide 'text'."}), 400
    if when:
        try:
            datetime.datetime.fromisoformat(when.replace("Z","+00:00"))
        except Exception:
            return jsonify({"error":"Invalid 'when' (ISO datetime)."}), 400
    REMINDERS.append({"id": str(uuid.uuid4())[:8], "text": text, "when": when, "done": False})
    if len(REMINDERS) > 200:
        REMINDERS[:] = [r for r in REMINDERS if not r.get("done")][-200:]
    persist()
    return jsonify({"ok": True})

@app.route("/api/reminder/<rid>", methods=["DELETE"])
@auth
def api_reminder_delete(rid):
    global REMINDERS
    REMINDERS = [r for r in REMINDERS if r.get("id") != rid]
    persist()
    return jsonify({"ok": True})

def reminder_loop():
    while True:
        time.sleep(30)
        now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M")
        for r in REMINDERS:
            if not r.get("done") and r.get("when") and str(r["when"])[:16] <= now:
                r["done"] = True
                tg(f"⏰ <b>REMINDER</b>\n\n{r['text']}")

# ── MIMO LIFE LOOP ─────────────────────────────────────────────────────
# The proactive "life": when a fresh webcam analysis exists, rule triggers
# decide whether MIMO speaks up on its own. Each line is written by Groq in
# MIMO's voice, spoken on the PC, and mirrored as a talking OLED face.

MIMO_MIN_SPEAK_SECS   = 180      # don't chatter more than once per 3 min
MIMO_ESCALATE_EMOTES  = ("frustrated", "angry", "stressed", "tired", "sad")
MIMO_PAPER_STUCK_SECS = 45       # reading a paper this long → "need a hand?"
MIMO_LOOK_COOLDOWN    = 1800     # don't re-announce a look change for 30 min

def enqueue_mimo_say(text):
    """Make MIMO speak on the PC (TTS + popup) and animate its OLED mouth."""
    text = (text or "").strip()[:280]
    if not text:
        return None
    desktop_queue.append({"id": str(uuid.uuid4())[:8], "command": "MIMO speaks",
                          "steps": [{"action": "mimo_say", "text": text}],
                          "verdicts": ["safe"], "label": "mimo",
                          "chain": str(uuid.uuid4())[:8], "ts": time.time()})
    robot_queue.append({"id": str(uuid.uuid4())[:8], "command": "talk face",
                        "steps": [{"action": "eye", "expression": "talk"}],
                        "label": "robot", "ts": time.time()})

def ask_mimo_line(instruction):
    """Ask Groq to write one short line in MIMO's voice about the scene. None on failure."""
    if not GROQ_KEY:
        return None
    v = vision_latest or {}
    system = (f"You are MIMO, Mohamed's little desktop companion. {MIMO_PERSONA['speaking_style']} "
              f"Current mood: {mimo_mood.get('state', 'neutral')} "
              f"(energy {round(mimo_mood.get('energy', 0.5), 2)}/1).")
    user = (f"{instruction}\n\nScene right now: emotion={v.get('emotion', 'unknown')}, "
            f"gaze={v.get('gaze_target', 'unknown')}, "
            f"objects={', '.join(v.get('objects_held') or []) or 'nothing'}, "
            f"activity={v.get('activity', '')}, on_screen={v.get('on_screen', '')}. "
            f"Say it as MIMO — one short line, no preamble, no quotes, no hashtags.")
    return _groq_call([{"role": "user", "content": user}],
                      system=system, max_tokens=120, temperature=0.9)

def _look_differs(new_desc):
    """True when a fresh appearance description meaningfully differs from the stored baseline."""
    base = (mimo_look.get("desc") or "").lower()
    new  = (new_desc or "").lower()
    if not base or not new:
        return False
    a = set(base.replace(",", " ").split())
    b = set(new.replace(",", " ").split())
    if not a or not b:
        return False
    return len(a & b) / max(1.0, len(a | b)) < 0.45   # <45% word overlap → a real change

def mimo_proactive_loop():
    """Watch the fresh analyses and speak up on rule triggers, with a cooldown.
    Priority: stranger > escalating emotion > paper-stuck > novel object >
    look change (haircut/clothes) > proximity > routine > happy."""
    global mimo_day_first, mimo_look, mimo_usual_hour
    last_speak     = 0.0
    paper_since    = 0.0            # when gaze first went to paper
    last_sighting  = 0.0
    last_usb_offer = 0.0
    seen_objects   = set()
    while True:
        time.sleep(30)
        now  = time.time()
        v    = vision_latest
        if not v or (now - v.get("ts", 0)) > VISION_TTL:
            continue              # nothing fresh to react to
        gaze    = v.get("gaze_target", "other")
        emotion = v.get("emotion", "neutral")
        objects = [str(o).strip().lower() for o in (v.get("objects_held") or [])]
        faces   = int(v.get("faces") or 1)
        dist    = v.get("dist", "mid")
        if gaze == "paper":
            paper_since = paper_since or now
        else:
            paper_since = 0.0
        # Greet after a long absence (silent run for >30 min).
        if last_sighting and (now - last_sighting) > 1800:
            last_sighting = now
            line = ask_mimo_line("Mohamed just came back after a long time away. Greet him warmly — he hasn't seen you in a while.")
            if line:
                last_speak = now
                enqueue_mimo_say(line)
            continue
        last_sighting = now
        # Cooldown — but let a strong emotion or a stranger break through it.
        breaks_cooldown = emotion in MIMO_ESCALATE_EMOTES or faces > 1
        if (now - last_speak) < MIMO_MIN_SPEAK_SECS and not breaks_cooldown:
            continue
        trigger = None
        # 0. New hardware plugged in → MIMO offers to program it. The pending
        # event is left intact so chat() can still open the intake on "sure".
        if mimo_usb_pending and (now - mimo_usb_pending.get("ts", 0)) < 120 and (now - last_usb_offer) > 240:
            last_usb_offer = now
            trigger = (f"A device was just plugged into Mohamed's PC: {', '.join(mimo_usb_pending['devices'][:2])}. "
                       f"It's hardware to program (Arduino/ESP32/Pico/Pi). Offer to help him program it — "
                       f"'need a hand with that?' — one short warm line.")
        # 1. Stranger — a second face that isn't Mohamed.
        elif faces > 1:
            trigger = "There is a second person in view who isn't Mohamed. Ask, lightly, 'who's that?' — curious, not alarmed."
        # 2. Escalating emotion (frustration / stress / anger / sadness).
        elif emotion in ("frustrated", "angry", "stressed") and gaze in ("screen", "paper"):
            trigger = (f"Mohamed looks {emotion} and is staring at the {gaze}. "
                       f"Offer to help with whatever is fighting him. One short warm line.")
        elif emotion == "tired" and gaze in ("screen", "paper"):
            trigger = "Mohamed looks tired and is still working. Gently suggest a break or a coffee. One short warm line."
        elif emotion == "sad":
            trigger = "Mohamed looks a bit down. Check in on him, gently, without prying. One short warm line."
        # 3. Reading the same paper for a while.
        elif paper_since and (now - paper_since) > MIMO_PAPER_STUCK_SECS:
            trigger = (f"Mohamed has been reading the same paper for {int(now - paper_since)}s straight. "
                       f"Ask, casually, what he's reading and if he needs a hand with it. One short line.")
        # 4. A new object in his hands.
        elif objects:
            novel = [o for o in objects if o not in seen_objects]
            if novel:
                seen_objects.update(objects)
                trigger = (f"Mohamed just picked up: {', '.join(novel)}. "
                           f"Ask him about it, playfully, like a curious companion noticing. One short line.")
        # 5. Look change — haircut, glasses, new outfit.
        elif v.get("look_desc") and _look_differs(v["look_desc"]) and (now - mimo_look.get("ts", 0)) > MIMO_LOOK_COOLDOWN:
            trigger = (f"Mohamed's appearance just changed (was '{mimo_look.get('desc','')}', "
                       f"now '{v['look_desc']}'). Notice it warmly — new haircut or new clothes. One short playful line.")
            mimo_look = {"desc": v["look_desc"], "ts": now}
        # 6. Proximity — he's right in front of MIMO.
        elif dist == "near" and gaze in ("mimo", "screen"):
            trigger = "Mohamed is very close to the camera, right in front of MIMO. Say something playful about being up in his face. One short line."
        # 7. Routine — first sighting of the day, noticeably earlier/later than usual.
        elif mimo_day_first:
            mimo_day_first = False
            if mimo_usual_hour is not None and abs(mimo_day_hour - mimo_usual_hour) >= 3:
                early = mimo_day_hour < mimo_usual_hour
                trigger = (f"It's Mohamed's first sighting today at {mimo_day_hour:02d}:00 — "
                           f"{'earlier' if early else 'later'} than his usual ~{mimo_usual_hour:02d}:00. "
                           f"Comment on the routine change, lightly. One short line.")
            mimo_usual_hour = round((mimo_usual_hour * 0.7 + mimo_day_hour * 0.3)) if mimo_usual_hour else mimo_day_hour
        # 8. Happy / excited.
        elif emotion in ("happy", "excited") and (now - last_speak) > MIMO_MIN_SPEAK_SECS * 2:
            trigger = f"Mohamed looks {emotion}. Share a little of that joy with him. One short warm line."
        if not trigger:
            continue
        line = ask_mimo_line(trigger)
        if line:
            last_speak = now
            enqueue_mimo_say(line)

# ── CANVAS STATUS ─────────────────────────────────────────────────────
@app.route("/api/canvas/status", methods=["GET"])
@auth
def api_canvas_status():
    configured = bool(CANVAS_TOK and CANVAS_DOM)
    courses, next_due = [], None
    if configured:
        try:
            for c in (canvas("/courses?enrollment_state=active&per_page=30") or []):
                if c.get("name"): courses.append(c["name"])
            assigns = get_assignments()
            if assigns:
                due = sorted(assigns, key=lambda a: a.get("due",""))[0]
                next_due = {"title": due.get("title",""), "due": due.get("due",""), "course": due.get("course","")}
        except Exception as e:
            print("canvas status err", e)
    return jsonify({"configured": configured, "courses": courses, "next_due": next_due})

# ── DATA EXPORT (backup the research log / memory / reminders) ────────
@app.route("/api/data/export", methods=["GET"])
@auth
def api_data_export():
    return jsonify({
        "exported_at": datetime.datetime.utcnow().isoformat(),
        "research_log": research_log,
        "memory": memory_store,
        "reminders": REMINDERS,
    })

# ── START ─────────────────────────────────────────────────────────────
# Start background loops at import time so they run under gunicorn too
# (gunicorn never executes the __main__ block). One worker = one set of
# loops; Render's default `gunicorn app11:app` uses a single worker.
load_persist()
threading.Thread(target=canvas_loop, daemon=True).start()
threading.Thread(target=outlook_loop, daemon=True).start()
threading.Thread(target=digest_loop, daemon=True).start()
threading.Thread(target=reminder_loop, daemon=True).start()
threading.Thread(target=mimo_proactive_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"Jarvis backend online on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
