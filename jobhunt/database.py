import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base
from config import DATABASE_URL

logger = logging.getLogger(__name__)
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate()


def _migrate():
    """Add new columns to existing DB without losing data."""
    new_columns = [
        ("level", "VARCHAR DEFAULT ''"),
        ("reply_subject", "VARCHAR"),
        ("reply_sender", "VARCHAR"),
        ("reply_date", "DATETIME"),
    ]
    with engine.connect() as conn:
        existing = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(jobs)")).fetchall()
        }
        for col_name, col_def in new_columns:
            if col_name not in existing:
                conn.execute(text(f"ALTER TABLE jobs ADD COLUMN {col_name} {col_def}"))
                logger.info(f"DB migration: added column '{col_name}'")
        conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
