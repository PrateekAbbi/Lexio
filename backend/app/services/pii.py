"""Local-only PII detection, role labeling, and redaction."""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Any

from app.exceptions import ConfigurationError


logger = logging.getLogger("legal-pipeline.pii")

DOC_TYPE_KEYWORDS = {
    "offer_letter": {
        "required": ["offer", "employment", "position", "salary"],
        "optional": ["base salary", "at-will", "background check", "benefits", "start date", "accept this offer"],
        "roles": ["OFFEROR", "CANDIDATE"],
    },
    "lease_agreement": {
        "required": ["landlord", "tenant", "rent", "lease", "premises"],
        "optional": ["monthly", "security deposit", "lessee", "lessor"],
        "roles": ["LANDLORD", "TENANT"],
    },
    "employment_contract": {
        "required": ["employer", "employee", "salary", "employment"],
        "optional": ["compensation", "benefits", "termination", "at-will"],
        "roles": ["EMPLOYER", "EMPLOYEE"],
    },
    "nda": {
        "required": ["confidential", "non-disclosure", "proprietary"],
        "optional": ["disclosing party", "receiving party", "trade secret"],
        "roles": ["DISCLOSING_PARTY", "RECEIVING_PARTY"],
    },
    "purchase_agreement": {
        "required": ["purchase price", "buyer", "seller", "property"],
        "optional": ["closing date", "escrow", "deed", "convey"],
        "roles": ["SELLER", "BUYER"],
    },
    "service_agreement": {
        "required": ["services", "contractor", "client", "deliverable"],
        "optional": ["scope of work", "invoice", "payment terms"],
        "roles": ["SERVICE_PROVIDER", "CLIENT"],
    },
    "loan_agreement": {
        "required": ["lender", "borrower", "principal", "interest rate"],
        "optional": ["repayment", "collateral", "default", "promissory"],
        "roles": ["LENDER", "BORROWER"],
    },
    "settlement_agreement": {
        "required": ["plaintiff", "defendant", "settlement", "claims"],
        "optional": ["release", "damages", "litigation", "court"],
        "roles": ["PLAINTIFF", "DEFENDANT"],
    },
    "partnership_agreement": {
        "required": ["partner", "partnership", "profit", "capital contribution"],
        "optional": ["general partner", "limited partner", "dissolution"],
        "roles": ["PARTNER_A", "PARTNER_B"],
    },
}

PRESIDIO_ENTITIES = [
    "PERSON",
    "PHONE_NUMBER",
    "EMAIL_ADDRESS",
    "LOCATION",
    "US_SSN",
    "US_ITIN",
    "US_BANK_NUMBER",
    "CREDIT_CARD",
    "US_PASSPORT",
    "DATE_TIME",
    "IP_ADDRESS",
    "US_DRIVER_LICENSE",
    "MEDICAL_LICENSE",
    "URL",
    "IBAN_CODE",
    "NRP",
    "US_DEA_NUMBER",
    "AU_ABN",
    "AU_ACN",
    "AU_TFN",
    "AU_MEDICARE",
    "SG_NRIC_FIN",
    "IN_PAN",
    "IN_AADHAAR",
]

ENTITY_DISPLAY_LABELS = {
    "PHONE_NUMBER": "PHONE",
    "EMAIL_ADDRESS": "EMAIL",
    "US_SSN": "SSN",
    "US_ITIN": "TAX_ID",
    "US_BANK_NUMBER": "BANK_ACCOUNT",
    "CREDIT_CARD": "CARD_NUMBER",
    "US_PASSPORT": "PASSPORT",
    "DATE_TIME": "DATE",
    "IP_ADDRESS": "IP_ADDRESS",
    "US_DRIVER_LICENSE": "DRIVER_LICENSE",
    "MEDICAL_LICENSE": "LICENSE",
    "URL": "URL",
    "IBAN_CODE": "IBAN",
    "NRP": "NATIONALITY",
    "LOCATION": "ADDRESS",
    "US_DEA_NUMBER": "DEA_NUMBER",
    "AU_ABN": "BUSINESS_ID",
    "AU_ACN": "BUSINESS_ID",
    "AU_TFN": "TAX_ID",
    "AU_MEDICARE": "ID_NUMBER",
    "IN_PAN": "TAX_ID",
    "IN_AADHAAR": "ID_NUMBER",
    "SG_NRIC_FIN": "ID_NUMBER",
    "ORGANIZATION": "COMPANY",
    "MONEY": "COMPENSATION",
}

