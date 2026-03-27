"""
Export current jobs from the local API to docs/jobs.json for GitHub Pages.
Run: python export_static.py
Then: git add docs/jobs.json && git commit -m "update jobs" && git push
"""
import json, sys, os
from datetime import datetime, timezone
try:
    import urllib.request as req
    data = req.urlopen("http://localhost:8000/api/jobs", timeout=5).read()
    jobs = json.loads(data)
except Exception as e:
    print(f"ERROR: Could not connect to http://localhost:8000 — is jobhunt running?\n  {e}")
    sys.exit(1)

out = {
    "jobs": jobs,
    "last_updated": datetime.now(timezone.utc).isoformat(),
}

dest = os.path.join(os.path.dirname(__file__), "docs", "jobs.json")
with open(dest, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False)

print(f"✓ Exported {len(jobs)} jobs to docs/jobs.json")
print()
print("Next steps:")
print("  git add docs/jobs.json")
print('  git commit -m "update jobs snapshot"')
print("  git push")
print()
print("GitHub Pages will deploy automatically.")
