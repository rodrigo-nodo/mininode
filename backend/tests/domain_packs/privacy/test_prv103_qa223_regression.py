from __future__ import annotations

import pytest

from mininode_api.domain_packs.privacy.evidence_adapter import _form_purpose_signal
from mininode_api.web_inspector.models import FieldEvidence, FormEvidence


def _form(*, heading=None, legend=None, introductory_text=None, submit_text=None):
    return FormEvidence(
        source_url="https://consumed-qa.invalid/form",
        action="https://consumed-qa.invalid/submit",
        method="post",
        fields=[FieldEvidence("email", "email", "Email", True)],
        checkboxes=[],
        nearby_text="",
        privacy_links=[],
        heading=heading,
        legend=legend,
        introductory_text=introductory_text,
        submit_text=submit_text,
    )


# These examples come from the already-consumed independent QA #223. They are
# regression fixtures only and must never be reported as a fresh QA metric.
@pytest.mark.parametrize(
    ("case_id", "kwargs", "expected"),
    [
        ("HF-S003-F01", {"introductory_text": "Get updates on Gorgias"}, "concrete"),
        ("HF-S006-F01", {"introductory_text": "Join our newsletter Get CX insights, AI trends & product news delivered weekly.", "submit_text": "Subscribe"}, "concrete"),
        ("HF-S006-F02", {"heading": "See Dixa in action", "submit_text": "Submit"}, "concrete"),
        ("HF-S008-F01", {"submit_text": "Sign up free"}, "generic"),
        ("HF-S008-F02", {"introductory_text": "Preview LiveChat® on your home page with one click", "submit_text": "Preview"}, "concrete"),
        ("HF-S009-F01", {"heading": "Write to us", "introductory_text": "Fill in the form and the right team will pick it up. Press, abuse reports, and partnership questions all land in the right inbox.", "submit_text": "Send message"}, "concrete"),
        ("HF-S015-F01", {"introductory_text": "Get a free demo", "submit_text": "Preview Bob (4:01)"}, "concrete"),
        ("HF-S015-F02", {"introductory_text": "Watch a demo", "submit_text": "SKIP TO VIDEO | START VIDEO"}, "concrete"),
        ("HF-S021-F03", {"heading": "Oh wait, did we mention that Freedcamp is absolutely free ?", "submit_text": "Start Now!"}, "concrete"),
        ("HF-S022-F01", {"submit_text": "Try Free for 7 Days"}, "concrete"),
        ("HF-S022-F04", {"introductory_text": "Join Over 250,000+ Smart Teams for Free", "submit_text": "Sign Up Now"}, "concrete"),
        ("HF-S025-F01", {"submit_text": "Submit your ticket"}, "concrete"),
        ("HF-S034-F02", {"heading": "Use the form to get in touch with the LogRocket team for a personalized demo.", "submit_text": "Get a demo"}, "concrete"),
        ("HF-S040-F01", {"submit_text": "Sign up"}, "generic"),
        ("HF-S045-F01", {"heading": "Reserva tu demo gratuita de Spendesk", "submit_text": "Enviar"}, "concrete"),
        ("HF-S051-F03", {"introductory_text": "Get actionable BFCM tips and strategies for your team", "submit_text": "Get the Guide"}, "concrete"),
        ("HF-S051-F04", {"introductory_text": "California Consumer Privacy Act Opt Out Form", "submit_text": "SUBMIT"}, "concrete"),
        ("HF-S055-F03", {"heading": "Grow your list for free with signup forms", "introductory_text": "Start for free | No hidden fees | Privacy protected", "submit_text": "CREATE FREE ACCOUNT"}, "generic"),
        ("HF-S061-F01", {"submit_text": "Create Account"}, "generic"),
        ("HF-S067-F01", {"heading": "Contact Duo to get started", "legend": "How will you use Duo?*", "introductory_text": "Let’s make some headlines. Get in touch with our team for any press-related requests.", "submit_text": "Submit"}, "concrete"),
        ("HF-S091-F01", {"heading": "Let's chat", "introductory_text": "Schedule a call to discuss your goals and how ButterCMS can help get there.", "submit_text": "Contact Us"}, "concrete"),
        ("HF-S096-F01", {"heading": "Get started with your free Essentials account", "submit_text": "Create Account"}, "generic"),
    ],
)
def test_prv103_qa223_consumed_classifier_regressions(case_id, kwargs, expected):
    assert _form_purpose_signal(_form(**kwargs)) == expected, case_id


def test_prv103_free_trial_remains_concrete_despite_signup_language():
    assert _form_purpose_signal(_form(
        heading="Sign up for a free trial",
        submit_text="Create account",
    )) == "concrete"
