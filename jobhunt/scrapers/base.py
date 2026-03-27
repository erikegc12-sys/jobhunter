from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class JobItem:
    title: str
    company: str
    url: str
    platform: str
    location: str = ""
    description: str = ""
    region: str = "International"
    category: str = ""
    level: str = ""
    date_found: datetime = field(default_factory=datetime.utcnow)
