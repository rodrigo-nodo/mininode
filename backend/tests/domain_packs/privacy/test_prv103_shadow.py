from __future__ import annotations

import json
from pathlib import Path

import pytest

from mininode_api.domain_packs.privacy import prv103_shadow
from mininode_api.domain_packs.privacy.prv103_shadow import (
    ShadowIntent,
    build_shadow_observation,
    enqueue_prv103_shadow,
    load_taxonomy,
    validate_intent_output,
)
from mininode_api.services import privacy_diagnostic as service
from mininode_api.web_inspector.models import (
    CookieEvidence,
    EvidenceContract,
    FetchPageResult,
    FieldEvidence,
    FormEvidence,
    InspectionEvidence,
    InspectionFetchResult,
    TargetEvidence,
    TransportEvidence,
)

HOME = "https://example.com/"


def form(
    *,
    heading="Contacto",
    legend=None,
    introductory_text=None,
    submit_text="Enviar mensaje",
    field_type="email",
):
    return FormEvidence(
        source_url=HOME,
        action=f"{HOME}send",
        method="post",
        fields=[FieldEvidence("email", field_type, "Email", True)],
        checkboxes=[],
        nearby_text="",
        privacy_links=[],
        heading=heading,
        legend=legend,
        introductory_text=introductory_text,
        submit_text=submit_text,
    )


def contract(forms):
    return EvidenceContract(
        target=TargetEvidence(HOME, HOME, "example.com"),
        inspection=InspectionEvidence(1, 1, False, []),
        pages=[],
        transport=TransportEvidence(True, True, None, False),
        links=[],
        forms=forms,
        cookies=CookieEvidence(False, [], False, False),
        contacts=[],
    )


def test_runtime_taxonomy_matches_qa6_frozen_taxonomy():
    qa6_path = (
        Path(__file__).parent
        / "prv103_semantic_benchmark"
        / "intent_taxonomy.json"
    )
    qa6 = json.loads(qa6_path.read_text(encoding="utf-8"))
    assert load_taxonomy() == qa6


def test_validate_output_uses_only_literal_allowed_evidence_and_uncertainty_abstains():
    target = form(heading="Reserva tu hora", submit_text="Agendar cita")
    raw = {
        "intent_id": "appointment_booking",
        "evidence": [{"field": "heading", "quote": "Reserva tu hora"}],
        "reason_short": "La finalidad visible es reservar una hora.",
        "uncertain": False,
    }

    result = validate_intent_output(raw, target)

    assert result.final_class == "concrete"
    assert result.evidence_fields == ("heading",)

    raw["uncertain"] = True
    assert validate_intent_output(raw, target).final_class == "unknown"

    raw["uncertain"] = False
    raw["evidence"] = [{"field": "heading", "quote": "Pagar cuenta"}]
    with pytest.raises(ValueError, match="not present"):
        validate_intent_output(raw, target)


def test_shadow_observation_evaluates_only_high_personal_forms_and_logs_no_form_text():
    personal = form()
    technical = FormEvidence(
        source_url=HOME,
        action=f"{HOME}technical",
        method="post",
        fields=[FieldEvidence("csrf", "hidden", "", False)],
        checkboxes=[],
        nearby_text="private nearby text",
        privacy_links=[],
        heading="Texto que no debe ir al log",
        submit_text="Enviar",
    )

    def classifier(_form):
        return ShadowIntent("contact_generic", "generic", False, ("heading",))

    event = build_shadow_observation(
        contract([personal, technical]),
        classifier=classifier,
    )
    encoded = json.dumps(event, ensure_ascii=False)

    assert event["forms_high_deduped"] == 1
    assert event["forms_evaluated"] == 1
    assert event["invalid_outputs"] == 0
    assert event["hostname"] == "example.com"
    assert "Contacto" not in encoded
    assert "Enviar mensaje" not in encoded
    assert "Texto que no debe ir al log" not in encoded
    assert "private nearby text" not in encoded


def test_shadow_observation_is_fail_open_per_form():
    def broken_classifier(_form):
        raise RuntimeError("provider failed with sensitive detail")

    event = build_shadow_observation(
        contract([form()]),
        classifier=broken_classifier,
    )
    encoded = json.dumps(event)

    assert event["invalid_outputs"] == 1
    assert event["forms_evaluated"] == 1
    assert "sensitive detail" not in encoded


def test_enqueue_is_disabled_by_default_and_requires_key(monkeypatch):
    monkeypatch.delenv("PRIVACY_PRV103_SHADOW_ENABLED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert enqueue_prv103_shadow(contract([form()])) is False

    monkeypatch.setenv("PRIVACY_PRV103_SHADOW_ENABLED", "true")
    assert enqueue_prv103_shadow(contract([form()])) is False


def test_sampling_is_deterministic_and_bounded():
    assert prv103_shadow._sampled("example.com", 0.0) is False
    assert prv103_shadow._sampled("example.com", 1.0) is True
    assert prv103_shadow._sampled("example.com", 0.37) == prv103_shadow._sampled(
        "example.com", 0.37
    )


class FakeFetcher:
    def __init__(self, html):
        self.html = html

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def fetch(self, target_url, candidate_urls, *, deadline=None):
        requested = list(candidate_urls)
        pages = [
            FetchPageResult(
                requested_url=url,
                final_url=url,
                status_code=200,
                content_type="text/html",
                html=self.html,
                tls_valid=True,
            )
            for url in requested
        ]
        return InspectionFetchResult(
            target_url=target_url,
            pages_requested=len(requested),
            pages_fetched=len(pages),
            pages=pages,
        )


def test_url_diagnostic_queues_shadow_once_with_final_contract_without_public_shadow_field(
    monkeypatch,
):
    captured = []
    monkeypatch.setattr(service, "enqueue_prv103_shadow", lambda value: captured.append(value) or True)
    html = """
    <html><body>
      <form action="/send" method="post">
        <h2>Contacto</h2>
        <label>Email <input type="email" name="email"></label>
        <button type="submit">Enviar mensaje</button>
      </form>
    </body></html>
    """

    diagnostic = service.diagnose_privacy_url(
        HOME,
        fetcher_factory=lambda **_: FakeFetcher(html),
    )

    assert len(captured) == 1
    assert captured[0].inspection.pages_analyzed == diagnostic["scope"]["pages_analyzed"]
    assert "prv103_shadow" not in diagnostic
    assert "shadow" not in diagnostic
