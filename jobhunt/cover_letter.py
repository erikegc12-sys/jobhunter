"""
Cover letter generator using Claude API.

Requires ANTHROPIC_API_KEY env var.
Run setup.bat and set the key before starting the app.
"""

import logging
import anthropic

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None

PROFILE = """\
Name: Erik Gomes
Portfolio: erikgomes.com.br
Current role: Post Production Editor @ G4 Educação (Mar 2025–present)
Highlights: 10M+ views on produced content; 7M views on a single viral video;
clients include G4 Educação, Red Bull, J.P. Morgan
Skills: Premiere Pro, After Effects, Motion Graphics, Color Grading\
"""

PROMPT_TEMPLATE = """\
Job: {title} at {company} — category: {category}

Write a cover letter for Erik Gomes. Rules:
- 3 paragraphs, max 120 words total
- P1: one sentence, why THIS company/role specifically
- P2: one or two sentences, most relevant experience for THIS role only
- P3: one sentence CTA + portfolio link erikgomes.com.br
- Zero filler words ("I am writing to", "passionate", "team player")
- Cinematic roles → lead with storytelling
- Editor roles → lead with results and views
- Motion roles → lead with visual identity
- {language}
Output only the letter. Nothing else.\
"""


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    return _client


def generate_cover_letter(job: dict) -> str:
    """
    Generate a cover letter for the given job dict.
    Synchronous — call via run_in_executor from async context.
    """
    region = job.get("region", "International")
    language = "Write in English." if region in ("International", "Remote") else "Escreva em português."

    prompt = PROMPT_TEMPLATE.format(
        title=job.get("title", ""),
        company=job.get("company", ""),
        category=job.get("category", ""),
        language=language,
    )

    client = _get_client()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        temperature=0,
        system=f"You are a cover letter writer. Candidate profile:\n{PROFILE}",
        messages=[{"role": "user", "content": prompt}],
    )

    text = next((b.text for b in response.content if b.type == "text"), "").strip()
    logger.info(f"Cover letter generated for '{job.get('title')}' @ {job.get('company')} ({len(text)} chars)")
    return text