LEGAL_PERSON_CONTEXT = ["party", "signed", "between", "herein", "referred"]
HONORIFIC_PATTERN = re.compile(r"^(mr|mrs|ms|miss|dr|prof|professor)\.?\s+", re.IGNORECASE)
WORD_PATTERN = re.compile(r"[a-z0-9]+", re.IGNORECASE)

ROLE_TERMS = {
    "LANDLORD": ["landlord", "lessor"],
    "TENANT": ["tenant", "lessee"],
    "EMPLOYER": ["employer"],
    "EMPLOYEE": ["employee"],
    "DISCLOSING_PARTY": ["disclosing party"],
    "RECEIVING_PARTY": ["receiving party"],
    "SELLER": ["seller"],
    "BUYER": ["buyer"],
    "SERVICE_PROVIDER": ["service provider", "contractor"],
    "CLIENT": ["client"],
    "LENDER": ["lender"],
    "BORROWER": ["borrower"],
    "PLAINTIFF": ["plaintiff"],
    "DEFENDANT": ["defendant"],
    "PARTNER_A": ["partner"],
    "PARTNER_B": ["partner"],
    "PARTY_A": ["party"],
    "PARTY_B": ["party"],
    "OFFEROR": ["offeror", "company", "employer", "from"],
    "CANDIDATE": ["candidate", "offeree", "employee", "you", "your"],
}

ORGANIZATION_PATTERN = re.compile(
    r"\b[A-Z][A-Za-z0-9&'.-]*(?:\s+[A-Z][A-Za-z0-9&'.-]*){0,6},?\s+"
    r"(?:Inc\.?|Incorporated|Corporation|Corp\.?|Company|Co\.?|LLC|L\.L\.C\.|Ltd\.?|Limited|PLC|LP|LLP)\b"
)
MONEY_PATTERNS = [
    re.compile(
        r"(?<!\w)(?:USD\s*)?\$\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?"
        r"(?:\s?(?:USD|dollars?|per\s+(?:year|annum|month|hour)|annually|yearly))?",
        re.IGNORECASE,
    ),
    re.compile(r"\b\d{2,3},\d{3}(?:\.\d{2})?\s?(?:USD|dollars?)\b", re.IGNORECASE),
]


class _LazyAnalyzer:
    def analyze(self, *args: Any, **kwargs: Any) -> list[Any]:
        return _get_analyzer().analyze(*args, **kwargs)


analyzer = _LazyAnalyzer()


def classify_document_type(full_text: str) -> tuple[str, list[str]]:
    """Classify a document locally by weighted keyword matches."""

    lowered = full_text.lower()
    best_doc_type = "general_contract"
    best_roles = ["PARTY_A", "PARTY_B"]
    best_score = 0

    for doc_type, config in DOC_TYPE_KEYWORDS.items():
        score = 0
        for keyword in config["required"]:
            if keyword in lowered:
                score += 3
        for keyword in config["optional"]:
            if keyword in lowered:
                score += 1
        if score > best_score:
            best_doc_type = doc_type
            best_roles = list(config["roles"])
            best_score = score

    if best_score <= 3:
        return "general_contract", ["PARTY_A", "PARTY_B"]
    return best_doc_type, best_roles


def assign_roles_to_persons(
    full_text: str,
    person_entities: list[dict],
    doc_type: str,
    roles: list[str],
) -> dict[str, str]:
    """Assign detected people to legal roles by local proximity matching."""

    candidates = _unique_person_candidates(person_entities)[:15]
    role_map: dict[str, str] = {}
    assigned_names: set[str] = set()
    role_occurrences = [(role, _first_role_occurrence(full_text, role)) for role in roles]
    role_occurrences.sort(key=lambda item: item[1] if item[1] >= 0 else len(full_text) + 1)

    for role, occurrence in role_occurrences:
        if occurrence < 0:
            continue
        window_start = max(0, occurrence - 150)
        window_end = min(len(full_text), occurrence + 150)
        window = full_text[window_start:window_end].lower()

        best_name: str | None = None
        best_distance: int | None = None
        for person in candidates:
            name = person["text"]
            if name in assigned_names:
                continue
            for variant in _person_variants(name):
                position = window.find(variant.lower())
                if position < 0:
                    continue
                distance = abs((window_start + position) - occurrence)
                if best_distance is None or distance < best_distance:
                    best_name = name
                    best_distance = distance

        if best_name is not None:
            role_map[best_name] = role
            assigned_names.add(best_name)

    if doc_type == "offer_letter" and "CANDIDATE" in roles:
        for person in candidates:
            name = person["text"]
            if name not in assigned_names:
                role_map[name] = "CANDIDATE"
                assigned_names.add(name)
                break

    third_party_index = 1
    for person in candidates:
        name = person["text"]
        if name in assigned_names:
            continue
        role_map[name] = f"THIRD_PARTY_{third_party_index}"
        third_party_index += 1

    return role_map


