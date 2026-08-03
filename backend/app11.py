"""
JARVIS BACKEND v3.0
- AI: Groq (free) — llama-3.3-70b-versatile
- Security: API_SECRET token + CORS whitelist
- Canvas: 2hr timer + Telegram approval flow
- Outlook: Background polling every 10 min → Telegram summary + draft approval
"""
import os, re, time, threading, requests, imaplib, smtplib, email as email_lib, json, uuid
from email.header import decode_header
from email.mime.text import MIMEText
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
GROQ_KEY       = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL     = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")  # free on console.groq.com
API_SECRET     = os.getenv("API_SECRET", "")       # random string you set on Render
TG_TOKEN       = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_CHAT_ID     = os.getenv("TELEGRAM_CHAT_ID", "")
CANVAS_TOK     = os.getenv("CANVAS_TOKEN", "")
CANVAS_DOM     = os.getenv("CANVAS_DOMAIN", "")    # e.g. school.instructure.com
OUTLOOK_EMAIL  = os.getenv("OUTLOOK_EMAIL", "")    # your full email address
OUTLOOK_PASS   = os.getenv("OUTLOOK_PASSWORD", "") # app password (personal) or regular (school)
IMAP_SERVER    = os.getenv("IMAP_SERVER", "outlook.office365.com")  # or imap-mail.outlook.com
SMTP_SERVER    = os.getenv("SMTP_SERVER", "smtp.office365.com")
POLL_SECS      = int(os.getenv("OUTLOOK_POLL_SECS", "600"))  # 10 min default
DIGEST_TIME    = os.getenv("DIGEST_TIME", "12:00")  # HH:MM daily digest (UTC by default)
DIGEST_TZ      = os.getenv("DIGEST_TZ", "+00:00")   # timezone offset, e.g. -05:00 for Houston (CT)

SYSTEM = ("You are Jarvis — Mohamed's personal AI and right hand. Always call him Sir. "
          "He's a web design student and freelancer in Katy/Houston, TX building local business "
          "websites, and finishing up university on Canvas. "
          "Talk to him like a sharp, loyal friend who happens to know everything: warm, concise, "
          "a little dry humor when it fits, contractions are fine ('I'll', 'you're', 'that's'). "
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
    "replies. Do NOT add that line for pure chat questions.")

# ── SHARED STATE ──────────────────────────────────────────────────────
pending          = {}   # approval_id → {type, data}
assign_timers    = {}   # assignment_id → timer info
seen_assignments = set()
seen_emails      = set()

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

def ask(messages, system=None, max_tokens=2000, temperature=0.7):
    """Free-form text completion via Groq (with Jarvis's remembered facts injected)."""
    if not GROQ_KEY:
        return "GROQ_API_KEY not set on Render, Sir. Add it in Environment Variables."
    sys = system or SYSTEM
    if memory_store:
        mem = "\n".join("- " + m["fact"] for m in memory_store[-20:])
        sys = sys + "\n\nThings you remember about Mohamed (use when relevant):\n" + mem
    text = _groq_call(messages, system=sys,
                      max_tokens=max_tokens, temperature=temperature)
    return text if text is not None else "AI error, Sir."

# ── TELEGRAM ──────────────────────────────────────────────────────────
def tg(msg):
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                      json={"chat_id": TG_CHAT_ID, "text": f"🤖 JARVIS\n\n{msg}", "parse_mode": "HTML"},
                      timeout=10)
    except: pass

# ── OUTLOOK VIA IMAP/SMTP (no app registration needed) ───────────────
import imaplib, smtplib, email as email_lib
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def get_emails(top=15):
    if not OUTLOOK_EMAIL or not OUTLOOK_PASS:
        return []
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(OUTLOOK_EMAIL, OUTLOOK_PASS)
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
    if not OUTLOOK_EMAIL or not OUTLOOK_PASS:
        return False, "Outlook not configured, Sir."
    try:
        msg = MIMEMultipart()
        msg["From"]    = OUTLOOK_EMAIL
        msg["To"]      = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(SMTP_SERVER, 587) as server:
            server.ehlo()
            server.starttls()
            server.login(OUTLOOK_EMAIL, OUTLOOK_PASS)
            server.sendmail(OUTLOOK_EMAIL, to, msg.as_string())
        return True, "Sent, Sir."
    except Exception as e:
        return False, f"Send failed: {e}"

