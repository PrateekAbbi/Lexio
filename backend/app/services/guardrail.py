"""Local NLP guardrails for identity-seeking requests."""

from __future__ import annotations

from functools import lru_cache
from typing import NamedTuple

import spacy
from spacy.language import Language
from spacy.matcher import Matcher, PhraseMatcher
from spacy.tokens import Doc


ROLE_TERMS = (
    "landlord",
    "tenant",
    "resident",
    "co-resident",
    "property manager",
    "manager",
    "authorized agent",
    "agent",
    "offeror",
    "offeree",
    "candidate",
    "employer",
    "employee",
    "company",
    "buyer",
    "seller",
    "lender",
    "borrower",
    "plaintiff",
    "defendant",
    "contractor",
    "client",
)
SENSITIVE_ATTRIBUTES = (
    "name",
    "names",
    "identity",
    "email",
    "e-mail",
    "phone",
    "phone number",
    "telephone",
    "address",
    "ssn",
    "social security",
    "passport",
    "license",
    "license number",
    "account",
    "account number",
    "bank account",
    "tax id",
    "itin",
    "aadhaar",
    "pan",
)
REVEAL_PHRASES = (
    "what is",
    "what are",
    "who is",
    "who are",
    "tell me",
    "show me",
    "give me",
    "provide",
    "list",
    "reveal",
    "extract",
    "display",
    "let me know",
    "actual",
    "real",
    "specific",
    "unredact",
    "deanonymize",
    "de-anonymize",
    "recover",
)


class GuardrailNlp(NamedTuple):
    nlp: Language
    phrase_matcher: PhraseMatcher
    matcher: Matcher


def is_identity_seeking_query(question: str) -> bool:
    """Return True when the user asks to reveal hidden personal information.

    This guardrail is local-only: it uses spaCy tokenization and matchers, not
    OpenAI or any network service. Role-only party questions remain allowed,
    while requests for real names, contact details, IDs, or account data are
    blocked before embedding or answer generation.
    """

    if not question.strip():
        return False

    guardrail_nlp = _get_guardrail_nlp()
    doc = guardrail_nlp.nlp(question)
    phrase_labels = _phrase_labels(doc, guardrail_nlp.phrase_matcher)
    structural_labels = _structural_labels(doc, guardrail_nlp.matcher)

    if "SAFE_DOCUMENT_NAME" in structural_labels:
        return False
    if "PARTY_ROLE_REQUEST" in structural_labels and "PARTY_REAL_NAME_REQUEST" not in structural_labels:
        return False
    if "PARTY_REAL_NAME_REQUEST" in structural_labels:
        return True
    if "NAME_OF_ROLE" in structural_labels or "ROLE_POSSESSIVE_ATTRIBUTE" in structural_labels:
        return True
    if "WHO_IS_ROLE" in structural_labels:
        return True

    has_sensitive_attribute = "SENSITIVE_ATTRIBUTE" in phrase_labels
    has_role = "ROLE" in phrase_labels
    has_reveal_intent = "REVEAL_INTENT" in phrase_labels

    if has_sensitive_attribute and has_reveal_intent:
        return True
    return bool(has_sensitive_attribute and has_role)


@lru_cache(maxsize=1)
def _get_guardrail_nlp() -> GuardrailNlp:
    nlp = spacy.blank("en")
    phrase_matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    phrase_matcher.add("ROLE", [nlp.make_doc(term) for term in ROLE_TERMS])
    phrase_matcher.add("SENSITIVE_ATTRIBUTE", [nlp.make_doc(term) for term in SENSITIVE_ATTRIBUTES])
    phrase_matcher.add("REVEAL_INTENT", [nlp.make_doc(term) for term in REVEAL_PHRASES])

    matcher = Matcher(nlp.vocab)
    role_pattern = {"LOWER": {"IN": [term for term in ROLE_TERMS if " " not in term]}}
    party_pattern = {"LOWER": {"IN": ["party", "parties"]}}
    sensitive_pattern = {"LOWER": {"IN": [term for term in SENSITIVE_ATTRIBUTES if " " not in term]}}

    matcher.add(
        "PARTY_ROLE_REQUEST",
        [
            [
                {"LOWER": {"IN": ["name", "identify", "list"]}},
                {"LOWER": "the", "OP": "?"},
                party_pattern,
            ]
        ],
    )
    matcher.add(
        "PARTY_REAL_NAME_REQUEST",
        [
            [
                {"LOWER": "names"},
                {"LOWER": "of", "OP": "?"},
                {"LOWER": "the", "OP": "?"},
                party_pattern,
            ],
            [
                {"LOWER": "name"},
                {"LOWER": "of"},
                {"LOWER": "the", "OP": "?"},
                party_pattern,
            ],
            [
                party_pattern,
                {"LOWER": {"IN": ["name", "names"]}},
            ],
            [
                party_pattern,
                {"LOWER": "'s", "OP": "?"},
                {"LOWER": {"IN": ["name", "names"]}},
            ],
        ],
    )
    matcher.add(
        "NAME_OF_ROLE",
        [
            [
                {"LOWER": {"IN": ["name", "names"]}},
                {"LOWER": "of"},
                {"LOWER": "the", "OP": "?"},
                role_pattern,
            ],
            [
                {"LOWER": {"IN": ["name", "names"]}},
                {"LOWER": "of"},
                {"LOWER": "the", "OP": "?"},
                {"LOWER": {"IN": ["property", "authorized"]}},
                {"LOWER": {"IN": ["manager", "agent"]}},
            ],
        ],
    )
    matcher.add(
        "ROLE_POSSESSIVE_ATTRIBUTE",
        [
            [
                role_pattern,
                {"LOWER": "'s"},
                sensitive_pattern,
            ],
            [
                {"LOWER": {"IN": ["property", "authorized"]}},
                {"LOWER": {"IN": ["manager", "agent"]}},
                {"LOWER": "'s"},
                sensitive_pattern,
            ],
        ],
    )
    matcher.add(
        "WHO_IS_ROLE",
        [
            [
                {"LOWER": "who"},
                {"LOWER": {"IN": ["is", "are"]}},
                {"LOWER": "the", "OP": "?"},
                role_pattern,
            ],
            [
                {"LOWER": "who"},
                {"LOWER": {"IN": ["is", "are"]}},
                {"LOWER": "the", "OP": "?"},
                {"LOWER": {"IN": ["property", "authorized"]}},
                {"LOWER": {"IN": ["manager", "agent"]}},
            ],
        ],
    )
    matcher.add(
        "SAFE_DOCUMENT_NAME",
        [
            [
                {"LOWER": {"IN": ["what", "tell", "show"]}, "OP": "?"},
                {"LOWER": {"IN": ["is", "me"]}, "OP": "?"},
                {"LOWER": "the", "OP": "?"},
                {"LOWER": "name"},
                {"LOWER": "of"},
                {"LOWER": "this", "OP": "?"},
                {"LOWER": {"IN": ["document", "file", "contract", "agreement"]}},
            ]
        ],
    )
    return GuardrailNlp(nlp=nlp, phrase_matcher=phrase_matcher, matcher=matcher)


def _phrase_labels(doc: Doc, phrase_matcher: PhraseMatcher) -> set[str]:
    return {doc.vocab.strings[match_id] for match_id, _, _ in phrase_matcher(doc)}


def _structural_labels(doc: Doc, matcher: Matcher) -> set[str]:
    return {doc.vocab.strings[match_id] for match_id, _, _ in matcher(doc)}
