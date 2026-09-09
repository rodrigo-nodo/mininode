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


def test_request_contract_has_hard_output_and_input_limits():
    taxonomy = load_taxonomy()
    kwargs = prv103_shadow._request_kwargs(form(), taxonomy)

    assert kwargs["max_output_tokens"] == prv103_shadow.MAX_OUTPUT_TOKENS == 256
    assert kwargs["store"] is False
    assert len(kwargs["input"].encode("utf-8")) <= prv103_shadow.MAX_FORM_INPUT_BYTES

    oversized = form(heading="x" * (prv103_shadow.MAX_FORM_INPUT_BYTES + 1))
    with pytest.raises(ValueError, match="hard input limit"):
        prv103_shadow._request_kwargs(oversized, taxonomy)


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
    assert event["forms_selected"] == 1
    assert event["forms_evaluated"] == 1
    assert event["llm_calls"] == 1
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
    assert event["llm_calls"] == 1
    assert "sensitive detail" not in encoded


def test_oversized_input_is_skipped_without_calling_llm():
    calls = []
    oversized = form(heading="x" * (prv103_shadow.MAX_FORM_INPUT_BYTES + 1))

    event = build_shadow_observation(
        contract([oversized]),
        classifier=lambda value: calls.append(value),
    )

    assert calls == []
    assert event["llm_calls"] == 0
    assert event["forms_evaluated"] == 0
    assert event["forms_skipped"] == 1
    assert event["skip_reasons"]["oversized_input"] == 1


def test_active_observer_stops_before_next_form_when_disabled():
    calls = []
    checks = iter([True, False])

    def classifier(target):
        calls.append(target.heading)
        return ShadowIntent("contact_generic", "generic", False, ("heading",))

    event = build_shadow_observation(
        contract([form(heading="Contacto A"), form(heading="Contacto B")]),
        classifier=classifier,
        should_continue=lambda: next(checks),
    )

    assert calls == ["Contacto A"]
    assert event["llm_calls"] == 1
    assert event["forms_skipped"] == 1
    assert event["skip_reasons"]["disabled_during_execution"] == 1


def test_call_budget_stops_remaining_forms_before_provider_call():
    calls = []
    budget = iter([True, False])

    def classifier(target):
        calls.append(target.heading)
        return ShadowIntent("contact_generic", "generic", False, ("heading",))

    event = build_shadow_observation(
        contract([form(heading="Contacto A"), form(heading="Contacto B")]),
        classifier=classifier,
        reserve_call=lambda: next(budget),
    )

    assert calls == ["Contacto A"]
    assert event["llm_calls"] == 1
    assert event["skip_reasons"]["call_budget_exhausted"] == 1


def test_process_call_budget_is_hard_capped_and_invalid_config_disables(monkeypatch):
    monkeypatch.setattr(prv103_shadow, "_CALLS_RESERVED", 0)
    monkeypatch.setenv(
        "PRIVACY_PRV103_SHADOW_MAX_CALLS_PER_PROCESS",
        str(prv103_shadow.HARD_MAX_CALLS_PER_PROCESS + 999),
    )
    assert prv103_shadow._max_calls_per_process() == prv103_shadow.HARD_MAX_CALLS_PER_PROCESS

    monkeypatch.setattr(
        prv103_shadow,
        "_CALLS_RESERVED",
        prv103_shadow.HARD_MAX_CALLS_PER_PROCESS - 1,
    )
    assert prv103_shadow._try_reserve_llm_call() is True
    assert prv103_shadow._try_reserve_llm_call() is False

    monkeypatch.setenv("PRIVACY_PRV103_SHADOW_MAX_CALLS_PER_PROCESS", "invalid")
    assert prv103_shadow._max_calls_per_process() == 0


def test_enqueue_is_disabled_by_default_and_requires_explicit_sample_rate(monkeypatch):
    monkeypatch.delenv("PRIVACY_PRV103_SHADOW_ENABLED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("PRIVACY_PRV103_SHADOW_SAMPLE_RATE", raising=False)
    assert enqueue_prv103_shadow(contract([form()])) is False

    monkeypatch.setenv("PRIVACY_PRV103_SHADOW_ENABLED", "true")
    assert enqueue_prv103_shadow(contract([form()])) is False

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    submitted = []
    monkeypatch.setattr(
        prv103_shadow._EXECUTOR,
        "submit",
        lambda *args: submitted.append(args),
    )
    assert enqueue_prv103_shadow(contract([form()])) is False
    assert submitted == []


def test_enqueue_rejects_when_bounded_queue_is_full(monkeypatch, caplog):
    class FullSlots:
        def acquire(self, *, blocking):
            assert blocking is False
            return False

        def release(self):
            raise AssertionError("full queue must not release an unreserved slot")

    monkeypatch.setenv("PRIVACY_PRV103_SHADOW_ENABLED", "true")
    monkeypatch.setenv("PRIVACY_PRV103_SHADOW_SAMPLE_RATE", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(prv103_shadow, "_JOB_SLOTS", FullSlots())

    with caplog.at_level("INFO", logger=prv103_shadow.__name__):
        assert enqueue_prv103_shadow(contract([form()])) is False

    event = json.loads(caplog.records[-1].message)
    assert event["reason"] == "queue_full"
    assert "Contacto" not in caplog.records[-1].message


def test_queued_work_rechecks_disable_and_releases_slot(monkeypatch, caplog):
    class Slots:
        released = 0

        def release(self):
            self.released += 1

    slots = Slots()
    executed = []
    monkeypatch.setattr(prv103_shadow, "_JOB_SLOTS", slots)
    monkeypatch.setattr(prv103_shadow, "_shadow_enabled", lambda: False)
    monkeypatch.setattr(prv103_shadow, "_run_and_log", lambda value: executed.append(value))

    with caplog.at_level("INFO", logger=prv103_shadow.__name__):
        prv103_shadow._run_reserved(contract([form()]))

    assert executed == []
    assert slots.released == 1
    event = json.loads(caplog.records[-1].message)
    assert event["reason"] == "disabled_before_execution"


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


def test_url_diagnostic_is_fail_open_when_shadow_enqueue_raises(monkeypatch):
    monkeypatch.setattr(
        service,
        "enqueue_prv103_shadow",
        lambda _value: (_ for _ in ()).throw(RuntimeError("shadow unavailable")),
    )
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

    assert isinstance(diagnostic["score"], int)
    assert "shadow" not in diagnostic
