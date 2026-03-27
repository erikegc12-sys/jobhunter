from config import KEYWORDS, EXCLUDE_KEYWORDS, CATEGORIES, BR_SIGNALS


def matches_keywords(text: str) -> bool:
    low = text.lower()
    return any(kw in low for kw in KEYWORDS)


def is_excluded(title: str, description: str = "") -> bool:
    """Exclude management/principal roles and extreme experience requirements."""
    combined = (title + " " + description).lower()
    return any(ex in combined for ex in EXCLUDE_KEYWORDS)


def get_category(title: str, description: str = "") -> str | None:
    combined = (title + " " + description).lower()
    for category, kws in CATEGORIES.items():
        if any(kw in combined for kw in kws):
            return category
    return None


def detect_level(title: str, description: str = "") -> str:
    """Returns Senior, Mid, Junior, or empty string."""
    combined = (title + " " + description).lower()
    if any(w in combined for w in ["senior", "sr.", " sr "]):
        return "Senior"
    if any(w in combined for w in ["mid-level", "mid level", "intermediate", " mid "]):
        return "Mid"
    if any(w in combined for w in ["junior", "jr.", " jr ", "entry level", "entry-level"]):
        return "Junior"
    return ""


def detect_region(location: str, description: str = "") -> str:
    combined = (location + " " + description).lower()
    if any(sig in combined for sig in BR_SIGNALS):
        return "BR"
    if "remote" in combined:
        return "Remote"
    return "International"


def should_include(title: str, description: str = "", location: str = "") -> tuple[bool, str | None]:
    """Returns (include, category). No level/seniority filtering — ALL jobs shown."""
    if not matches_keywords(title + " " + description):
        return False, None
    category = get_category(title, description)
    if category is None:
        return False, None
    return True, category