def scan_all_pii(text: str, threshold: float = 0.5) -> list[dict]:
    """Run Presidio over every configured entity plus a lower-threshold PERSON pass."""

    if not text:
        return []

    primary = analyzer.analyze(text=text, entities=PRESIDIO_ENTITIES, language="en", score_threshold=threshold)
    person_pass = analyzer.analyze(
        text=text,
        entities=["PERSON"],
        language="en",
        score_threshold=0.35,
        context=LEGAL_PERSON_CONTEXT,
    )

    by_span: dict[tuple[int, int], dict] = {}
    for result in [*primary, *person_pass]:
        entity = _entity_from_span(
            entity_type=result.entity_type,
            start=result.start,
            end=result.end,
            score=float(result.score),
            text=text,
        )
        key = (entity["start"], entity["end"])
        if key not in by_span or entity["score"] > by_span[key]["score"]:
            by_span[key] = entity

    for entity in _scan_sensitive_document_fields(text):
        key = (entity["start"], entity["end"])
        if key not in by_span or entity["score"] > by_span[key]["score"]:
            by_span[key] = entity

    return _remove_overlapping_entities(sorted(by_span.values(), key=lambda item: item["start"]))


def redact_text(text: str, entities: list[dict], role_map: dict[str, str]) -> tuple[str, int]:
    """Replace detected entities with role labels or generic entity placeholders."""

    redacted_text = text
    redaction_count = 0
    for entity in sorted(entities, key=lambda item: item["start"], reverse=True):
        entity_type = entity["entity_type"]
        if entity_type == "PERSON":
            label = _role_label_for_name(entity["text_snippet"], role_map, default_label="PERSON")
        elif entity_type == "ORGANIZATION":
            label = _role_label_for_name(entity["text_snippet"], role_map, default_label="COMPANY")
        else:
            label = ENTITY_DISPLAY_LABELS.get(entity_type, entity_type)
        replacement = f"[{label}]"
        redacted_text = redacted_text[: entity["start"]] + replacement + redacted_text[entity["end"] :]
        redaction_count += 1
    return redacted_text, redaction_count


def validate_no_pii_remains(redacted_text: str) -> tuple[str, int]:
    """Run a final lower-threshold pass and redact anything still detected."""

    second_pass_entities = scan_all_pii(redacted_text, threshold=0.35)
    if not second_pass_entities:
        return redacted_text, 0
    final_text, count = redact_text(redacted_text, second_pass_entities, {})
    logger.warning("Second-pass caught %s entities missed in first pass", count)
    return final_text, count


async def process_document(pages: list[dict]) -> dict:
    """Redact a document locally and return only redacted page text plus metadata."""

    normalized_pages = [_normalize_page(page) for page in pages]
    full_text = "\n\n".join(page["text"] for page in normalized_pages)
    doc_type, roles = classify_document_type(full_text)
    all_entities = scan_all_pii(full_text)
    person_entities = [entity for entity in all_entities if entity["entity_type"] == "PERSON"]
    organization_entities = [entity for entity in all_entities if entity["entity_type"] == "ORGANIZATION"]
    deduplicated_persons = deduplicate_persons(person_entities, full_text)
    role_map = assign_roles_to_persons(full_text, deduplicated_persons, doc_type, roles)
    role_map.update(assign_roles_to_organizations(full_text, organization_entities, doc_type, roles))

    redacted_pages: list[dict] = []
    total_redactions = 0
    second_pass_catches = 0
    for page in normalized_pages:
        entities_on_page = scan_all_pii(page["text"])
        redacted_text, count = redact_text(page["text"], entities_on_page, role_map)
        final_text, extra = validate_no_pii_remains(redacted_text)
        redacted_pages.append(
            {
                "page_number": page["page_number"],
                "text": final_text,
                "redaction_count": count + extra,
            }
        )
        total_redactions += count + extra
        second_pass_catches += extra

    return {
        "doc_type": doc_type,
        "roles_detected": sorted(set(role_map.values())),
        "role_map": role_map,
        "redacted_pages": redacted_pages,
        "total_redactions": total_redactions,
        "second_pass_catches": second_pass_catches,
    }


