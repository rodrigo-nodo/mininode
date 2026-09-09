"""Shadow-only semantic observer for PRV-103.

This module mirrors the QA6-validated Intent LLM V2 architecture. Shadow output
never changes the public diagnostic, score, priorities, or correction plan.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from mininode_api.web_inspector.models import EvidenceContract, FormEvidence

from .evidence_adapter import _form_purpose_signal, _personal_form

logger = logging.getLogger(__name__)

MODEL_ID = "gpt-5.6-sol"
PROMPT_VERSION = "prv103-intent-v2-01"
REASONING_EFFORT = "medium"
EXPECTED_TAXONOMY_VERSION = "prv103-intents-v1"
ALLOWED_FIELDS = ("heading", "legend", "introductory_text", "submit_text")
MAX_SHADOW_FORMS = 10
_TAXONOMY_PATH = Path(__file__).with_name("prv103_intent_taxonomy.json")
_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="privacy-prv103-shadow")


@dataclass(frozen=True)
class ShadowIntent:
    intent_id: str
    final_class: str
    uncertain: bool
    evidence_fields: tuple[str, ...]


Classifier = Callable[[FormEvidence], ShadowIntent]


def load_taxonomy() -> dict[str, Any]:
    taxonomy = json.loads(_TAXONOMY_PATH.read_text(encoding="utf-8"))
    if taxonomy.get("taxonomy_version") != EXPECTED_TAXONOMY_VERSION:
        raise ValueError("unexpected PRV-103 shadow taxonomy version")
    return taxonomy


def _intent_class(taxonomy: dict[str, Any]) -> dict[str, str]:
    return {item["id"]: item["class"] for item in taxonomy["intents"]}


def _catalog_for_model(taxonomy: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"intent_id": item["id"], "examples": item["prototypes"]}
        for item in taxonomy["intents"]
    ]


def _output_schema(taxonomy: dict[str, Any]) -> dict[str, Any]:
    ids = [item["id"] for item in taxonomy["intents"]]
    return {
        "type": "object",
        "properties": {
            "intent_id": {"type": "string", "enum": ids},
            "evidence": {
                "type": "array",
                "maxItems": 4,
                "items": {
                    "type": "object",
                    "properties": {
                        "field": {"type": "string", "enum": list(ALLOWED_FIELDS)},
                        "quote": {"type": "string", "minLength": 1, "maxLength": 200},
                    },
                    "required": ["field", "quote"],
                    "additionalProperties": False,
                },
            },
            "reason_short": {"type": "string", "minLength": 1, "maxLength": 240},
            "uncertain": {"type": "boolean"},
        },
        "required": ["intent_id", "evidence", "reason_short", "uncertain"],
        "additionalProperties": False,
    }


def _instructions(taxonomy: dict[str, Any]) -> str:
    catalog = json.dumps(
        _catalog_for_model(taxonomy), ensure_ascii=False, separators=(",", ":")
    )
    return (
        "Clasifica únicamente la intención observable del formulario recibido. "
        "No decidas clases de producto ni cumplimiento. Usa solo heading, legend, "
        "introductory_text y submit_text; no uses conocimiento externo ni infieras "
        "desde campos que no están presentes. Elige exactamente un intent_id del "
        "catálogo. Contacto, registro o suscripción genéricos siguen siendo genéricos "
        "si no existe un resultado explícito. Acciones aisladas como Buscar, Next, "
        "Start now o equivalentes sin objeto reconocible son ambiguas. Un placeholder "
        "de plantilla sin significado humano es technical_placeholder. Si la evidencia "
        "no soporta claramente una intención o hay conflicto, uncertain=true. "
        "evidence debe citar literalmente substrings de los campos recibidos y solo "
        "los campos necesarios. reason_short debe ser una frase breve basada en la "
        "evidencia visible, sin razonamiento interno. Catálogo cerrado de intenciones: "
        + catalog
    )


def _payload(form: FormEvidence) -> dict[str, str | None]:
    return {field: getattr(form, field, None) for field in ALLOWED_FIELDS}


def _normalize(value: str) -> str:
    return " ".join(value.split())


def validate_intent_output(
    raw: Any,
    form: FormEvidence,
    taxonomy: dict[str, Any] | None = None,
) -> ShadowIntent:
    taxonomy = taxonomy or load_taxonomy()
    mapping = _intent_class(taxonomy)
    required = {"intent_id", "evidence", "reason_short", "uncertain"}
    if not isinstance(raw, dict) or set(raw) != required:
        raise ValueError("output fields do not match the frozen contract")

    intent_id = raw["intent_id"]
    if intent_id not in mapping:
        raise ValueError("intent_id is outside the frozen taxonomy")
    if not isinstance(raw["uncertain"], bool):
        raise ValueError("uncertain must be boolean")
    reason = raw["reason_short"]
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 240:
        raise ValueError("reason_short must be a non-empty short string")

    evidence = raw["evidence"]
    if not isinstance(evidence, list) or len(evidence) > 4:
        raise ValueError("evidence must contain at most four items")

    seen: set[str] = set()
    evidence_fields: list[str] = []
    for item in evidence:
        if not isinstance(item, dict) or set(item) != {"field", "quote"}:
            raise ValueError("evidence item fields do not match the frozen contract")
        field = item["field"]
        quote = item["quote"]
        if field not in ALLOWED_FIELDS or field in seen:
            raise ValueError("invalid or duplicated evidence field")
        source = getattr(form, field, None)
        if not isinstance(source, str) or not source.strip():
            raise ValueError("evidence references an empty field")
        if not isinstance(quote, str) or not quote.strip() or len(quote) > 200:
            raise ValueError("evidence quote must be a short non-empty string")
        if _normalize(quote) not in _normalize(source):
            raise ValueError("evidence quote is not present in the cited field")
        seen.add(field)
        evidence_fields.append(field)

    final_class = "unknown" if raw["uncertain"] else mapping[intent_id]
    evidence_fields.sort(key=ALLOWED_FIELDS.index)
    return ShadowIntent(
        intent_id=intent_id,
        final_class=final_class,
        uncertain=raw["uncertain"],
        evidence_fields=tuple(evidence_fields),
    )


def classify_form_intent(form: FormEvidence) -> ShadowIntent:
    from openai import OpenAI

    taxonomy = load_taxonomy()
    client = OpenAI(timeout=12.0, max_retries=0)
    response = client.responses.create(
        model=MODEL_ID,
        reasoning={"effort": REASONING_EFFORT},
        instructions=_instructions(taxonomy),
        input=json.dumps(_payload(form), ensure_ascii=False),
        text={
            "format": {
                "type": "json_schema",
                "name": "prv103_intent_shadow",
                "strict": True,
                "schema": _output_schema(taxonomy),
            }
        },
        store=False,
    )
    return validate_intent_output(json.loads(response.output_text), form, taxonomy)


def _deduped_high_personal_forms(contract: EvidenceContract) -> list[FormEvidence]:
    forms: list[FormEvidence] = []
    seen: set[tuple[str, ...]] = set()
    for form in contract.forms:
        is_personal, confidence = _personal_form(form)
        if not is_personal or confidence != "high":
            continue
        key = tuple(
            _normalize((getattr(form, field, None) or "")).casefold()
            for field in ALLOWED_FIELDS
        )
        if key in seen:
            continue
        seen.add(key)
        forms.append(form)
    return forms


def build_shadow_observation(
    contract: EvidenceContract,
    *,
    classifier: Classifier = classify_form_intent,
    max_forms: int = MAX_SHADOW_FORMS,
) -> dict[str, Any]:
    eligible = _deduped_high_personal_forms(contract)
    selected = eligible[: max(0, max_forms)]
    rows: list[dict[str, Any]] = []
    invalid_outputs = 0

    for index, form in enumerate(selected):
        baseline = _form_purpose_signal(form)
        try:
            shadow = classifier(form)
            rows.append(
                {
                    "form_index": index,
                    "baseline_class": baseline,
                    "shadow_class": shadow.final_class,
                    "intent_id": shadow.intent_id,
                    "uncertain": shadow.uncertain,
                    "evidence_fields": list(shadow.evidence_fields),
                    "valid": True,
                }
            )
        except Exception:
            invalid_outputs += 1
            rows.append(
                {
                    "form_index": index,
                    "baseline_class": baseline,
                    "shadow_class": "unknown",
                    "intent_id": "__error__",
                    "uncertain": True,
                    "evidence_fields": [],
                    "valid": False,
                }
            )

    valid_rows = [row for row in rows if row["valid"]]
    disagreements = [
        {
            "form_index": row["form_index"],
            "baseline_class": row["baseline_class"],
            "shadow_class": row["shadow_class"],
            "intent_id": row["intent_id"],
            "uncertain": row["uncertain"],
            "evidence_fields": row["evidence_fields"],
        }
        for row in valid_rows
        if row["baseline_class"] != row["shadow_class"]
    ]
    return {
        "event": "privacy_prv103_shadow_completed",
        "hostname": contract.target.domain,
        "model": MODEL_ID,
        "prompt_version": PROMPT_VERSION,
        "taxonomy_version": EXPECTED_TAXONOMY_VERSION,
        "forms_high_deduped": len(eligible),
        "forms_evaluated": len(selected),
        "forms_truncated": max(0, len(eligible) - len(selected)),
        "baseline_distribution": dict(Counter(row["baseline_class"] for row in rows)),
        "shadow_distribution": dict(Counter(row["shadow_class"] for row in valid_rows)),
        "class_agreement": sum(
            row["baseline_class"] == row["shadow_class"] for row in valid_rows
        ),
        "class_disagreements": len(disagreements),
        "invalid_outputs": invalid_outputs,
        "disagreements": disagreements,
    }


def _sampled(hostname: str | None, rate: float) -> bool:
    if rate <= 0:
        return False
    if rate >= 1:
        return True
    key = (hostname or "unknown").encode("utf-8")
    bucket = int.from_bytes(hashlib.sha256(key).digest()[:8], "big") / float(2**64)
    return bucket < rate


def _shadow_enabled() -> bool:
    return os.getenv("PRIVACY_PRV103_SHADOW_ENABLED", "").strip().casefold() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _shadow_sample_rate() -> float:
    raw = os.getenv("PRIVACY_PRV103_SHADOW_SAMPLE_RATE", "1").strip()
    try:
        return max(0.0, min(1.0, float(raw)))
    except ValueError:
        return 0.0


def _run_and_log(contract: EvidenceContract) -> None:
    try:
        event = build_shadow_observation(contract)
        logger.info(json.dumps(event, separators=(",", ":"), sort_keys=True))
    except Exception:
        logger.warning(
            json.dumps(
                {"event": "privacy_prv103_shadow_failed", "reason": "observer_error"},
                separators=(",", ":"),
                sort_keys=True,
            )
        )


def enqueue_prv103_shadow(contract: EvidenceContract) -> bool:
    """Queue shadow observation without delaying or changing the public result."""

    if not _shadow_enabled():
        return False
    if not os.getenv("OPENAI_API_KEY"):
        logger.warning(
            json.dumps(
                {"event": "privacy_prv103_shadow_skipped", "reason": "missing_openai_key"},
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return False
    if not _sampled(contract.target.domain, _shadow_sample_rate()):
        return False
    _EXECUTOR.submit(_run_and_log, contract)
    return True
