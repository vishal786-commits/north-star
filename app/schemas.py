from typing import Literal
from pydantic import BaseModel, Field

# Target market the resume is being optimised for. Drives length rules, what-to-cut,
# spelling (CV vs resume, British vs US), and market-specific conventions.
Market = Literal["india_modern", "india_traditional", "uk", "us_global"]

class ATSScore(BaseModel):
    overall: int = Field(ge=0, le=100)
    keyword_match: int = Field(ge=0, le=100)
    formatting: int = Field(ge=0, le=100)
    quantification: int = Field(ge=0, le=100)
    notes: list[str]

class Parseability(BaseModel):
    """Machine-readability of the document — distinct from ATS content quality.
    Framed to debunk the 'ATS auto-rejects' myth: issues mean the resume gets
    BURIED or mis-parsed, not silently deleted by a robot."""
    score: int = Field(ge=0, le=100, description="Higher = cleaner, more reliable parsing.")
    passes_plaintext_test: bool = Field(description="Would it read top-to-bottom in the right order as plain text?")
    issues: list[str] = Field(description="Concrete parse risks, e.g. two-column layout, tables, contact info in header.")
    notes: list[str] = Field(description="Guidance INCLUDING the myth-correcting reassurance that an ATS does not auto-reject.")

class BulletRewrite(BaseModel):
    """A weak, real resume bullet rewritten into XYZ form. Never fabricated."""
    section: str = Field(description="Section the bullet belongs to.")
    original: str = Field(description="The weak bullet, quoted or closely paraphrased from the resume.")
    rewrite: str = Field(description="XYZ-form rewrite grounded strictly in existing resume content — no invented metrics.")
    why: str = Field(description="What got stronger — added verb, surfaced metric, showed impact.")

class DefensibilityFlag(BaseModel):
    """A claim/skill/number that likely won't survive interview cross-examination."""
    claim: str = Field(description="The resume claim, listed skill, or number at risk.")
    risk: str = Field(description="Why a sharp interviewer (esp. an Indian panel) would probe it.")
    suggestion: str = Field(description="Defend it (add evidence), quantify it, or cut it.")

class CutItem(BaseModel):
    """A piece of dead weight to remove, tuned to the target market."""
    item: str = Field(description="The thing to remove, e.g. 'objective statement', 'photo', 'notice period'.")
    reason: str = Field(description="Why it should go for this market.")

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
    market: Market = Field(description="The market this analysis was optimised for — echo back the market you were told to target.")
    ats: ATSScore
    parseability: Parseability
    length: LengthAssessment
    sections: list[SectionAnalysis]        # one entry per detected section
    bullet_rewrites: list[BulletRewrite]   # 3-6 weakest real bullets rewritten in XYZ form
    defensibility_flags: list[DefensibilityFlag]  # claims that won't survive interview probing
    cut_list: list[CutItem]                # market-tuned dead weight to remove
    overall_improvements: list[str]        # cross-cutting, whole-resume fixes
    primary_path: CareerPath
    parallel_paths: list[ParallelPath] = Field(min_length=2, max_length=3)  # exactly 2-3 realistic paths
    summary: str

class FitAnalysis(BaseModel):
    """How well a resume fits a specific job description."""
    market: Market = Field(description="The market this fit check was optimised for — echo back the market you were told to target.")
    match_score: int = Field(ge=0, le=100)        # overall fit, evidence-based
    verdict: str                                  # one-line honest call
    matched_requirements: list[str]               # JD needs the evidence supports
    missing_requirements: list[str]               # JD needs the resume does NOT demonstrate
    strengths_for_role: list[str]                 # what makes them a strong candidate here
    gaps: list[str]                               # concrete gaps to close
    tailoring_suggestions: list[str]              # how to tailor the resume for THIS job
    bullet_rewrites: list[BulletRewrite]          # weak real bullets rewritten in XYZ form, tailored to THIS job
    summary: str

class AnalyzeResponse(BaseModel):
    session_id: str
    analysis: Analysis

class FitResponse(BaseModel):
    session_id: str
    fit: FitAnalysis

class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(min_length=1, max_length=4000)

class ChatResponse(BaseModel):
    reply: str
    messages_remaining: int
    limit_reached: bool

class FeedbackRequest(BaseModel):
    session_id: str
    rating: Literal["up", "down"]
    comment: str | None = None