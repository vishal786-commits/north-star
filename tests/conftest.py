"""Shared test setup.

Provide dummy secrets BEFORE anything imports `app.config`, so `Settings()`
constructs without a real `.env` (env vars take precedence over the .env file).
No real Redis or OpenAI is ever contacted — tests fake both.
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from app.schemas import (  # noqa: E402  (import after env is set)
    Analysis,
    ATSScore,
    BulletRewrite,
    CareerPath,
    CutItem,
    DefensibilityFlag,
    FitAnalysis,
    LengthAssessment,
    ParallelPath,
    Parseability,
)


def sample_analysis() -> Analysis:
    """A minimal, schema-valid Analysis for mocking analyze_resume."""
    return Analysis(
        market="india_modern",
        ats=ATSScore(overall=80, keyword_match=70, formatting=90,
                     quantification=60, notes=["ok"]),
        parseability=Parseability(score=85, passes_plaintext_test=True,
                                  issues=[], notes=["clean single column"]),
        length=LengthAssessment(page_count=1, is_appropriate=True, verdict="fine"),
        sections=[],
        bullet_rewrites=[
            BulletRewrite(section="Experience", original="Responsible for reports",
                          rewrite="Built 12 weekly dashboards used by 3 teams",
                          why="added a verb and volume"),
        ],
        defensibility_flags=[
            DefensibilityFlag(claim="Expert in Kubernetes", risk="no k8s project shown",
                              suggestion="quantify or cut"),
        ],
        cut_list=[CutItem(item="objective statement", reason="dead weight for modern employers")],
        overall_improvements=["tighten bullets"],
        primary_path=CareerPath(current_role="Analyst", current_scope="data",
                                future_scope="senior analyst", timeline="1y"),
        parallel_paths=[
            ParallelPath(title="Data Engineer", fit_reason="sql",
                         requirements=["pipelines"], effort_level="medium"),
            ParallelPath(title="PM", fit_reason="comms",
                         requirements=["roadmaps"], effort_level="high"),
        ],
        summary="solid",
    )


def sample_fit() -> FitAnalysis:
    """A minimal, schema-valid FitAnalysis for mocking analyze_fit."""
    return FitAnalysis(
        market="india_modern",
        match_score=75,
        verdict="decent",
        matched_requirements=["python"],
        missing_requirements=["k8s"],
        strengths_for_role=["fast learner"],
        gaps=["infra"],
        tailoring_suggestions=["surface metrics"],
        bullet_rewrites=[
            BulletRewrite(section="Experience", original="Worked on APIs",
                          rewrite="Shipped 5 REST endpoints serving 2K req/day",
                          why="added scope and volume"),
        ],
        summary="close",
    )
