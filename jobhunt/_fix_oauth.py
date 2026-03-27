"""
Fix Gmail 403 access_denied: add test user then re-run OAuth.
"""
import os, sys, json, webbrowser, subprocess

PROJECT = "jobhunt-491518"
TEST_USER = "erikegc12@gmail.com"
CREDS = os.path.join(os.path.dirname(__file__), "credentials.json")
TOKEN = os.path.join(os.path.dirname(__file__), "token.json")
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

CONSENT_URL = f"https://console.cloud.google.com/apis/credentials/consent?project={PROJECT}"

def open_browser(url):
    try:
        webbrowser.open(url)
    except Exception:
        subprocess.Popen(["cmd.exe", "/c", "start", url])

def add_test_user_instructions():
    print()
    print("=" * 60)
    print()
    print("  Open this exact link in your browser:")
    print()
    print(f"  {CONSENT_URL}")
    print()
    print("  Look for a button that says PUBLISH APP or Publicar app.")
    print("  Click it and confirm.")
    print()
    print("  If you don't see that button, look for Test Users section.")
    print(f"  Add: {TEST_USER}")
    print("  Click Save.")
    print()
    print("  Press Enter when done.")
    print()
    print("=" * 60)
    open_browser(CONSENT_URL)
    input("\n  Press Enter when done... ")

def run_oauth():
    from google_auth_oauthlib.flow import InstalledAppFlow

    print("\n→ Opening browser for Gmail authorization...")
    flow = InstalledAppFlow.from_client_secrets_file(CREDS, scopes=SCOPES)
    creds = flow.run_local_server(port=0)

    with open(TOKEN, "w") as f:
        f.write(creds.to_json())

    print("✅ Gmail connected — token.json saved")
    return True

def main():
    if not os.path.exists(CREDS):
        print("❌ credentials.json not found")
        sys.exit(1)

    # Remove stale token if present
    if os.path.exists(TOKEN):
        os.remove(TOKEN)
        print("→ Removed old token.json")

    # Step 1: Show instructions and open browser
    add_test_user_instructions()

    # Step 2: Run OAuth flow (retry up to 2x if user needs to fix something)
    for attempt in range(1, 4):
        print(f"\n→ Running OAuth flow (attempt {attempt}/3)...")
        try:
            success = run_oauth()
            if success and os.path.exists(TOKEN):
                print("\n✅ All done — Gmail is connected")
                return
        except Exception as e:
            err = str(e)
            if "access_denied" in err or "403" in err:
                print(f"\n⚠ Still getting access_denied (attempt {attempt})")
                if attempt < 3:
                    print("\n  Make sure you:")
                    print(f"  • Added {TEST_USER} as a test user (not just saved the form)")
                    print(f"  • Are signing in WITH {TEST_USER} in the browser popup")
                    print()
                    open_browser(CONSENT_URL)
                    input("  Press Enter after confirming the test user is saved... ")
            else:
                print(f"\n❌ OAuth error: {err}")
                if attempt >= 3:
                    sys.exit(1)

    print("\n❌ Could not complete OAuth after 3 attempts.")
    print(f"   Make sure {TEST_USER} is added as a Test User at:")
    print(f"   {CONSENT_URL}")
    sys.exit(1)

if __name__ == "__main__":
    main()
