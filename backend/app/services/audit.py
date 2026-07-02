"""Local-only audit logging for PII security events."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path


AUDIT_LOG_PATH = Path(__file__).resolve().parents[2] / "pii_audit.log"
audit_logger = logging.getLogger("pii_audit")
if not audit_logger.handlers:
    handler = logging.FileHandler(AUDIT_LOG_PATH, delay=True)
    audit_logger.addHandler(handler)
audit_logger.setLevel(logging.INFO)
audit_logger.propagate = False


def log_ingest(
    doc_id: str,
    doc_type: str,
    total_redactions: int,
    second_pass_catches: int,
    roles_detected: list[str],
) -> None:
    audit_logger.info(
        f"{datetime.utcnow().isoformat()} | INGEST | doc={doc_id} "
        f"type={doc_type} redacted={total_redactions} "
        f"second_pass={second_pass_catches} roles={roles_detected}"
    )


def log_query_blocked(session_id: str, reason: str) -> None:
    audit_logger.info(f"{datetime.utcnow().isoformat()} | BLOCKED | session={session_id} reason={reason}")


def log_chunk_pii_detected_at_query_time(session_id: str, entity_types: list[str]) -> None:
    audit_logger.warning(f"{datetime.utcnow().isoformat()} | LEAK_CAUGHT | session={session_id} types={entity_types}")
