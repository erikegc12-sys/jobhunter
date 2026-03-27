#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

PYTHON="/c/Users/Erike/AppData/Local/Programs/Python/Python312/python.exe"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  jobhunt"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Install dependencies
echo "Installing dependencies..."
"$PYTHON" -m pip install -q -r requirements.txt
"$PYTHON" -m playwright install chromium --quiet 2>/dev/null || "$PYTHON" -m playwright install chromium
echo "  OK  Dependencies ready"

# 2. Gmail OAuth if needed
if [ -f "credentials.json" ] && [ ! -f "token.json" ]; then
  echo "Running Gmail OAuth (browser will open)..."
  "$PYTHON" -c "from gmail_checker import get_gmail_service; get_gmail_service()"
  echo "  OK  Gmail authorized"
elif [ ! -f "credentials.json" ]; then
  echo "  --  credentials.json not found, Gmail disabled"
fi

# 3. Start server
echo "Starting server..."
"$PYTHON" -m uvicorn main:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!

# Wait until ready
for i in $(seq 1 20); do
  sleep 1
  if curl -s http://localhost:8000/api/stats >/dev/null 2>&1; then break; fi
done
echo "  OK  Server running at http://localhost:8000"

# 4. Initial scrape
curl -s -X POST http://localhost:8000/api/scrape >/dev/null 2>&1
echo "  OK  Initial scrape started"

# 5. Open browser
sleep 1
powershell.exe -Command "Start-Process 'http://localhost:8000'" 2>/dev/null || \
  xdg-open http://localhost:8000 2>/dev/null || \
  open http://localhost:8000 2>/dev/null || true
echo "  OK  Browser opened"

echo ""
echo "  Dashboard : http://localhost:8000"
echo "  Scraper   : every 6h"
echo "  Gmail     : every 30min"
echo "  Ctrl+C to stop"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

trap "kill $SERVER_PID 2>/dev/null; echo 'Stopped.'; exit 0" INT TERM
wait $SERVER_PID
