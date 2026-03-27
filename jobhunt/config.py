KEYWORDS = [
    # English / International
    "cinematic artist",
    "video editor",
    "motion designer",
    "motion design",
    "social media editor",
    "cinematics",
    "game capture",
    "social media",
    # Portuguese / BR
    "editor de vídeo",
    "editor de video",
    "produtor audiovisual",
]

# No level filtering — show ALL jobs regardless of seniority.
EXCLUDE_KEYWORDS: list[str] = []

CATEGORIES = {
    "Cinematic Artist": ["cinematic artist", "cinematics", "game capture"],
    "Video Editor": [
        "video editor",
        "editor de vídeo",
        "editor de video",
        "produtor audiovisual",
    ],
    "Motion Designer": ["motion designer", "motion design"],
    "Social Media Editor": ["social media editor", "social media"],
}

BR_SIGNALS = [
    "brazil", "brasil", "são paulo", "sao paulo",
    "rio de janeiro", "brasília", "brasilia", ", br",
    "(br)", "brazil remote",
]

# Greenhouse boards (JSON API — public, no auth needed)
GREENHOUSE_BOARDS = [
    {"company": "Riot Games",      "board": "riotgames"},
    {"company": "Epic Games",      "board": "epicgames"},
    {"company": "Bungie",          "board": "bungie"},
    {"company": "Netflix",         "board": "netflix"},
    {"company": "Insomniac Games", "board": "insomniac"},
    {"company": "Naughty Dog",     "board": "naughtydog"},
    {"company": "CD Projekt Red",  "board": "cdprojektred"},
]

# Lever companies (JSON API — public, no auth needed)
LEVER_COMPANIES = [
    {"company": "Valve",           "slug": "valve"},
    {"company": "Larian Studios",  "slug": "larian-studios"},
]

# Workday targets — site_url is the Playwright search URL (en-US/<site>?q=<term>)
# url is the CXS JSON API endpoint (used for network interception)
WORKDAY_TARGETS = [
    {
        "company": "EA",
        "url": "https://ea.wd1.myworkdayjobs.com/wday/cxs/ea/EA_BPO/jobs",
        "site_url": "https://ea.wd1.myworkdayjobs.com/en-US/EA_BPO",
    },
    {
        "company": "Blizzard Entertainment",
        "url": "https://activision.wd1.myworkdayjobs.com/wday/cxs/activision/Blizzard_External/jobs",
        "site_url": "https://activision.wd1.myworkdayjobs.com/en-US/Blizzard_External",
    },
    {
        "company": "2K Games",
        "url": "https://2k.wd1.myworkdayjobs.com/wday/cxs/2k/2K_Careers/jobs",
        "site_url": "https://2k.wd1.myworkdayjobs.com/en-US/2K_Careers",
    },
]

INDEED_QUERIES_INTL = [
    "cinematic artist",
    "video editor game",
    "motion designer game",
    "game capture artist",
    "social media editor",
]

INDEED_QUERIES_BR = [
    "editor de video",
    "motion designer",
    "produtor audiovisual",
    "social media editor",
]

GLASSDOOR_QUERIES = [
    "cinematic artist",
    "video editor",
    "motion designer",
    "social media editor",
]

LINKEDIN_QUERIES_INTL = [
    "cinematic artist",
    "video editor game",
    "motion designer",
    "game capture",
]

LINKEDIN_QUERIES_BR = [
    "editor de video",
    "motion designer",
    "produtor audiovisual",
    "social media",
]

VAGAS_QUERIES = [
    "editor-de-video",
    "motion-designer",
    "produtor-audiovisual",
    "social-media",
]

CATHO_QUERIES = [
    "editor-de-video",
    "motion-designer",
    "social-media",
]

INFOJOBS_QUERIES = [
    "editor-video",
    "motion-designer",
    "social-media",
]

# Gmail: subjects containing any of these trigger a reply match
GMAIL_SUBJECT_KEYWORDS = [
    "application",
    "candidatura",
    "your application",
    "next steps",
    "interview",
    "entrevista",
    "vaga",
    "cinematic artist",
    "video editor",
    "motion designer",
    "motion design",
    "social media editor",
    "cinematics",
    "game capture",
]

# Known company → domain mapping for Gmail sender matching
COMPANY_DOMAIN_MAP = {
    "riot games": ["riotgames.com"],
    "electronic arts": ["ea.com"],
    "ea": ["ea.com"],
    "blizzard entertainment": ["blizzard.com", "activisionblizzard.com"],
    "blizzard": ["blizzard.com"],
    "2k games": ["2k.com", "take2games.com"],
    "2k": ["2k.com"],
    "activision": ["activision.com", "activisionblizzard.com"],
    "ubisoft": ["ubisoft.com"],
    "epic games": ["epicgames.com"],
    "naughty dog": ["naughtydog.com"],
    "santa monica studio": ["sms.playstation.com", "sonyinteractiveentertainment.com"],
    "insomniac games": ["insomniac.com"],
    "cd projekt": ["cdprojektred.com", "cdprojekt.com"],
}

SCRAPE_INTERVAL_HOURS = 6
GMAIL_CHECK_INTERVAL_HOURS = 6

import os
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./jobhunt.db")
