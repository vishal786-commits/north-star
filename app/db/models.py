"""ORM models for the permanent datastore.

`LLMInteraction` is one row per successful LLM request. It is deliberately the
raw substrate for later work — prompt evals, regression testing, failure
analysis, token/cost analytics, model comparisons, and user-feedback analysis —
so it stores the full response payload and the prompt version alongside the
usual token/latency metadata.
"""
import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.engine import Base

# JSONB in Postgres (indexable, queryable); plain JSON on other dialects such as
# the SQLite used by the offline test suite.
JSON_VARIANT = sa.JSON().with_variant(JSONB, "postgresql")


class LLMInteraction(Base):
    __tablename__ = "llm_interactions"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True,
    )
    session_id: Mapped[str | None] = mapped_column(sa.Text, index=True)
    feature: Mapped[str] = mapped_column(sa.Text, nullable=False, index=True)  # resume_review | job_fit | chat
    resume_text: Mapped[str | None] = mapped_column(sa.Text)
    job_description: Mapped[str | None] = mapped_column(sa.Text)  # /fit only
    model: Mapped[str | None] = mapped_column(sa.Text, index=True)
    prompt_version: Mapped[str | None] = mapped_column(sa.Text, index=True)
    response_json: Mapped[dict | None] = mapped_column(JSON_VARIANT)
    input_tokens: Mapped[int | None] = mapped_column(sa.Integer)
    output_tokens: Mapped[int | None] = mapped_column(sa.Integer)
    latency_ms: Mapped[float | None] = mapped_column(sa.Float)
    user_rating: Mapped[str | None] = mapped_column(sa.Text)   # up | down
    user_comment: Mapped[str | None] = mapped_column(sa.Text)
    request_id: Mapped[str | None] = mapped_column(sa.Text, index=True)  # joins to logs + EMF
