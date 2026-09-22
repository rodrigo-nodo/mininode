from __future__ import annotations

import pytest

from mininode_api.domain_packs.privacy.declared_processing import (
    API_MAX_RETRIES,
    API_TIMEOUT_SECONDS,
    FACT_FIELDS,
    MODEL_ID,
    SCHEMA_VERSION,
    PublicDocument,
    extract_declared_processing,
    output_schema,
    request_kwargs,
    validate_output,
)


def _empty_record(document: PublicDocument) -> dict:
    return {
        "record_id": "dp_001",
        **{field: [] for field in FACT_FIELDS},
        "source": {
            "url": document.url,
            "document_type": document.document_type,
            "page_title": document.page_title,
        },
    }


def _fact(document: PublicDocument, value: str, quote: str, *, status: str = "supported") -> dict:
    return {
        "value": value,
        "normalized_value": None,
        "status": status,
        "evidence": {"text": quote, "source_url": document.url},
    }


def test_schema_is_frozen_and_has_only_the_eight_v1_fact_families():
    schema = output_schema()
    props = schema["properties"]["records"]["items"]["properties"]

    assert schema["properties"]["schema_version"]["const"] == SCHEMA_VERSION
    assert tuple(field for field in FACT_FIELDS) == (
        "technology",
        "provider",
        "data_categories",
        "purposes",
        "recipients",
        "legal_basis",
        "retention",
        "international_transfers",
    )
    assert set(props) == {"record_id", *FACT_FIELDS, "source"}


def test_request_is_isolated_from_prv_and_uses_strict_structured_output():
    document = PublicDocument(
        url="https://example.test/privacy",
        text="Usamos una herramienta para estadísticas.",
        document_type="privacy_policy",
        page_title="Privacidad",
    )

    kwargs = request_kwargs(document)

    assert kwargs["model"] == MODEL_ID
    assert kwargs["store"] is False
    assert kwargs["text"]["format"]["strict"] is True
    assert "PRV-202" not in kwargs["instructions"]
    assert "cumplimiento" in kwargs["instructions"]


def test_supported_fact_requires_literal_evidence_from_same_source():
    document = PublicDocument(
        url="https://example.test/cookies",
        text="Utilizamos Google Analytics para obtener estadísticas sobre el uso del sitio.",
        document_type="cookie_policy",
        page_title="Cookies",
    )
    record = _empty_record(document)
    record["technology"] = [
        _fact(document, "Google Analytics", "Utilizamos Google Analytics para obtener estadísticas")
    ]
    raw = {"schema_version": SCHEMA_VERSION, "records": [record]}

    assert validate_output(raw, document) == raw


def test_ambiguous_fact_is_valid_and_absence_is_an_empty_collection():
    document = PublicDocument(
        url="https://example.test/privacy",
        text="Podemos utilizar tecnologías de terceros.",
        document_type="privacy_policy",
    )
    record = _empty_record(document)
    record["technology"] = [
        _fact(
            document,
            "tecnologías de terceros",
            "Podemos utilizar tecnologías de terceros.",
            status="ambiguous",
        )
    ]

    validated = validate_output(
        {"schema_version": SCHEMA_VERSION, "records": [record]}, document
    )

    assert validated["records"][0]["provider"] == []
    assert validated["records"][0]["technology"][0]["status"] == "ambiguous"


def test_rejects_hallucinated_evidence():
    document = PublicDocument(
        url="https://example.test/privacy",
        text="Usamos cookies necesarias para el funcionamiento del sitio.",
    )
    record = _empty_record(document)
    record["technology"] = [
        _fact(document, "Google Analytics", "Usamos Google Analytics.")
    ]

    with pytest.raises(ValueError, match="not present"):
        validate_output({"schema_version": SCHEMA_VERSION, "records": [record]}, document)


def test_rejects_cross_source_evidence():
    document = PublicDocument(
        url="https://example.test/privacy",
        text="Usamos cookies necesarias.",
    )
    record = _empty_record(document)
    fact = _fact(document, "cookies necesarias", "Usamos cookies necesarias.")
    fact["evidence"]["source_url"] = "https://other.test/privacy"
    record["technology"] = [fact]

    with pytest.raises(ValueError, match="source URL"):
        validate_output({"schema_version": SCHEMA_VERSION, "records": [record]}, document)


def test_rejects_not_found_as_a_fact_status():
    document = PublicDocument(
        url="https://example.test/privacy",
        text="Usamos cookies.",
    )
    record = _empty_record(document)
    record["technology"] = [
        _fact(document, "cookies", "Usamos cookies.", status="not_found")
    ]

    with pytest.raises(ValueError, match="unsupported fact status"):
        validate_output({"schema_version": SCHEMA_VERSION, "records": [record]}, document)


def test_extractor_accepts_injected_client_without_network():
    document = PublicDocument(
        url="https://example.test/privacy",
        text="Usamos cookies necesarias para que el sitio funcione.",
        document_type="privacy_policy",
    )
    record = _empty_record(document)
    record["technology"] = [
        _fact(document, "cookies necesarias", "Usamos cookies necesarias")
    ]
    expected = {"schema_version": SCHEMA_VERSION, "records": [record]}

    def fake_client(kwargs):
        assert kwargs["model"] == MODEL_ID
        return expected

    assert extract_declared_processing(document, client=fake_client) == expected


def test_rejects_oversized_input_before_calling_model():
    document = PublicDocument(
        url="https://example.test/privacy",
        text="x" * 60_000,
    )

    with pytest.raises(ValueError, match="hard input limit"):
        extract_declared_processing(document, client=lambda _: pytest.fail("must not call"))


def test_api_timeout_allows_slow_reasoning_without_hidden_retry():
    assert API_TIMEOUT_SECONDS == 120.0
    assert API_MAX_RETRIES == 0
