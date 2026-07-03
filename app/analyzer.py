import json
import logging

from openai import AsyncOpenAI, OpenAI
from pydantic import ValidationError
# from pymupdf.extra import page_count

from app.config import settings
from app.schemas import Analysis
from app.errors import AnalysisError

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=45)

MODEL = "gpt-4o-mini"
MAX_RETRIES = 1

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

async def analyze_resume(resume_text:str, page_count:int) -> Analysis:
    schema = json.dumps(Analysis.model_json_schema(), indent=2)

    user_prompt = f"""Analyze the resume below and strictly return only a JSON object that matches the
    schema provided. Do not include any markdown or commentary.
    Schema:{schema}
    The resume has {page_count} page(s) — use this for your length assessment.
    
    Resume:{resume_text}"""

    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = await client.chat.completions.create(
                model=MODEL,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            raw = response.choices[0].message.content
            return Analysis.model_validate_json(raw)

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




