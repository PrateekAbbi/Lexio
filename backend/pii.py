"""Compatibility exports for local PII handling."""

from app.services.pii import (
    DOC_TYPE_KEYWORDS,
    ENTITY_DISPLAY_LABELS,
    PRESIDIO_ENTITIES,
    analyzer,
    assign_roles_to_organizations,
    assign_roles_to_persons,
    classify_document_type,
    deduplicate_persons,
    process_document,
    redact_text,
    scan_all_pii,
    validate_no_pii_remains,
)

__all__ = [
    "DOC_TYPE_KEYWORDS",
    "ENTITY_DISPLAY_LABELS",
    "PRESIDIO_ENTITIES",
    "analyzer",
    "assign_roles_to_organizations",
    "assign_roles_to_persons",
    "classify_document_type",
    "deduplicate_persons",
    "process_document",
    "redact_text",
    "scan_all_pii",
    "validate_no_pii_remains",
]
