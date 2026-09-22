"""Common semantic extractor for public processing declarations.

This module is deliberately isolated from Privacy controls. It turns one public
text source into declared_processing/v1 facts and never decides a PRV result.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

MODEL_ID = "gpt-5.6-sol"
SCHEMA_VERSION = "declared_processing/v1"
PROMPT_VERSION = "declared-processing-v1-01"
REASONING_EFFORT = "medium"
MAX_INPUT_BYTES = 48_000
MAX_OUTPUT_TOKENS = 4_096
API_TIMEOUT_SECONDS = 120.0
API_MAX_RETRIES = 0

FACT_FIELDS = (
    "technology",
    "provider",
    "data_categories",
    "purposes",
    "recipients",
    "legal_basis",
    "retention",
    "international_transfers",
)
FACT_STATUSES = frozenset({"supported", "ambiguous"})
DOCUMENT_TYPES = ("privacy_policy", "cookie_policy", "other_public_document")


@dataclass(frozen=True)
class PublicDocument:
    url: str
    text: str
    document_type: str = "other_public_document"
    page_title: str | None = None


Client = Callable[[dict[str, Any]], Any]


def _fact_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "value": {"type": "string", "minLength": 1, "maxLength": 500},
            "normalized_value": {"type": ["string", "null"], "maxLength": 200},
            "status": {"type": "string", "enum": sorted(FACT_STATUSES)},
            "evidence": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "minLength": 1, "maxLength": 1000},
                    "source_url": {"type": "string", "minLength": 1},
                },
                "required": ["text", "source_url"],
                "additionalProperties": False,
            },
        },
        "required": ["value", "normalized_value", "status", "evidence"],
        "additionalProperties": False,
    }


def output_schema() -> dict[str, Any]:
    fact = _fact_schema()
    return {
        "type": "object",
        "properties": {
            "schema_version": {"type": "string", "const": SCHEMA_VERSION},
            "records": {
                "type": "array",
                "maxItems": 100,
                "items": {
                    "type": "object",
                    "properties": {
                        "record_id": {"type": "string", "minLength": 1, "maxLength": 80},
                        **{
                            field: {"type": "array", "maxItems": 30, "items": fact}
                            for field in FACT_FIELDS
                        },
                        "source": {
                            "type": "object",
                            "properties": {
                                "url": {"type": "string", "minLength": 1},
                                "document_type": {
                                    "type": "string",
                                    "enum": list(DOCUMENT_TYPES),
                                },
                                "page_title": {"type": ["string", "null"], "maxLength": 500},
                            },
                            "required": ["url", "document_type", "page_title"],
                            "additionalProperties": False,
                        },
                    },
                    "required": ["record_id", *FACT_FIELDS, "source"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["schema_version", "records"],
        "additionalProperties": False,
    }


def instructions() -> str:
    return (
        "Extrae únicamente hechos que el documento público recibido declara sobre "
        "tratamiento de datos. Devuelve exactamente el contrato declared_processing/v1. "
        "Cada record debe conservar juntos solo hechos que el texto permita relacionar "
        "entre sí; no mezcles tecnologías, proveedores, finalidades u otros hechos de "
        "unidades distintas. value debe ser una representación fiel de lo declarado. "
        "normalized_value es opcional y debe ser null si la normalización no está "
        "suficientemente respaldada. Usa supported solo cuando la cita respalde el "
        "hecho y ambiguous cuando exista evidencia relacionada pero la estructuración "
        "no sea inequívoca. No generes hechos not_found: usa listas vacías. evidence.text "
        "debe ser una cita literal y breve del texto recibido; source_url debe ser "
        "exactamente la URL recibida. No uses conocimiento externo. No concluyas "
        "cumplimiento, riesgo, score, necesidad de banner o consentimiento, validez "
        "jurídica, categorías necessary/tracking ni estados PRV."
    )


def request_kwargs(document: PublicDocument) -> dict[str, Any]:
    if document.document_type not in DOCUMENT_TYPES:
        raise ValueError("unsupported document_type")
    if not document.url.strip() or not document.text.strip():
        raise ValueError("url and text are required")
    payload = json.dumps(
        {
            "source": {
                "url": document.url,
                "document_type": document.document_type,
                "page_title": document.page_title,
            },
            "text": document.text,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    if len(payload.encode("utf-8")) > MAX_INPUT_BYTES:
        raise ValueError("semantic document exceeds hard input limit")
    return {
        "model": MODEL_ID,
        "reasoning": {"effort": REASONING_EFFORT},
        "instructions": instructions(),
        "input": payload,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "declared_processing_v1",
                "strict": True,
                "schema": output_schema(),
            }
        },
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "store": False,
    }


def _normalize(value: str) -> str:
    return " ".join(value.split())


def validate_output(raw: Any, document: PublicDocument) -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) != {"schema_version", "records"}:
        raise ValueError("output fields do not match declared_processing/v1")
    if raw["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unexpected schema_version")
    records = raw["records"]
    if not isinstance(records, list) or len(records) > 100:
        raise ValueError("records must be a bounded list")

    source_text = _normalize(document.text)
    seen_ids: set[str] = set()
    expected_record_fields = {"record_id", *FACT_FIELDS, "source"}

    for record in records:
        if not isinstance(record, dict) or set(record) != expected_record_fields:
            raise ValueError("record fields do not match declared_processing/v1")
        record_id = record["record_id"]
        if not isinstance(record_id, str) or not record_id.strip() or record_id in seen_ids:
            raise ValueError("record_id must be a unique non-empty string")
        seen_ids.add(record_id)

        source = record["source"]
        if not isinstance(source, dict) or set(source) != {"url", "document_type", "page_title"}:
            raise ValueError("source fields do not match declared_processing/v1")
        if source["url"] != document.url:
            raise ValueError("source URL does not match input")
        if source["document_type"] != document.document_type:
            raise ValueError("document_type does not match input")
        if source["page_title"] != document.page_title:
            raise ValueError("page_title does not match input")

        for field in FACT_FIELDS:
            facts = record[field]
            if not isinstance(facts, list) or len(facts) > 30:
                raise ValueError(f"{field} must be a bounded list")
            for fact in facts:
                if not isinstance(fact, dict) or set(fact) != {
                    "value", "normalized_value", "status", "evidence"
                }:
                    raise ValueError("fact fields do not match declared_processing/v1")
                if not isinstance(fact["value"], str) or not fact["value"].strip():
                    raise ValueError("fact value must be non-empty")
                normalized = fact["normalized_value"]
                if normalized is not None and not isinstance(normalized, str):
                    raise ValueError("normalized_value must be a string or null")
                if fact["status"] not in FACT_STATUSES:
                    raise ValueError("unsupported fact status")
                evidence = fact["evidence"]
                if not isinstance(evidence, dict) or set(evidence) != {"text", "source_url"}:
                    raise ValueError("evidence fields do not match declared_processing/v1")
                quote = evidence["text"]
                if evidence["source_url"] != document.url:
                    raise ValueError("evidence source URL does not match input")
                if not isinstance(quote, str) or not quote.strip():
                    raise ValueError("evidence text must be non-empty")
                if _normalize(quote) not in source_text:
                    raise ValueError("evidence text is not present in input document")

    return raw


def extract_declared_processing(
    document: PublicDocument,
    *,
    client: Client | None = None,
) -> dict[str, Any]:
    """Extract and validate declared_processing/v1 from one public document."""

    kwargs = request_kwargs(document)
    if client is None:
        from openai import OpenAI

        sdk = OpenAI(timeout=API_TIMEOUT_SECONDS, max_retries=API_MAX_RETRIES)
        response = sdk.responses.create(**kwargs)
        raw = json.loads(response.output_text)
    else:
        raw = client(kwargs)
    return validate_output(raw, document)
