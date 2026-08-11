"""Orchestration for the in-memory Privacy Integration v0.1."""

from __future__ import annotations

from mininode_api.web_inspector.models import EvidenceContract

from .evaluator import evaluate_control
from .evidence_adapter import CONTROL_CODES, adapt_evidence
from .prioritization import prioritize_findings
from .scoring import score_privacy


def run_privacy_diagnostic(contract: EvidenceContract) -> dict:
    """Adapt and evaluate one Evidence Contract without performing any I/O."""
    evidence_by_control = adapt_evidence(contract)
    previous_results: dict[str, dict] = {}
    for code in CONTROL_CODES:
        previous_results[code] = evaluate_control(
            code, evidence_by_control[code], previous_results
        )

    controls = list(previous_results.values())
    score = score_privacy(controls)
    return {
        "controls": controls,
        **score,
        "priorities": prioritize_findings(controls),
        "scope": {
            "pages_requested": contract.inspection.pages_requested,
            "pages_analyzed": contract.inspection.pages_analyzed,
            "limited": contract.inspection.limited,
        },
    }
