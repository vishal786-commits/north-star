from typing import Literal
from pydantic import BaseModel, Field

class ATSScore(BaseModel):
    overall: int = Field(ge=0, le=100)
    keyword_match: int = Field(ge=0, le=100)
    formatting: int = Field(ge=0, le=100)
    quantification: int = Field(ge=0, le=100)
    notes: list[str]

class SectionAnalysis(BaseModel):
    section_name: str
    is_standard: bool
    score: int = Field(ge=0, le=100)
    strengths: list[str]
    issues: list[str]
    suggestions: list[str]

class LengthAssessment(BaseModel):
    page_count: int
    is_appropriate: bool
    verdict: str

class CareerPath(BaseModel):
    current_role: str
    current_scope: str
    future_scope: str
    timeline: str

class ParallelPath(BaseModel):
    title: str
    fit_reason: str
    requirements: list[str]                       # was: str
    effort_level: Literal["low", "medium", "high"]  # was: str

class Analysis(BaseModel):
    ats: ATSScore
    length: LengthAssessment
    sections: list[SectionAnalysis]        # one entry per detected section
    overall_improvements: list[str]        # cross-cutting, whole-resume fixes
    primary_path: CareerPath
    parallel_paths: list[ParallelPath] = Field(min_items=2, max_items=3)  # exactly 2-3 realistic paths
    summary: str

class AnalyzeResponse(BaseModel):
    session_id: str
    analysis: Analysis