@echo off
echo [jobhunt] Installing dependencies...
python -m pip install -r requirements.txt
python -m playwright install chromium
echo.
echo [jobhunt] Done. Run with: python run.py
echo.
echo [Cover Letter setup]
echo   Set ANTHROPIC_API_KEY before running:
echo   set ANTHROPIC_API_KEY=sk-ant-...
echo.
echo [Gmail setup]
echo   1. Go to console.cloud.google.com
echo   2. New project ^> Enable "Gmail API"
echo   3. OAuth consent screen ^> External ^> add your Gmail as test user
echo   4. Credentials ^> Create ^> OAuth 2.0 Client ID ^> Desktop App
echo   5. Download JSON ^> save as credentials.json in this folder
echo   6. Run the app — browser opens for auth on first launch
echo   7. token.json is saved automatically
