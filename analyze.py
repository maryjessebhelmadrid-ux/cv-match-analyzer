import json
import sys

import anthropic
from dotenv import load_dotenv
from pydantic import ValidationError

from schema import MatchResult

load_dotenv()
client = anthropic.Anthropic()

DEFAULT_MODEL = "claude-haiku-5-5"

SYSTEM_PROMPT = """You are a careful recruiter assistant. You compare a CV against a job posting.

Return ONLY a JSON object (no markdown, no commentary) with exactly these keys:
- match_score: integer 0-100. Anchors: 0-20 unrelated, 21-40 weak, 41-60 partial, 61-80 good, 81-100 strong.
- summary: 2-3 sentences explaining the score.
- matched_skills: list of {"skill": str, "evidence": str}. "evidence" MUST be an exact, verbatim
  quote copied from the CV (max 25 words). If you cannot quote it, do not list the skill.
- missing_requirements: list of {"requirement": str, "importance": "must_have" | "nice_to_have"}.
  Only include requirements that are actually stated in the job posting.
- suggested_cv_edits: list of {"section": str, "suggestion": str}. Only suggest rewording or
  reordering things the candidate has really done. Never suggest claiming skills or experience
  that are not in the CV.

Be strict and honest. Do not invent anything."""


def _parse(raw: str) -> MatchResult:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    return MatchResult.model_validate(json.loads(text))


def analyze(cv_text: str, job_text: str, model: str = DEFAULT_MODEL, retries: int = 1):
    """Returns (result_or_None, raw_text). result is None if output was invalid JSON/schema."""
    user_msg = f"<cv>\n{cv_text}\n</cv>\n\n<job_posting>\n{job_text}\n</job_posting>"
    raw = ""
    for _ in range(retries + 1):
        msg = client.messages.create(
            model=model,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = "".join(b.text for b in msg.content if b.type == "text")
        try:
            return _parse(raw), raw
        except (json.JSONDecodeError, ValidationError):
            continue
    return None, raw


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python analyze.py cv.txt job.txt")
    cv = open(sys.argv[1], encoding="utf-8").read()
    job = open(sys.argv[2], encoding="utf-8").read()
    result, raw = analyze(cv, job)
    if result is None:
        print("Model output was not valid. Raw output:\n", raw)
    else:
        print(result.model_dump_json(indent=2))