# ── CANVAS ────────────────────────────────────────────────────────────
def canvas(path):
    if not CANVAS_TOK or not CANVAS_DOM: return None
    try:
        r = requests.get(f"https://{CANVAS_DOM}/api/v1{path}",
                         headers={"Authorization": f"Bearer {CANVAS_TOK}"}, timeout=15)
        if r.status_code == 401:
            tg("⚠️ <b>Canvas token expired, Sir.</b> Please renew it.")
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
    assign_timers[aid] = {**a, "start": time.time(), "status": "pending"}

    def run():
        time.sleep(7200)  # 2 hours
        if aid not in assign_timers: return
        assign_timers[aid]["status"] = "ready"
        tg(f"📚 <b>ASSIGNMENT READY, SIR</b>\n\n"
           f"<b>Course:</b> {a['course']}\n"
           f"<b>Title:</b> {a['title']}\n"
           f"<b>Due:</b> {a.get('due','?')}\n\n"
           f"Shall I complete and submit it?\n"
           f"Reply: <code>CANVAS YES {aid}</code>  or  <code>CANVAS NO {aid}</code>")
    threading.Thread(target=run, daemon=True).start()

# ── BACKGROUND: CANVAS POLLER ─────────────────────────────────────────
def canvas_loop():
    while True:
        try:
            for a in get_assignments():
                aid = a["id"]
                if aid not in seen_assignments:
                    seen_assignments.add(aid)
                    start_timer(a)
                    tg(f"🎓 <b>NEW ASSIGNMENT, SIR</b>\n\n"
                       f"<b>Course:</b> {a['course']}\n"
                       f"<b>Title:</b> {a['title']}\n"
                       f"<b>Due:</b> {a.get('due','?')}\n"
                       f"<b>Points:</b> {a.get('points','?')}\n\n"
                       f"2-hour auto-complete window started.")
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

                tg(f"📧 <b>NEW EMAIL, SIR</b>\n\n"
                   f"<b>From:</b> {fname} &lt;{faddr}&gt;\n"
                   f"<b>Subject:</b> {subj}\n"
                   f"<b>Received:</b> {recv}\n\n"
                   f"<b>Summary:</b>\n{summary}")

                pid = f"email_{eid}"
                pending[pid] = {"type":"email","to":faddr,"subject":f"Re: {subj}","body":draft,"email_id":eid}
                time.sleep(1)
                tg(f"📝 <b>DRAFT REPLY READY, SIR</b>\n\n"
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
                 "click_text","click_selector","type_selector","type_label",
                 "search","run_js","scroll","wait","press_key",
                 "list_tabs","read_tab","switch_tab","close_tab",
                 "go_back","go_forward","new_window","group_tabs",
                 "save_session","restore_session","save_tab"}
STEP_FIELDS   = {"action","url","text","selector","value","label","code","x","y","ms","key","query","tab","keyword","name"}
BROWSER_MAX_STEPS = 8
BROWSER_MAX_ITERS = 12          # guard against infinite agentic loops

browser_queue     = []          # pending tasks
browser_running   = {}          # task_id → task being executed
browser_results   = {}          # task_id → last result
browser_tab_state = {}          # last tab reported by the extension
browser_iters     = {}          # command chain → iterations left
browser_delivered = set()       # task ids already handed to the extension (runs-once guard)
browser_last_seen = 0.0         # epoch seconds of last tab ping
browser_answers   = []          # recent finished results {command, answer, ts}
browser_sessions  = []          # saved tab sessions [{urls, ts}] (latest wins)
research_log      = []          # cross-window saves {id,title,url,text,label,ts}

