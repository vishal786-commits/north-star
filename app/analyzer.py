import json
import logging
import time

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.config import settings
from app.schemas import Analysis, FitAnalysis
from app.errors import AnalysisError

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=45)

MODEL = "gpt-4o-mini"
MAX_RETRIES = 1


def _meta(response, llm_ms: float) -> dict:
    """Pull the monitoring metadata off an OpenAI response.

    Token usage was previously discarded — capturing it here is what lets the
    metrics layer track cost and latency per request.
    """
    usage = getattr(response, "usage", None)
    return {
        "model": MODEL,
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
        "llm_ms": round(llm_ms, 1),
    }


SYSTEM_PROMPT = """You are an expert, honest career coach and resume analyst.

Analyze resumes SECTION BY SECTION. Identify EVERY section present — standard
ones (Education, Experience, Skills, Projects, etc.) AND any custom or unusual
sections the candidate created. For each, give an honest score and specific
strengths, issues, and suggestions.

CRITICAL — assess EVIDENCE, not self-description. A resume is a marketing
document that projects an aspirational identity. Do NOT repeat the candidate's
framing back as fact.
- Distinguish what the resume CLAIMS from what it actually DEMONSTRATES through
  concrete evidence (shipped work, measurable outcomes, real scope, tenure).
- primary_path.current_role MUST state the role the evidence actually supports,
  NOT the title the resume brands itself with. If the self-labeling outruns the
  demonstrated evidence (e.g. "AI Engineer" on a resume whose real history is
  analytics plus some AI projects), name the genuine current position AND make
  the gap explicit in current_scope. That gap is the single most valuable thing
  a coach surfaces.
- current_scope describes what they have genuinely demonstrated — not the
  aspirational scope the resume implies.

parallel_paths: ALWAYS provide EXACTLY 2 to 3 realistic parallel career paths.
NEVER return an empty list. Each has discrete concrete requirements (a list of
items, not one sentence) and effort_level of exactly "low", "medium", or "high".

Assess length: one page is strongly preferred; more is appropriate only when
justified by senior experience or genuinely dense, relevant content.

Be concrete, realistic, and honest. Avoid generic filler. Base everything
strictly on the actual resume content."""

async def analyze_resume(resume_text: str, page_count: int) -> tuple[Analysis, dict]:
    """Analyze a resume. Returns (analysis, meta) where meta carries token
    usage + latency for the monitoring layer."""
    schema = json.dumps(Analysis.model_json_schema(), indent=2)

    user_prompt = f"""Analyze the resume below and strictly return only a JSON object that matches the
    schema provided. Do not include any markdown or commentary.
    Schema:{schema}
    The resume has {page_count} page(s) — use this for your length assessment.

    Resume:{resume_text}"""

    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            started = time.perf_counter()
            response = await client.chat.completions.create(
                model=MODEL,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            llm_ms = (time.perf_counter() - started) * 1000
            raw = response.choices[0].message.content
            return Analysis.model_validate_json(raw), _meta(response, llm_ms)

        except ValidationError as e:
            # The model returned JSON, but not OUR shape. Worth a retry.
            last_error = e
            logger.warning(
                "LLM output failed schema validation (attempt %d/%d): %s",
                attempt + 1, MAX_RETRIES + 1, e,
            )
            continue

        except Exception as e:
            # Network error, timeout, auth, etc. — not worth retrying blindly.
            logger.exception("OpenAI request failed")
            raise AnalysisError("The analysis service is unavailable.") from e

    # Exhausted retries on validation failures.
    raise AnalysisError(
        "The AI returned malformed data after retrying."
    ) from last_error


FIT_SYSTEM_PROMPT = """You are an expert, honest career coach assessing how well a candidate's
resume fits a SPECIFIC job. You are given the full resume text and a job description.

CRITICAL — assess EVIDENCE, not keyword surface or self-description. A resume is a marketing
document; a job description is a wish list. Compare what the resume actually DEMONSTRATES
(shipped work, measurable outcomes, real scope, tenure) against what the job GENUINELY requires.

- match_score reflects real, demonstrated fit for THIS role — not how many keywords overlap.
- matched_requirements: job needs the resume genuinely supports with evidence.
- missing_requirements: job needs the resume does NOT demonstrate (be honest, don't pad).
- gaps: concrete, closeable gaps between the candidate and the role.
- tailoring_suggestions: specific ways to tailor THIS resume for THIS job (reframing real
  experience, surfacing buried evidence, quantifying) — never fabricate experience.

Be concrete, realistic, and honest. Avoid generic filler. Base everything strictly on the
actual resume and job description."""

async def analyze_fit(resume_text: str, page_count: int, job_description: str) -> tuple[FitAnalysis, dict]:
    """Assess resume-to-job fit. Returns (fit, meta)."""
    schema = json.dumps(FitAnalysis.model_json_schema(), indent=2)

    user_prompt = f"""Assess how well the resume fits the job below. Strictly return only a JSON
    object that matches the schema provided. Do not include any markdown or commentary.
    Schema:{schema}

    JOB DESCRIPTION:
    {job_description}

    RESUME ({page_count} page(s)):
    {resume_text}"""

    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            started = time.perf_counter()
            response = await client.chat.completions.create(
                model=MODEL,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": FIT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            llm_ms = (time.perf_counter() - started) * 1000
            raw = response.choices[0].message.content
            return FitAnalysis.model_validate_json(raw), _meta(response, llm_ms)

        except ValidationError as e:
            last_error = e
            logger.warning(
                "Fit output failed schema validation (attempt %d/%d): %s",
                attempt + 1, MAX_RETRIES + 1, e,
            )
            continue

        except Exception as e:
            logger.exception("OpenAI fit request failed")
            raise AnalysisError("The analysis service is unavailable.") from e

    raise AnalysisError(
        "The AI returned malformed data after retrying."
    ) from last_error


CHAT_SYSTEM_PROMPT = """You are North Star — an expert, honest career coach chatting with a
candidate about their resume. You have already analyzed their resume; both the full resume text
and your structured analysis are provided below as grounding context.

Answer their questions specifically and concretely, drawing on THIS resume and analysis — never
generic advice. Keep the same evidence-based honesty as the analysis: distinguish what the resume
claims from what it demonstrates, and don't repeat aspirational framing back as fact. Be warm,
direct, and concise (a few sentences to a short paragraph). Plain text only — no markdown headers
or JSON.

RESUME:
{resume_text}

ANALYSIS (JSON):
{analysis}"""


async def chat_reply(resume_text: str, analysis: dict, history: list[dict], message: str) -> tuple[str, dict]:
    """Answer a follow-up question, grounded in the resume + prior analysis.

    Reuses the module-level AsyncOpenAI client. Plain-text (conversational) — unlike
    analyze_resume, this does NOT request a JSON object. Returns (reply, meta).
    """
    system_prompt = CHAT_SYSTEM_PROMPT.format(
        resume_text=resume_text,
        analysis=json.dumps(analysis),
    )
    messages = (
        [{"role": "system", "content": system_prompt}]
        + history
        + [{"role": "user", "content": message}]
    )

    try:
        started = time.perf_counter()
        response = await client.chat.completions.create(model=MODEL, messages=messages)
        llm_ms = (time.perf_counter() - started) * 1000
        return response.choices[0].message.content, _meta(response, llm_ms)
    except Exception as e:
        logger.exception("OpenAI chat request failed")
        raise AnalysisError("The coach is unavailable right now.") from e
