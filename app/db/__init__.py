"""Permanent datastore package (Amazon RDS PostgreSQL).

The durable home for every successful LLM interaction. Redis (`app.session`)
stays the TEMPORARY store (sessions, chat history, rate-limit counters); this
package is the permanent one that survives container restarts.

Public surface: the declarative `Base`, connectivity helpers (`ping`,
`dispose`, `db_enabled`), and the best-effort CRUD helpers.
"""
from app.db.crud import record_interaction, update_feedback
from app.db.engine import Base, db_enabled, dispose, ping

__all__ = [
    "Base",
    "db_enabled",
    "dispose",
    "ping",
    "record_interaction",
    "update_feedback",
]