ACTIONS_DOC = """Return a JSON object with a "steps" array (1-8 steps). Allowed step actions:
- {"action":"navigate","url":"https://..."}
- {"action":"new_tab","url":"https://..."}
- {"action":"read_page"}
- {"action":"screenshot"}
- {"action":"click_text","text":"visible button/link text"}
- {"action":"click_selector","selector":"css selector"}
- {"action":"type_selector","selector":"css selector","value":"text"}
- {"action":"type_label","label":"input label or placeholder","value":"text"}
- {"action":"search","query":"text to search the site's own search box"}
- {"action":"scroll","y":500}
- {"action":"wait","ms":1000}
- {"action":"press_key","key":"Enter"}
- {"action":"run_js","code":"return document.title"}
To find a video/article/result: navigate to the site, use {"action":"search","query":"..."} on its search box, wait, then read_page and click the matching result by its title text. Prefer clicking by visible text; add a wait after navigating.
When the user asks to OPEN a site (e.g. "open youtube", "open google"), use {"action":"new_tab","url":"https://..."} — it opens in a NEW TAB and becomes active. Do NOT use navigate for open-requests.
Tab control (the "tab" field matches a tab's URL, title, or tab number):
- {"action":"list_tabs"} — list all open tabs
- {"action":"read_tab","tab":"substring or number"} — read a specific tab's content
- {"action":"switch_tab","tab":"substring or number"} — bring that tab to front
- {"action":"close_tab","tab":"substring or number"} — close it (omit tab = current)
- {"action":"go_back"} / {"action":"go_forward"}
- {"action":"new_window","url":"https://..."} — open in a new window
- {"action":"group_tabs","keyword":"topic"} — group tabs matching the topic
- {"action":"save_session"} — save all open tabs for later
- {"action":"restore_session"} — reopen the last saved session
- {"action":"save_tab","label":"note"} — save the current tab's text to the research log"""

def ask_json(system, user):
    """Ask Groq for a JSON object (strip markdown fences if any)."""
    if not GROQ_KEY:
        return None
    text = _groq_call([{"role": "user", "content": user}], system=system,
                      max_tokens=2000, temperature=0.2)
    if not text:
        return None
    text = re.sub(r"^```[a-z]*\n?", "", text.strip())
    text = re.sub(r"\n?```$", "", text)
    try:
        return json.loads(text)
    except Exception:
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

def plan_steps(command):
    """Turn a natural-language command into a first batch of steps."""
    obj = ask_json("You are Jarvis planning browser automation. " + ACTIONS_DOC,
                   f"Task: {command}\nCurrent tab: {browser_tab_state.get('url','')} ({browser_tab_state.get('title','')})")
    if not obj:
        return []
    return prefer_new_tab(command, sanitize_steps(obj.get("steps")))

def decide_next(command, log, page):
    """Decide if the goal is done; otherwise produce the next batch of steps.
    Returns {"done": bool, "steps": [...], "answer": str} — when done, `answer`
    carries the final synthesis for Mohamed (summary, drafts, key info)."""
    system = ("You are Jarvis driving a browser agent to completion. Given the goal, the steps already "
              "run, their results, and the current page, decide whether the goal is achieved. Return JSON: "
              "{\"done\": true, \"answer\": \"<concise final answer for Mohamed>\"} when the goal is achieved "
              "or cannot progress — the answer should synthesize what he asked for (a summary, key details, "
              "or example drafts). Otherwise return {\"done\": false, \"steps\": [...]} (1-6 steps). "
              + ACTIONS_DOC)
    user = (f"Goal: {command}\n\nSteps so far:\n{json.dumps(log[-10:], indent=1)[:4000]}\n\n"
            f"Current page:\nURL: {page.get('url')}\nTitle: {page.get('title')}\n"
            f"Text: {page.get('text','')[:2000]}")
    obj = ask_json(system, user)
    if not obj:
        return {"done": True, "steps": [], "answer": ""}
    if obj.get("done"):
        return {"done": True, "steps": [], "answer": (obj.get("answer") or "").strip()}
    return {"done": False, "steps": sanitize_steps(obj.get("steps")), "answer": ""}