def deduplicate_persons(entities: list[dict], full_text: str) -> list[dict]:
    """Group person mentions that likely refer to the same person."""

    del full_text
    groups: list[list[dict]] = []
    for entity in sorted(entities, key=lambda item: (item["start"], -len(item["text_snippet"]))):
        candidate = {**entity, "text": _clean_person_name(entity["text_snippet"])}
        if not candidate["text"]:
            continue
        for group in groups:
            if any(_same_person(candidate["text"], existing["text"]) for existing in group):
                group.append(candidate)
                break
        else:
            groups.append([candidate])

    unique: list[dict] = []
    for group in groups:
        best = max(group, key=lambda item: (len(_name_words(item["text"])), len(item["text"])))
        unique.append({"text": best["text"], "start": best["start"], "end": best["end"]})
    unique.sort(key=lambda item: item["start"])
    return unique[:15]


def assign_roles_to_organizations(
    full_text: str,
    organization_entities: list[dict],
    doc_type: str,
    roles: list[str],
) -> dict[str, str]:
    """Assign organization names to document roles when they are sensitive."""

    del full_text
    organizations = _unique_organization_candidates(organization_entities)
    if not organizations:
        return {}

    role = "COMPANY"
    if doc_type == "offer_letter" and "OFFEROR" in roles:
        role = "OFFEROR"
    elif doc_type == "employment_contract" and "EMPLOYER" in roles:
        role = "EMPLOYER"

    return {organization["text"]: role for organization in organizations[:5]}


@lru_cache(maxsize=1)
def _get_analyzer() -> Any:
    try:
        from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
    except ImportError as exc:
        raise ConfigurationError(
            "presidio-analyzer is required for local PII redaction. Install backend/requirements.txt before ingesting."
        ) from exc

    try:
        engine = AnalyzerEngine()
    except Exception as exc:
        raise ConfigurationError(
            "Presidio AnalyzerEngine could not initialize. Install presidio-analyzer and its English NLP model "
            "before ingesting documents."
        ) from exc
    registry = engine.registry
    for recognizer in _custom_pattern_recognizers(Pattern, PatternRecognizer):
        registry.add_recognizer(recognizer)
    return engine


def _custom_pattern_recognizers(pattern_cls: Any, recognizer_cls: Any) -> list[Any]:
    specs = {
        "US_DEA_NUMBER": [r"\b[A-Z]{2}\d{7}\b"],
        "AU_ABN": [r"\b\d{2}\s?\d{3}\s?\d{3}\s?\d{3}\b"],
        "AU_ACN": [r"\b\d{3}\s?\d{3}\s?\d{3}\b"],
        "AU_TFN": [r"\b\d{3}\s?\d{3}\s?\d{3}\b"],
        "AU_MEDICARE": [r"\b\d{4}\s?\d{5}\s?\d\b"],
        "SG_NRIC_FIN": [r"\b[STFGM]\d{7}[A-Z]\b"],
        "IN_PAN": [r"\b[A-Z]{5}\d{4}[A-Z]\b"],
        "IN_AADHAAR": [r"\b\d{4}\s?\d{4}\s?\d{4}\b"],
        "US_ITIN": [r"\b9\d{2}[- ]?(?:7\d|8[0-8]|9[0-2]|9[4-9])[- ]?\d{4}\b"],
    }
    recognizers = []
    for entity, regexes in specs.items():
        patterns = [pattern_cls(f"{entity}_pattern_{index}", regex, 0.6) for index, regex in enumerate(regexes)]
        recognizers.append(recognizer_cls(supported_entity=entity, patterns=patterns))
    return recognizers


def _scan_sensitive_document_fields(text: str) -> list[dict]:
    entities: list[dict] = []
    for match in ORGANIZATION_PATTERN.finditer(text):
        entities.append(
            _entity_from_span(
                entity_type="ORGANIZATION",
                start=match.start(),
                end=match.end(),
                score=0.99,
                text=text,
            )
        )
    for pattern in MONEY_PATTERNS:
        for match in pattern.finditer(text):
            entities.append(
                _entity_from_span(
                    entity_type="MONEY",
                    start=match.start(),
                    end=match.end(),
                    score=0.99,
                    text=text,
                )
            )
    return entities


def _entity_from_span(entity_type: str, start: int, end: int, score: float, text: str) -> dict:
    return {
        "entity_type": entity_type,
        "start": start,
        "end": end,
        "score": score,
        "text_snippet": text[start:end],
    }


