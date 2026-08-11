---
lang: python
keywords: email, smtp, smtplib, send mail, MIME, attachment, ssl, gmail, EmailMessage, mail
---

# Sending email with attachments via smtplib

`smtplib` speaks SMTP; `email.message.EmailMessage` builds a MIME message with a text body and
attachments. The standard flow: construct the message, connect over TLS/SSL, log in, send.

```python
import smtplib
from email.message import EmailMessage


def send_email(
    host: str,
    port: int,
    username: str,
    password: str,
    to: str,
    subject: str,
    body: str,
    attachment_path: str | None = None,
) -> None:
    msg = EmailMessage()
    msg["From"] = username
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)                       # plain-text part

    if attachment_path:
        with open(attachment_path, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="application",
                subtype="octet-stream",
                filename=attachment_path.rsplit("/", 1)[-1],
            )

    with smtplib.SMTP_SSL(host, port, timeout=30) as server:   # implicit TLS (465)
        server.login(username, password)
        server.send_message(msg)


# send_email("smtp.gmail.com", 465, "me@gmail.com", "app-password",
#            "you@example.com", "Subject line", "Hello from Python")
```

Gotchas:
- Use `SMTP_SSL` for port 465, or `SMTP` + `starttls()` for port 587 — matching the wrong
  transport to the port fails with an SMTP handshake error.
- Gmail and most providers need an **app password / OAuth**, not your normal account password —
  and the SMTP `login` will raise `SMTPAuthenticationError` if the account has 2FA.
- `msg["To"]` may contain a display name (`"Ada <a@b.com>"`); use the `email.utils.formataddr`
  helper rather than hand-stringing headers.
- Set a `timeout=` on the SMTP connection or a dead mail server hangs your program for minutes.
- Attachments: always binary-read the file; `filename` with a path leaks the full path in
  headers — pass just the basename.
- `send_message` serializes the message with RFC-compliant line endings; don't hand-build the
  raw text, and call `msg.set_content` before `add_attachment` so the text stays the first part.
