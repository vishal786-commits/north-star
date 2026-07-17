import json
import logging
import time

from openai import AsyncOpenAI
from pydantic import ValidationError

from app import knowledge
from app.config import settings
from app.errors import AnalysisError
from app.schemas import Analysis, FitAnalysis

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


_BASE_PHILOSOPHY = """You are an expert, honest career coach and resume analyst.

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
items, not one sentence) and effort_level of exactly "low", "medium", or "high"."""


def _build_system_prompt(market: str) -> str:
    """Compose the resume-review system prompt for a specific target market.

    The base philosophy is market-agnostic; the knowledge fragments and the
    market guide situate the advice so it is specific to THIS market's norms
    rather than generic. `market` is validated at the route layer, but we fall
    back to the default guide defensively."""
    guide = knowledge.MARKET_GUIDES.get(market, knowledge.MARKET_GUIDES[knowledge.DEFAULT_MARKET])
    label = knowledge.MARKET_LABELS.get(market, knowledge.MARKET_LABELS[knowledge.DEFAULT_MARKET])
    return f"""{_BASE_PHILOSOPHY}

You are optimising this resume for {label}. Echo this exact market code back in the
`market` field: "{market}". Apply the market rules below — they OVERRIDE the generic
baselines where they conflict (e.g. length, what to cut, spelling, CV vs resume).

{guide}

{knowledge.RESUME_PRINCIPLES}

{knowledge.PARSEABILITY_RULES}

{knowledge.CUT_LIST}

{knowledge.XYZ_RULE}

{knowledge.DEFENSIBILITY_RULE}

Populate `parseability`, `bullet_rewrites`, `defensibility_flags`, and `cut_list`
accordingly. For `cut_list`, tune to the market: be aggressive for modern/UK/US
markets, but for traditional Indian employers keep it minimal (their conventions,
like a declaration or photo, may be expected — do not reflexively flag them).

Be concrete, realistic, and honest. Avoid generic filler. Base everything strictly
on the actual resume content."""


async def analyze_resume(resume_text: str, page_count: int, market: str = knowledge.DEFAULT_MARKET) -> tuple[Analysis, dict]:
    """Analyze a resume. Returns (analysis, meta) where meta carries token
    usage + latency for the monitoring layer."""
    schema = json.dumps(Analysis.model_json_schema(), indent=2)
    system_prompt = _build_system_prompt(market)

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
                    {"role": "system", "content": system_prompt},
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


_FIT_PHILOSOPHY = """You are an expert, honest career coach assessing how well a candidate's
resume fits a SPECIFIC job. You are given the full resume text and a job description.

CRITICAL — assess EVIDENCE, not keyword surface or self-description. A resume is a marketing
document; a job description is a wish list. Compare what the resume actually DEMONSTRATES
(shipped work, measurable outcomes, real scope, tenure) against what the job GENUINELY requires.

- match_score reflects real, demonstrated fit for THIS role — not how many keywords overlap.
- matched_requirements: job needs the resume genuinely supports with evidence.
- missing_requirements: job needs the resume does NOT demonstrate (be honest, don't pad).
- gaps: concrete, closeable gaps between the candidate and the role.
- tailoring_suggestions: specific ways to tailor THIS resume for THIS job (reframing real
  experience, surfacing buried evidence, quantifying) — never fabricate experience."""


def _build_fit_system_prompt(market: str) -> str:
    """Compose the job-fit system prompt for a specific target market."""
    guide = knowledge.MARKET_GUIDES.get(market, knowledge.MARKET_GUIDES[knowledge.DEFAULT_MARKET])
    label = knowledge.MARKET_LABELS.get(market, knowledge.MARKET_LABELS[knowledge.DEFAULT_MARKET])
    return f"""{_FIT_PHILOSOPHY}

You are assessing this for {label}. Echo this exact market code back in the `market`
field: "{market}". Mirror the job description's exact language where the resume genuinely
supports it (spelled-out term + acronym once) — never keyword-stuff.

{guide}

{knowledge.XYZ_RULE}
For fit, target the rewrites at bullets most relevant to THIS job — reframe real experience
toward the role's language and surface buried, relevant evidence. Never fabricate.

Be concrete, realistic, and honest. Avoid generic filler. Base everything strictly on the
actual resume and job description."""


async def analyze_fit(resume_text: str, page_count: int, job_description: str, market: str = knowledge.DEFAULT_MARKET) -> tuple[FitAnalysis, dict]:
    """Assess resume-to-job fit. Returns (fit, meta)."""
    schema = json.dumps(FitAnalysis.model_json_schema(), indent=2)
    system_prompt = _build_fit_system_prompt(market)

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
                    {"role": "system", "content": system_prompt},
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

You are advising for {market_label}. Keep advice specific to that market's norms (length,
CV vs resume, spelling, what belongs on the document and what to cut).

Answer their questions specifically and concretely, drawing on THIS resume and analysis — never
generic advice. Keep the same evidence-based honesty as the analysis: distinguish what the resume
claims from what it demonstrates, and don't repeat aspirational framing back as fact. Be warm,
direct, and concise (a few sentences to a short paragraph). Plain text only — no markdown headers
or JSON.

RESUME:
{resume_text}

ANALYSIS (JSON):
{analysis}"""


async def chat_reply(resume_text: str, analysis: dict, history: list[dict], message: str,
                     market: str = knowledge.DEFAULT_MARKET) -> tuple[str, dict]:
    """Answer a follow-up question, grounded in the resume + prior analysis.

    Reuses the module-level AsyncOpenAI client. Plain-text (conversational) — unlike
    analyze_resume, this does NOT request a JSON object. Returns (reply, meta).
    """
    market_label = knowledge.MARKET_LABELS.get(market, knowledge.MARKET_LABELS[knowledge.DEFAULT_MARKET])
    system_prompt = CHAT_SYSTEM_PROMPT.format(
        resume_text=resume_text,
        analysis=json.dumps(analysis),
        market_label=market_label,
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