def _remove_overlapping_entities(entities: list[dict]) -> list[dict]:
    selected: list[dict] = []
    for entity in sorted(entities, key=lambda item: (item["start"], -(item["end"] - item["start"]))):
        overlap_index = next(
            (
                index
                for index, existing in enumerate(selected)
                if entity["start"] < existing["end"] and entity["end"] > existing["start"]
            ),
            None,
        )
        if overlap_index is None:
            selected.append(entity)
            continue
        existing = selected[overlap_index]
        entity_rank = (entity["score"], entity["end"] - entity["start"])
        existing_rank = (existing["score"], existing["end"] - existing["start"])
        if entity_rank > existing_rank:
            selected[overlap_index] = entity
    return sorted(selected, key=lambda item: item["start"])


def _unique_person_candidates(person_entities: list[dict]) -> list[dict]:
    seen: set[str] = set()
    candidates: list[dict] = []
    for entity in person_entities:
        name = _clean_person_name(entity.get("text") or entity.get("text_snippet", ""))
        key = _name_key(name)
        if not key or key in seen:
            continue
        seen.add(key)
        candidates.append({"text": name, "start": entity.get("start", 0), "end": entity.get("end", 0)})
    candidates.sort(key=lambda item: item["start"])
    return candidates


def _unique_organization_candidates(organization_entities: list[dict]) -> list[dict]:
    seen: set[str] = set()
    candidates: list[dict] = []
    for entity in organization_entities:
        name = _clean_organization_name(entity.get("text") or entity.get("text_snippet", ""))
        key = _organization_key(name)
        if not key or key in seen:
            continue
        seen.add(key)
        candidates.append({"text": name, "start": entity.get("start", 0), "end": entity.get("end", 0)})
    candidates.sort(key=lambda item: item["start"])
    return candidates


def _first_role_occurrence(full_text: str, role: str) -> int:
    lowered = full_text.lower()
    occurrences = [
        position
        for term in ROLE_TERMS.get(role, [role.lower().replace("_", " ")])
        if (position := lowered.find(term.lower())) >= 0
    ]
    return min(occurrences) if occurrences else -1


def _role_label_for_name(name: str, role_map: dict[str, str], default_label: str) -> str:
    clean_name = _clean_person_name(name)
    if clean_name in role_map:
        return role_map[clean_name]
    for full_name in sorted(role_map, key=len, reverse=True):
        if _names_partially_match(clean_name, full_name):
            return role_map[full_name]
    return default_label


def _person_variants(name: str) -> list[str]:
    variants = [name]
    words = _name_words(name)
    if words:
        variants.append(words[-1])
    if len(words) >= 2:
        variants.append(f"{words[0]} {words[-1]}")
    return list(dict.fromkeys(variants))


def _same_person(left: str, right: str) -> bool:
    left_clean = _clean_person_name(left)
    right_clean = _clean_person_name(right)
    if _names_partially_match(left_clean, right_clean):
        return True
    left_words = _name_words(left_clean)
    right_words = _name_words(right_clean)
    if left_words and right_words and left_words[-1].lower() == right_words[-1].lower():
        return True
    return False


def _names_partially_match(left: str, right: str) -> bool:
    left_key = _name_key(left)
    right_key = _name_key(right)
    if not left_key or not right_key:
        return False
    if left_key in right_key or right_key in left_key:
        return True
    left_words = set(_name_words(left))
    right_words = set(_name_words(right))
    return bool(left_words and right_words and (left_words <= right_words or right_words <= left_words))


def _clean_person_name(name: str) -> str:
    cleaned = HONORIFIC_PATTERN.sub("", " ".join(name.split()).strip(" ,.;:()[]{}"))
    return cleaned


def _clean_organization_name(name: str) -> str:
    return " ".join(name.split()).strip(" ,;:()[]{}")


def _organization_key(name: str) -> str:
    return " ".join(word.lower() for word in WORD_PATTERN.findall(_clean_organization_name(name)))


def _name_words(name: str) -> list[str]:
    return WORD_PATTERN.findall(_clean_person_name(name))


def _name_key(name: str) -> str:
    return " ".join(word.lower() for word in _name_words(name))


def _normalize_page(page: Any) -> dict:
    if isinstance(page, dict):
        return {"page_number": int(page["page_number"]), "text": str(page.get("text", ""))}
    return {"page_number": int(page.page_number), "text": str(page.text)}
