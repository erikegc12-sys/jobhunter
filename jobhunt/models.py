from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    url = Column(String, unique=True, nullable=False)
    platform = Column(String, nullable=False)
    region = Column(String, default="International")   # BR, Remote, International
    category = Column(String, nullable=False)
    level = Column(String, default="")                 # Junior, Mid, Senior, ""
    status = Column(String, default="new")             # new, saved, applied, dismissed, replied
    date_found = Column(DateTime, default=datetime.utcnow)
    description = Column(Text, nullable=True)
    location = Column(String, nullable=True)

    # Gmail reply metadata
    reply_subject = Column(String, nullable=True)
    reply_sender = Column(String, nullable=True)
    reply_date = Column(DateTime, nullable=True)
