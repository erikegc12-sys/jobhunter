"""One-shot Gmail OAuth — run this once to generate token.json."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from gmail_checker import get_gmail_service

print("Opening browser for Gmail authorization...")
svc = get_gmail_service()
if svc:
    print("✅ Gmail authorized — token.json saved")
else:
    print("❌ Authorization failed — check credentials.json")
