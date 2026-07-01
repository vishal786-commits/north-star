import json

from openai import OpenAI

from app.config import settings
from app.schemas import Analysis

client = OpenAI(api_key=settings.openai_api_key)

MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """You are an expert career coach and resume analyst. You are supportive, motivating
and nurturing, but also honest and direct. You analyze resumes and return structured, honest, specific career guidance.
Be concrete and realistic — avoid generic filler. Base everything on the actual
resume content provided."""

def analyze_resume(resume_text:str) -> Analysis:
    schema = json.dumps(Analysis.model_json_schema(), indent=2)

    user_promt = f"""Analyze the resume below and strictly return only a JSON object that matches the
    schema provided. Do not include any markdown or commentary.
    Schema:{schema}
    Resume:{resume_text}"""

    response = client.chat.completions.create(
        model = MODEL,
        response_format={"type":"json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_promt}
        ],
        temperature=0.2
    )
    raw = response.choices[0].message.content

    return Analysis.model_validate_json(raw)




