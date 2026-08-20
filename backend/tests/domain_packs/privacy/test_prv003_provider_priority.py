import sys
from pathlib import Path

BACKEND_SRC = Path(__file__).resolve().parents[3] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.domain_packs.privacy.evaluator import evaluate_control  # noqa: E402
from mininode_api.domain_packs.privacy.evidence_adapter import adapt_evidence  # noqa: E402
from mininode_api.web_inspector.models import (  # noqa: E402
    CookieEvidence,
    EvidenceContract,
    InspectionEvidence,
    LinkEvidence,
    PageEvidence,
    TargetEvidence,
    TransportEvidence,
)


def _contract(*, link: LinkEvidence, pages=None) -> EvidenceContract:
    return EvidenceContract(
        target=TargetEvidence("https://example.com/", "https://example.com/", "example.com"),
        inspection=InspectionEvidence(1, 1, False, []),
        pages=pages if pages is not None else [
            PageEvidence("https://example.com/", 200, "Example", "text/html")
        ],
        transport=TransportEvidence(True, True, None, False),
        links=[link],
        forms=[],
        cookies=CookieEvidence(False, [], False, False),
        contacts=[],
    )


def test_known_provider_anchor_cannot_override_third_party_classification():
    link = LinkEvidence(
        "https://hcaptcha.com/privacy",
        "Política de privacidad utilizada por Example",
        "https://example.com/",
    )

    adapted = adapt_evidence(_contract(link=link))

    assert adapted["PRV-003"]["policy_attribution"] == "third_party"
    assert evaluate_control("PRV-003", adapted["PRV-003"])["result"] == "not_detected"


def test_known_provider_can_be_own_only_with_inspected_document_attribution():
    url = "https://hcaptcha.com/privacy"
    link = LinkEvidence(url, "Política de privacidad", "https://example.com/")
    pages = [
        PageEvidence("https://example.com/", 200, "Example", "text/html"),
        PageEvidence(
            url,
            200,
            "Política de privacidad de Example",
            "text/html",
            document_text="Example es responsable de esta política de privacidad.",
        ),
    ]

    adapted = adapt_evidence(_contract(link=link, pages=pages))

    assert adapted["PRV-003"]["policy_attribution"] == "own"
    assert evaluate_control("PRV-003", adapted["PRV-003"])["result"] == "detected"
    assert adapted["PRV-003"]["attribution_signals"][0]["signal"] == (
        "provider_document_organization_mentioned"
    )
