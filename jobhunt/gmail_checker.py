"""
Gmail integration — detects replies from companies where you applied.

Setup (one-time):
  1. Go to console.cloud.google.com
  2. Create a project → Enable "Gmail API"
  3. OAuth consent screen → External → add your Gmail as test user
  4. Credentials → Create → OAuth 2.0 Client ID → Desktop App
  5. Download JSON → save as credentials.json next to this file
  6. Run the app — browser will open for auth on first launch
  7. token.json is created automatically and reused on future runs
"""

import logging
import os
import re
from datetime import datetime
from email.utils import parsedate_to_datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from database import SessionLocal
from models import Job
from config import GMAIL_SUBJECT_KEYWORDS, COMPANY_DOMAIN_MAP

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
BASE_DIR = os.path.dirname(__file__)
TOKEN_PATH = os.path.join(BASE_DIR, "token.json")
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")

# Platforms that are NOT company domains (skip for from: matching)
ATS_DOMAINS = {
    "greenhouse.io", "lever.co", "workday.com", "myworkdayjobs.com",
    "indeed.com", "glassdoor.com", "linkedin.com",
}

# Shared state for API
gmail_state = {
    "last_run": None,
    "last_result": None,
    "authorized": None,  # True/False/None (unknown)
}


# ─── Auth ─────────────────────────────────────────────────────────────────────

def get_gmail_service():
    """Return authenticated Gmail API service, or None if not possible."""
    if not os.path.exists(CREDENTIALS_PATH):
        logger.warning(
            "credentials.json not found — Gmail integration disabled. "
            "See gmail_checker.py docstring for setup instructions."
        )
        gmail_state["authorized"] = False
        return None

    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.warning(f"Gmail token refresh failed: {e}")
                creds = None

        if not creds:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                logger.error(f"Gmail OAuth flow failed: {e}")
                gmail_state["authorized"] = False
                return None

        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    gmail_state["authorized"] = True
    return build("gmail", "v1", credentials=creds)


# ─── Domain helpers ───────────────────────────────────────────────────────────

def _domain_from_url(url: str) -> str | None:
    match = re.search(r"https?://(?:www\.)?([^/]+)", url)
    if not match:
        return None
    host = match.group(1).lower()
    if any(host.endswith(ats) for ats in ATS_DOMAINS):
        return None
    return host


def _domains_for_company(company: str, url: str) -> list[str]:
    domains = set()
    url_domain = _domain_from_url(url)
    if url_domain:
        domains.add(url_domain)
    key = company.lower().strip()
    if key in COMPANY_DOMAIN_MAP:
        domains.update(COMPANY_DOMAIN_MAP[key])
    else:
        # Best-effort: strip non-alpha and append .com
        slug = re.sub(r"[^a-z0-9]", "", key)
        if slug:
            domains.add(f"{slug}.com")
    return list(domains)


# ─── Gmail query ──────────────────────────────────────────────────────────────

def _build_query(all_domains: list[str]) -> str:
    """Build Gmail search query. Chunks domains to stay within query limits."""
    domain_clause = ""
    if all_domains:
        # Limit to 50 domains per query to avoid hitting Gmail query length limits
        top_domains = all_domains[:50]
        domain_clause = "(" + " OR ".join(f"from:{d}" for d in top_domains) + ")"

    subj_clause = "(" + " OR ".join(f'subject:"{kw}"' for kw in GMAIL_SUBJECT_KEYWORDS) + ")"

    if domain_clause:
        return f"{domain_clause} OR {subj_clause}"
    return subj_clause


# ─── Message parsing ──────────────────────────────────────────────────────────

def _get_headers(service, msg_id: str) -> dict:
    msg = service.users().messages().get(
        userId="me", id=msg_id, format="metadata",
        metadataHeaders=["From", "Subject", "Date"],
    ).execute()
    return {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}


def _match_to_job(sender: str, subject: str, candidates: list[tuple]) -> int | None:
    """
    candidates: list of (job_id, company, domains)
    Returns job_id of best match, or None.
    """
    sender_lower = sender.lower()
    subject_lower = subject.lower()

    # Priority 1: exact domain match in sender
    for job_id, company, domains in candidates:
        for domain in domains:
            if domain in sender_lower:
                return job_id

    # Priority 2: company name token in subject
    for job_id, company, domains in candidates:
        tokens = [w for w in company.lower().split() if len(w) > 3]
        if tokens and any(t in subject_lower for t in tokens):
            return job_id

    return None


# ─── Main check ───────────────────────────────────────────────────────────────

def check_gmail() -> dict:
    """
    Synchronous — run via run_in_executor from async context.
    Checks inbox and updates replied jobs in DB.
    """
    service = get_gmail_service()
    if service is None:
        return {"skipped": True, "reason": "not_authorized"}

    db = SessionLocal()
    try:
        # Only check jobs marked as "applied"
        applied_jobs = db.query(Job).filter(Job.status == "applied").all()
        if not applied_jobs:
            logger.info("Gmail: no applied jobs to check")
            return {"checked": 0, "matched": 0}

        candidates = [
            (j.id, j.company, _domains_for_company(j.company, j.url))
            for j in applied_jobs
        ]
        all_domains = list({d for _, _, doms in candidates for d in doms})

        query = _build_query(all_domains)
        logger.info(f"Gmail: querying inbox...")

        results = service.users().messages().list(
            userId="me", q=query, maxResults=100,
        ).execute()
        messages = results.get("messages", [])
        logger.info(f"Gmail: {len(messages)} messages matched")

        matched = 0
        for stub in messages:
            try:
                headers = _get_headers(service, stub["id"])
                sender = headers.get("From", "")
                subject = headers.get("Subject", "")
                date_str = headers.get("Date", "")

                try:
                    email_date = parsedate_to_datetime(date_str).replace(tzinfo=None)
                except Exception:
                    email_date = datetime.utcnow()

                job_id = _match_to_job(sender, subject, candidates)
                if job_id is None:
                    continue

                job = db.query(Job).filter(Job.id == job_id).first()
                if not job or job.status == "replied":
                    continue

                job.status = "replied"
                job.reply_subject = subject[:500]
                job.reply_sender = sender[:200]
                job.reply_date = email_date
                db.commit()
                matched += 1
                logger.info(f"Gmail reply → #{job.id} '{job.title}' @ {job.company} | {subject[:60]}")

            except HttpError as e:
                logger.error(f"Gmail API error on message {stub['id']}: {e}")
                continue

        result = {
            "checked": len(messages),
            "matched": matched,
            "timestamp": datetime.utcnow().isoformat(),
        }
        gmail_state["last_run"] = result["timestamp"]
        gmail_state["last_result"] = result
        return result

    except Exception as e:
        db.rollback()
        logger.error(f"Gmail check error: {e}")
        result = {"checked": 0, "matched": 0, "error": str(e)}
        gmail_state["last_result"] = result
        return result
    finally:
        db.close()
