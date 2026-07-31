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
GROQ_MODEL     = "llama-3.3-70b-versatile"
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

SYSTEM = ("You are Jarvis — personal AI assistant to Mohamed exclusively. "
          "Always call him Sir. He is a web design student/freelancer in Katy/Houston TX "
          "building local business websites. He studies at university using Canvas LMS. "
          "Be concise, sharp, and genuinely helpful. Use markdown. "
          "For business tasks be persuasive and professional. "
          "For math show full step-by-step work.")

CHAT_SYSTEM = SYSTEM + ("\n\nYou can also control Mohamed's browser through the Jarvis extension. "
    "If his message asks for a browser action (open a site, search, read a page, screenshot, click, "
    "fill a form — including multi-step ones like 'open Gmail, summarize the newest messages and give "
    "me example drafts'), reply normally but END your reply with exactly one line: [[BROWSER]]<short "
    "imperative command> describing the whole task, e.g. [[BROWSER]]open mail.google.com, read the inbox, "
    "summarize the 5 newest messages and draft replies. Do NOT add that line for pure chat questions.")

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

# ── GROQ AI ───────────────────────────────────────────────────────────
def ask(messages, system=None, max_tokens=2000):
    if not GROQ_KEY:
        return "GROQ_API_KEY not set on Render, Sir. Add it in Environment Variables."
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    body = {
        "model": GROQ_MODEL, "max_tokens": max_tokens, "temperature": 0.7,
        "messages": [{"role": "system", "content": system or SYSTEM}, *messages]
    }
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                          headers=headers, json=body, timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"AI error, Sir: {e}"

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
            new_ones = [e for e in emails if e["id"] not in seen_emails and not e.get("isRead", True)]
            for e in new_ones[:5]:
                eid = e["id"]
                seen_emails.add(eid)
                sender = e.get("from", {}).get("emailAddress", {})
                fname = sender.get("name", "Unknown")
                faddr = sender.get("address", "")
                subj  = e.get("subject", "(no subject)")
                body  = re.sub(r"<[^<]+?>"," ", e.get("body",{}).get("content","") or e.get("bodyPreview","")).strip()[:3000]
                recv  = e.get("receivedDateTime","")[:16].replace("T"," ")

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
                 "run_js","scroll","wait","press_key"}
STEP_FIELDS   = {"action","url","text","selector","value","label","code","x","y","ms","key"}
BROWSER_MAX_STEPS = 8
BROWSER_MAX_ITERS = 12          # guard against infinite agentic loops

browser_queue     = []          # pending tasks
browser_running   = {}          # task_id → task being executed
browser_results   = {}          # task_id → last result
browser_tab       = {}          # last tab reported by the extension
browser_iters     = {}          # command chain → iterations left
browser_last_seen = 0.0         # epoch seconds of last tab ping
browser_answers   = []          # recent finished results {command, answer, ts}

ACTIONS_DOC = """Return a JSON object with a "steps" array (1-8 steps). Allowed step actions:
- {"action":"navigate","url":"https://..."}
- {"action":"new_tab","url":"https://..."}
- {"action":"read_page"}
- {"action":"screenshot"}
- {"action":"click_text","text":"visible button/link text"}
- {"action":"click_selector","selector":"css selector"}
- {"action":"type_selector","selector":"css selector","value":"text"}
- {"action":"type_label","label":"input label or placeholder","value":"text"}
- {"action":"scroll","y":500}
- {"action":"wait","ms":1000}
- {"action":"press_key","key":"Enter"}
- {"action":"run_js","code":"return document.title"}
Prefer clicking by visible text; add a wait after navigating."""

def ask_json(system, user):
    """Ask Groq for a JSON object (strip markdown fences if any)."""
    if not GROQ_KEY:
        return None
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    body = {"model": GROQ_MODEL, "temperature": 0.2, "max_tokens": 2000,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                          headers=headers, json=body, timeout=60)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None
    content = re.sub(r"^```[a-z]*\n?", "", content)
    content = re.sub(r"\n?```$", "", content)
    try:
        return json.loads(content)
    except Exception:
        return None

def sanitize_steps(steps):
    out = []
    for s in (steps or []):
        if not isinstance(s, dict) or s.get("action") not in KNOWN_ACTIONS:
            continue
        out.append({k: v for k, v in s.items() if k in STEP_FIELDS and v is not None})
        if len(out) >= BROWSER_MAX_STEPS:
            break
    return out

def plan_steps(command):
    """Turn a natural-language command into a first batch of steps."""
    obj = ask_json("You are Jarvis planning browser automation. " + ACTIONS_DOC,
                   f"Task: {command}\nCurrent tab: {browser_tab.get('url','')} ({browser_tab.get('title','')})")
    if not obj:
        return []
    return sanitize_steps(obj.get("steps"))

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

# ── ROUTES ────────────────────────────────────────────────────────────
@app.route("/")
def health():
    return jsonify({"status":"online","model":GROQ_MODEL,"message":"Jarvis online, Sir."})

@app.route("/api/chat", methods=["POST"])
@auth
def chat():
    d = request.json or {}
    msg  = d.get("message","").strip()
    hist = [m for m in d.get("history",[]) if m.get("role") in ("user","assistant")][-24:]
    if not msg: return jsonify({"response":"No message, Sir."}), 400
    if not hist or hist[-1].get("content") != msg:
        hist.append({"role":"user","content":msg})
    reply = ask(hist, system=CHAT_SYSTEM)

    # If Jarvis decided the request needs the browser, dispatch it.
    m = re.search(r"\[\[BROWSER\]\]\s*([^\[]*)", reply)
    extra = ""
    if m and m.group(1).strip():
        cmd = m.group(1).strip()
        planned = plan_steps(cmd)
        if planned:
            task = enqueue_browser(cmd, planned)
            browser_iters[task["chain"]] = BROWSER_MAX_ITERS
            extra = (f"\n\n🌐 Browser: I've queued \"{cmd}\" ({len(planned)} actions). "
                     f"Your extension is carrying it out — the result lands on the Browser page and Telegram, Sir.")
        else:
            extra = f"\n\n⚠️ Browser: I couldn't plan \"{cmd}\", Sir."
        reply = re.sub(r"\[\[BROWSER\]\][^\[]*", "", reply).rstrip()
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
    browser_tab.clear()
    browser_tab.update({"url": d.get("url",""), "title": d.get("title","")})
    browser_last_seen = time.time()
    return jsonify({"ok": True})

@app.route("/api/browser/status", methods=["GET"])
@auth
def browser_status():
    return jsonify({
        "connected": bool(browser_tab) and (time.time() - browser_last_seen) < 60,
        "tab": browser_tab,
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

# ── START ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    threading.Thread(target=canvas_loop, daemon=True).start()
    threading.Thread(target=outlook_loop, daemon=True).start()
    port = int(os.getenv("PORT", 5000))
    print(f"Jarvis backend online on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