def finish_browser(chain, command, answer):
    """End a command chain and deliver the final answer (Telegram + stored for the site)."""
    browser_iters.pop(chain, None)
    if not answer:
        tg(f"✅ Browser task complete: \"{command[:40]}\"")
        return
    browser_answers.insert(0, {"command": command, "answer": answer, "ts": time.time()})
    del browser_answers[10:]
    safe = answer.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    tg(f"📋 <b>BROWSER RESULT, SIR</b>\n\n{safe[:3000]}")

def enqueue_browser(command, steps, chain=None):
    task = {"id": str(uuid.uuid4())[:8], "command": command,
            "steps": steps, "chain": chain or str(uuid.uuid4())[:8]}
    browser_queue.append(task)
    return task

# Fallback intent detection: if the model didn't emit [[BROWSER]], still
# dispatch when the user's message is clearly a browser action.
BROWSER_RE = re.compile(
    r"\b(open|go to|navigate|browse|visit|search|look up|google|scroll|click|type in|"
    r"open on|go on|find on|search on)\b", re.I)

# ── SKILLS (from the 10 Must-Have AI Skills guide) ─────────────────────
SKILL_PROMPTS = {
    "design": ("You are a senior UI/UX designer with a huge design database (50+ UI styles, 97 palettes, "
               "57 font pairings). For the brief: (1) output a ```json``` design system: aesthetic direction, "
               "6-color palette with hex codes, heading+body font pairing, spacing scale, border radius, shadow, "
               "3-5 named UI styles, style notes; (2) then output a complete single-file HTML page (embedded CSS, "
               "no frameworks) using it. Make it distinctive and NOT AI-looking: no generic purple gradients, no "
               "default system font stack, bold typography. Web + mobile responsive."),
    "humanize": ("You are a humanizer that removes every trace of AI-generated writing. Detect and fix these 24 "
                 "patterns: inflated symbolism, promotional language, superficial analyses, vague attributions, "
                 "em-dash overuse, rule-of-three structures, AI vocabulary words ('delve', 'leverage', 'elevate', "
                 "'moreover', 'furthermore', 'navigate', 'robust', 'seamless'), excessive conjunctive phrases, "
                 "overly balanced sentences, generic openers, and more. Rewrite the user's text to sound natural "
                 "and human while preserving the original meaning. Return ONLY the rewritten text."),
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

def analyze_data(text):
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
            return jsonify({"error": "No fact to remember, Sir."}), 400
        memory_store.append({"id": str(uuid.uuid4())[:8], "fact": f[:400], "ts": time.time()})
        del memory_store[100:]
        return jsonify({"ok": True})
    mid = (request.json or {}).get("id", "").strip()
    memory_store[:] = [m for m in memory_store if m["id"] != mid]
    return jsonify({"ok": True})

@app.route("/api/skills/<skill>", methods=["POST"])
@auth
def api_skill(skill):
    prompt = SKILL_PROMPTS.get(skill)
    if not prompt:
        return jsonify({"error": "Unknown skill, Sir."}), 404
    text = ((request.json or {}).get("text") or "").strip()
    if not text:
        return jsonify({"error": "No input, Sir."}), 400
    if skill == "analyze":
        stats = analyze_data(text)
        if not stats:
            return jsonify({"error": "I need a list of numbers (one per line), Sir."}), 400
        res = ask([{"role": "user", "content": f"Dataset:\n{text[:4000]}\n\nComputed statistics:\n{stats}\n\nInterpret these statistics."}],
                  system=prompt, max_tokens=1500)
        return jsonify({"result": res or "AI error, Sir.", "stats": stats})
    if skill == "seo" and text.startswith(("http://", "https://")):
        a = audit_url(text)
        if a:
            text += "\n\nLIVE ON-PAGE AUDIT (fetched now):\n" + json.dumps(a, indent=2, default=str)[:1500]
    res = ask([{"role": "user", "content": text[:6000]}], system=prompt, max_tokens=1800)
    return jsonify({"result": res or "AI error, Sir."})

# ── ROUTES ────────────────────────────────────────────────────────────
@app.route("/")
def health():
    return jsonify({"status":"online","model":GROQ_MODEL,"message":"Jarvis online, Sir."})

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

@app.route("/api/chat", methods=["POST"])
@auth
def chat():
    d = request.json or {}
    msg  = d.get("message","").strip()
    hist = [{"role": m.get("role"), "content": (m.get("content") or "")[:1500]}
            for m in d.get("history",[]) if m.get("role") in ("user","assistant")][-10:]
    if not msg: return jsonify({"response":"No message, Sir."}), 400
    if not hist or hist[-1].get("content") != msg:
        hist.append({"role":"user","content":msg})
    rm = re.match(r"^(?:remember|note)\s+(?:that\s+)?(.+)$", msg, re.I)
    if rm and len(rm.group(1).strip()) < 300:
        memory_store.append({"id": str(uuid.uuid4())[:8], "fact": rm.group(1).strip()[:400], "ts": time.time()})
        del memory_store[100:]
        return jsonify({"response":"Got it, Sir — I'll remember that."})
    system = CHAT_SYSTEM
    if not BROWSER_RE.search(msg) and "```" not in msg and len(msg) <= 400 and GROUND_RE.search(msg):
        ctx = search_web(msg)
        if ctx:
            system = CHAT_SYSTEM + ("\n\nFresh web context to ground your answer (use it if relevant, cite "
                                    "sources with their URLs):\n" + ctx[:2500])
    reply = ask(hist, system=system, max_tokens=1200)

    # Dispatch to the browser when the model tagged it, OR when the user's
    # request is clearly a browser action and the model just gave text.
    extra = ""
    m = re.search(r"\[\[BROWSER\]\]\s*([^\[]*)", reply)
    cmd = None
    if m and m.group(1).strip():
        reply = re.sub(r"\[\[BROWSER\]\][^\[]*", "", reply).rstrip()
        cmd = m.group(1).strip()
    elif BROWSER_RE.search(msg):
        cmd = msg

    if cmd:
        planned = plan_steps(cmd)
        if planned:
            task = enqueue_browser(cmd, planned)
            browser_iters[task["chain"]] = BROWSER_MAX_ITERS
            extra = (f"\n\n🌐 Browser: I've queued \"{cmd}\" ({len(planned)} actions). "
                     f"Your extension is carrying it out — the result lands on the Browser page and Telegram, Sir.")
        else:
            extra = f"\n\n⚠️ Browser: I couldn't plan \"{cmd}\", Sir."
    return jsonify({"response": reply + extra})

@app.route("/api/math/solve", methods=["POST"])
@auth
def math_solve():
    prob = (request.json or {}).get("problem","").strip()
    if not prob: return jsonify({"solution":"No problem given, Sir."}), 400
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
        pct, label = 0, ""
        if "start" in t:
            elapsed  = time.time() - t["start"]
            pct      = min(100, int(elapsed/7200*100))
            rem      = max(0, 7200-elapsed)
            label    = f"{int(rem//3600)}h {int(rem%3600//60)}m remaining"
        result.append({**a,"status":status,"timer_pct":pct,"timer_label":label})
    return jsonify({"assignments": result})

@app.route("/api/canvas/complete", methods=["POST"])
@auth
def canvas_complete():
    aid = (request.json or {}).get("assignment_id","")
    if not aid or aid not in assign_timers:
        return jsonify({"message":"Assignment not found, Sir."}), 404
    a = assign_timers[aid]
    assign_timers[aid]["status"] = "drafting"

    def do():
        draft = ask([{"role":"user","content":f"Complete this assignment fully:\n\nTitle: {a['title']}\nCourse: {a['course']}\n\nInstructions:\n{a.get('description','')}"}],
                    system="You are Jarvis completing a university assignment for Mohamed. Write a complete well-structured academic response.",
                    max_tokens=2000)
        pid = f"canvas_{aid}"
        pending[pid] = {"type":"canvas","assignment":a,"draft":draft,"aid":aid}
        assign_timers[aid]["status"] = "awaiting"
        tg(f"📝 <b>DRAFT COMPLETE, SIR</b>\n\n"
           f"<b>Course:</b> {a['course']}\n"
           f"<b>Title:</b> {a['title']}\n\n"
           f"{draft[:700]}{'...' if len(draft)>700 else ''}\n\n"
           f"Reply: <code>SUBMIT {pid}</code>  or  <code>REJECT {pid}</code>")
    threading.Thread(target=do, daemon=True).start()
    return jsonify({"message":"Drafting now, Sir. Check Telegram in ~30 seconds."})

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

@app.route("/api/browser/status", methods=["GET"])
@auth
def browser_status():
    return jsonify({
        "connected": bool(browser_tab_state) and (time.time() - browser_last_seen) < 60,
        "tab": browser_tab_state,
        "queue": len(browser_queue),
        "running": len(browser_running),
        "results": len(browser_results),
        "last_answer": browser_answers[0] if browser_answers else None,
    })

@app.route("/api/browser/task", methods=["POST"])
@auth
def browser_task():
    d = request.json or {}
    command = (d.get("command") or "").strip()
    steps   = d.get("steps")
    if not command and not steps:
        return jsonify({"error": "Provide 'command' or 'steps', Sir."}), 400
    if steps:
        clean = sanitize_steps(steps)
        if not clean:
            return jsonify({"error": "No valid steps provided, Sir."}), 400
        task = enqueue_browser(command or "manual steps", clean)
    else:
        planned = plan_steps(command)
        if not planned:
            return jsonify({"error": "Couldn't plan steps for that, Sir."}), 502
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
            return jsonify({"error":"No valid URLs, Sir."}), 400
        browser_sessions = [{"urls": urls, "ts": time.time()}]
        return jsonify({"ok": True, "saved": len(urls)})
    return jsonify({"urls": browser_sessions[0]["urls"] if browser_sessions else []})

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
        return jsonify({"ok": True})
    return jsonify({"log": research_log})

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
            tg("⚡ Starting completion now, Sir...")
            a = assign_timers[aid]
            assign_timers[aid]["status"] = "drafting"
            def do_approve():
                draft = ask([{"role":"user","content":f"Complete this assignment:\n\nTitle: {a['title']}\nCourse: {a['course']}\n\nInstructions:\n{a.get('description','')}"}],
                            system="Complete a university assignment for Mohamed. Write a full academic response.",
                            max_tokens=2000)
                pid = f"canvas_{aid}"
                pending[pid] = {"type":"canvas","assignment":a,"draft":draft,"aid":aid}
                assign_timers[aid]["status"] = "awaiting"
                tg(f"📝 <b>DRAFT READY, SIR</b>\n\n{a['title']}\n\n{draft[:700]}{'...' if len(draft)>700 else ''}\n\nReply: <code>SUBMIT {pid}</code>  or  <code>REJECT {pid}</code>")
            threading.Thread(target=do_approve, daemon=True).start()
        else:
            tg("Assignment not found, Sir.")

    elif upper.startswith("CANVAS NO "):
        aid = text.split()[-1]
        if aid in assign_timers: assign_timers[aid]["status"] = "skipped"
        tg("✅ Skipped, Sir.")

    elif upper.startswith("SUBMIT CANVAS_"):
        pid = text.split(" ",1)[1].strip()
        p = pending.pop(pid, None)
        if p and p["type"] == "canvas":
            a = p["assignment"]
            ok, m = submit_canvas(a.get("course_id",""), p["aid"], p["draft"])
            assign_timers.get(p["aid"],{}).update({"status":"submitted" if ok else "ready"})
            tg(f"{'✅ SUBMITTED' if ok else '❌ FAILED'}, SIR. {m}")
        else:
            tg("Approval not found, Sir.")

    elif upper.startswith("REJECT CANVAS_"):
        pid = text.split(" ",1)[1].strip()
        p = pending.pop(pid, None)
        if p: assign_timers.get(p["aid"],{}).update({"status":"ready"})
        tg("❌ Rejected, Sir. Assignment not submitted.")

    # EMAIL approval
    elif upper.startswith("SEND EMAIL_"):
        pid = text.split(" ",1)[1].strip()
        p = pending.pop(pid, None)
        if p and p["type"] == "email":
            ok, m = send_email(p["to"], p["subject"], p["body"], p.get("email_id"))
            tg(f"{'✅ Email sent' if ok else '❌ Failed'}, Sir. {m}")
        else:
            tg("Approval not found, Sir.")

    elif upper.startswith("SKIP EMAIL_"):
        pid = text.split(" ",1)[1].strip()
        pending.pop(pid, None)
        tg("✅ Email draft discarded, Sir.")

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
        return "Nothing new this morning, Sir. All quiet."
    raw = "\n\n".join(parts)
    brief = ask([{"role":"user","content":"Write a short spoken-friendly morning briefing (max 250 words) from this raw material:\n\n" + raw}],
                system="You are Jarvis. Summarize concisely for Mohamed ('Sir') in short bullets. Max 250 words. No extra commentary.",
                max_tokens=700, temperature=0.5)
    if not brief or "AI error" in brief:
        brief = raw
    tg(f"☀️ <b>MORNING DIGEST, SIR</b>\n\n{brief}")
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
        return "I couldn't find enough to answer that reliably, Sir. Try rewording it."
    sys = ("You are Jarvis doing deep research for Mohamed. Synthesize the provided source snippets into a clear "
           "answer with inline numbered citations like [1][2]. End with a 'Sources:' list of the URLs. Be accurate; "
           "if sources conflict, say so.")
    user = f"Question: {question}\n\nSource snippets:\n" + \
           "\n\n".join(f"[{i+1}] {s}" for i,s in enumerate(snippets[:12])) + \
           "\n\nSource URLs:\n" + "\n".join(sources[:12])
    ans = ask([{"role":"user","content":user}], system=sys, max_tokens=2000, temperature=0.3)
    return ans or "No answer, Sir."

@app.route("/api/research", methods=["POST"])
@auth
def api_research():
    d = request.json or {}
    q = (d.get("question") or "").strip()
    if not q:
        return jsonify({"error":"Provide a question, Sir."}), 400
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
        return jsonify({"error":"Provide 'text', Sir."}), 400
    if when:
        try:
            datetime.datetime.fromisoformat(when.replace("Z","+00:00"))
        except Exception:
            return jsonify({"error":"Invalid 'when' (ISO datetime), Sir."}), 400
    REMINDERS.append({"id": str(uuid.uuid4())[:8], "text": text, "when": when, "done": False})
    if len(REMINDERS) > 200:
        REMINDERS[:] = [r for r in REMINDERS if not r.get("done")][-200:]
    return jsonify({"ok": True})

@app.route("/api/reminder/<rid>", methods=["DELETE"])
@auth
def api_reminder_delete(rid):
    global REMINDERS
    REMINDERS = [r for r in REMINDERS if r.get("id") != rid]
    return jsonify({"ok": True})

def reminder_loop():
    while True:
        time.sleep(30)
        now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M")
        for r in REMINDERS:
            if not r.get("done") and r.get("when") and str(r["when"])[:16] <= now:
                r["done"] = True
                tg(f"⏰ <b>REMINDER, SIR</b>\n\n{r['text']}")

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

# ── START ─────────────────────────────────────────────────────────────
# Start background loops at import time so they run under gunicorn too
# (gunicorn never executes the __main__ block). One worker = one set of
# loops; Render's default `gunicorn app11:app` uses a single worker.
threading.Thread(target=canvas_loop, daemon=True).start()
threading.Thread(target=outlook_loop, daemon=True).start()
threading.Thread(target=digest_loop, daemon=True).start()
threading.Thread(target=reminder_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"Jarvis backend online on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
