"""create llm_interactions

Revision ID: 0001
Revises:
Create Date: 2026-07-18

Initial schema for the permanent datastore: one row per successful LLM
interaction. Built to later support prompt evals, regression testing, failure
analysis, token/cost analytics, model comparisons, and user-feedback analysis.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "llm_interactions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("session_id", sa.Text(), nullable=True),
        sa.Column("feature", sa.Text(), nullable=False),
        sa.Column("resume_text", sa.Text(), nullable=True),
        sa.Column("job_description", sa.Text(), nullable=True),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column("prompt_version", sa.Text(), nullable=True),
        sa.Column("response_json", postgresql.JSONB(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("user_rating", sa.Text(), nullable=True),
        sa.Column("user_comment", sa.Text(), nullable=True),
        sa.Column("request_id", sa.Text(), nullable=True),
    )
    op.create_index("ix_llm_interactions_created_at", "llm_interactions", ["created_at"])
    op.create_index("ix_llm_interactions_session_id", "llm_interactions", ["session_id"])
    op.create_index("ix_llm_interactions_feature", "llm_interactions", ["feature"])
    op.create_index("ix_llm_interactions_model", "llm_interactions", ["model"])
    op.create_index("ix_llm_interactions_prompt_version", "llm_interactions", ["prompt_version"])
    op.create_index("ix_llm_interactions_request_id", "llm_interactions", ["request_id"])


def downgrade() -> None:
    op.drop_table("llm_interactions")
