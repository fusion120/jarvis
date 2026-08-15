"""
setup_outlook_oauth.py — Run this ONCE on your local PC to create an Outlook
OAuth2 refresh token for Jarvis.

Microsoft disabled basic IMAP/SMTP auth for Outlook/M365 accounts, so Jarvis
now logs in with an OAuth2 access token (XOAUTH2). This script does the one-time
interactive sign-in (opens your browser), then prints the REFRESH TOKEN you
paste into Render's OUTLOOK_REFRESH_TOKEN env var. The refresh token is
long-lived and lets Render mint new access tokens forever without a browser.

USAGE:
  1. In Azure Portal (entra.microsoft.com) create an App Registration:
       - Type: "Public client (mobile & desktop)"
       - Redirect URI: http://localhost:8400  (type: Mobile/Desktop)
       - API permissions: add "Microsoft Graph" delegated →
           IMAP.AccessAsUser.All, SMTP.Send, offline_access
       - Copy the Application (client) ID and the Directory (tenant) ID.
  2. pip install msal
  3. Run:  python backend/setup_outlook_oauth.py
     and answer the prompts. It opens a browser for you to sign in.
  4. Copy the printed OUTLOOK_REFRESH_TOKEN into Render's env vars, plus
     OUTLOOK_CLIENT_ID, OUTLOOK_TENANT_ID, and OUTLOOK_EMAIL.

Requires Python 3.8+.
"""

import webbrowser
import urllib.parse
import http.server
import threading
import sys

try:
    import msal
except ImportError:
    print("Missing dependency. Run:  pip install msal")
    sys.exit(1)

SCOPES = ["https://outlook.office365.com/IMAP.AccessAsUser.All",
          "https://outlook.office365.com/SMTP.Send",
          "offline_access"]
REDIRECT_URI = "http://localhost:8400"
AUTHORITY = "https://login.microsoftonline.com/{tenant}"

# Minimal local server to catch the OAuth redirect
auth_code = {}

class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        auth_code["code"] = params.get("code", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h2>Jarvis Outlook auth complete. You can close this tab.</h2>")
        self.server.stop = True

    def log_message(self, *a):
        pass

def main():
    client_id = input("Azure App (client) ID: ").strip()
    tenant_id = input("Azure Directory (tenant) ID [or 'common']: ").strip() or "common"
    email = input("Your Outlook/M365 email: ").strip()

    app = msal.PublicClientApplication(client_id, authority=AUTHORITY.format(tenant=tenant_id))

    # Start local redirect server
    server = http.server.HTTPServer(("localhost", 8400), _Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    # Build auth URL and open browser
    flow = app.initiate_auth_code_flow(SCOPES, redirect_uri=REDIRECT_URI)
    print("\nOpening browser for sign-in...")
    webbrowser.open(flow["authorization_uri"])

    # Wait for redirect
    print("Waiting for you to sign in (browser window)...")
    while not auth_code.get("code"):
        import time
        time.sleep(0.5)
    server.shutdown()

    # Exchange code for tokens
    result = app.acquire_token_by_auth_code_flow(flow,
        {"code": auth_code["code"],
         "state": flow["state"],
         "redirect_uri": REDIRECT_URI})

    if "refresh_token" in result:
        print("\n" + "=" * 60)
        print("SUCCESS. Copy these into Render's env vars:")
        print("=" * 60)
        print(f"OUTLOOK_EMAIL={email}")
        print(f"OUTLOOK_CLIENT_ID={client_id}")
        print(f"OUTLOOK_TENANT_ID={tenant_id}")
        print(f"OUTLOOK_REFRESH_TOKEN={result['refresh_token']}")
        print("=" * 60)
        print("\nKeep the refresh token secret — it grants long-term email access.")
    else:
        print("FAILED:", result.get("error_description", "unknown error"))

if __name__ == "__main__":
    main()
