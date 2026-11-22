from typing import Literal
from pydantic import BaseModel, Field


class MatchedSkill(BaseModel):
    skill: str
    evidence: str  # exact quote copied from the CV


class MissingRequirement(BaseModel):
    requirement: str
    importance: Literal["must_have", "nice_to_have"]


class CVEdit(BaseModel):
    section: str
    suggestion: str


class MatchResult(BaseModel):
    match_score: int = Field(ge=0, le=100)
    summary: str
    matched_skills: list[MatchedSkill]
    missing_requirements: list[MissingRequirement]
    suggested_cv_edits: list[CVEdit]
