import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import init_db, get_db
from models import Job
from runner import run_all_scrapers, scrape_state
from scheduler import start_scheduler, stop_scheduler
from gmail_checker import check_gmail, gmail_state
from cover_letter import generate_cover_letter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

VALID_STATUSES = {"new", "saved", "applied", "dismissed", "replied"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_scheduler()
    logger.info("jobhunt started — dashboard at http://localhost:8000")
    yield
    stop_scheduler()


app = FastAPI(title="jobhunt", lifespan=lifespan)

BASE_DIR = os.path.dirname(__file__)
DASHBOARD_HTML = os.path.join(BASE_DIR, "templates", "index.html")


# ─── Dashboard ────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return FileResponse(DASHBOARD_HTML)


# ─── API: Jobs ────────────────────────────────────────────────────────────────

def _job_dict(j: Job) -> dict:
    return {
        "id": j.id,
        "title": j.title,
        "company": j.company,
        "url": j.url,
        "platform": j.platform,
        "region": j.region,
        "category": j.category,
        "level": j.level or "",
        "status": j.status,
        "location": j.location or "",
        "date_found": j.date_found.isoformat() if j.date_found else None,
        "reply_subject": j.reply_subject,
        "reply_sender": j.reply_sender,
        "reply_date": j.reply_date.isoformat() if j.reply_date else None,
    }


@app.get("/api/jobs")
async def get_jobs(
    status: str = "",
    category: str = "",
    platform: str = "",
    region: str = "",
    level: str = "",
    q: str = "",
    db: Session = Depends(get_db),
):
    query = db.query(Job)

    if status:
        query = query.filter(Job.status == status)
    if category:
        query = query.filter(Job.category == category)
    if platform:
        query = query.filter(Job.platform == platform)
    if region:
        query = query.filter(Job.region == region)
    if level:
        query = query.filter(Job.level == level)
    if q:
        search = f"%{q}%"
        query = query.filter(
            Job.title.ilike(search) | Job.company.ilike(search)
        )

    jobs = query.order_by(desc(Job.date_found)).all()
    return [_job_dict(j) for j in jobs]


@app.get("/replies")
async def replies_page():
    return FileResponse(DASHBOARD_HTML)


@app.get("/api/replies")
async def get_replies(db: Session = Depends(get_db)):
    jobs = (
        db.query(Job)
        .filter(Job.status == "replied")
        .order_by(desc(Job.reply_date))
        .all()
    )
    return [_job_dict(j) for j in jobs]


@app.patch("/api/jobs/{job_id}/status")
async def update_status(job_id: int, body: dict, db: Session = Depends(get_db)):
    new_status = body.get("status")
    if new_status not in VALID_STATUSES:
        return JSONResponse({"error": f"invalid status, must be one of {VALID_STATUSES}"}, status_code=400)

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return JSONResponse({"error": "not found"}, status_code=404)

    job.status = new_status
    db.commit()
    return {"id": job_id, "status": new_status}


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return JSONResponse({"error": "not found"}, status_code=404)
    db.delete(job)
    db.commit()
    return {"deleted": job_id}


# ─── API: Stats ───────────────────────────────────────────────────────────────

@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    total = db.query(Job).count()
    by_status: dict = {}
    by_category: dict = {}
    by_platform: dict = {}
    by_level: dict = {}

    for job in db.query(Job).all():
        by_status[job.status] = by_status.get(job.status, 0) + 1
        by_category[job.category] = by_category.get(job.category, 0) + 1
        by_platform[job.platform] = by_platform.get(job.platform, 0) + 1
        lv = job.level or "Unknown"
        by_level[lv] = by_level.get(lv, 0) + 1

    return {
        "total": total,
        "by_status": by_status,
        "by_category": by_category,
        "by_platform": by_platform,
        "by_level": by_level,
        "scraper": {
            "running": scrape_state["running"],
            "last_run": scrape_state["last_run"],
            "last_result": scrape_state["last_result"],
        },
        "gmail": {
            "authorized": gmail_state["authorized"],
            "last_run": gmail_state["last_run"],
            "last_result": gmail_state["last_result"],
        },
    }


# ─── API: Scraper ─────────────────────────────────────────────────────────────

@app.post("/api/scrape")
async def trigger_scrape(background_tasks: BackgroundTasks):
    if scrape_state["running"]:
        return {"status": "already_running"}
    background_tasks.add_task(run_all_scrapers)
    return {"status": "started"}


@app.get("/api/scrape/status")
async def scrape_status():
    return {
        "running": scrape_state["running"],
        "last_run": scrape_state["last_run"],
        "last_result": scrape_state["last_result"],
    }


# ─── API: Gmail ───────────────────────────────────────────────────────────────

@app.post("/api/gmail/check")
async def trigger_gmail_check(background_tasks: BackgroundTasks):
    async def _run():
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, check_gmail)

    background_tasks.add_task(_run)
    return {"status": "started"}


@app.get("/api/gmail/status")
async def gmail_check_status():
    return gmail_state


# ─── API: Cover Letter ────────────────────────────────────────────────────────

@app.post("/api/cover-letter/{job_id}")
async def cover_letter(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return JSONResponse({"error": "not found"}, status_code=404)

    job_dict = _job_dict(job)

    try:
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, generate_cover_letter, job_dict)
        return {"text": text}
    except Exception as e:
        logger.error(f"Cover letter generation failed for job #{job_id}: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
