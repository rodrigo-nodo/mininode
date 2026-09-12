from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


# 1. PRV-103 deterministic classifier: broaden specific observable purpose families
#    and stop treating account creation / plain signup as a concrete purpose.
path = "backend/src/mininode_api/domain_packs/privacy/evidence_adapter.py"
text = read(path)

anchor = '_FORM_PURPOSE_CONCRETE_PATTERNS = tuple(re.compile(pattern) for pattern in (\n'
strong = '''_FORM_PURPOSE_STRONG_CONCRETE_PATTERNS = tuple(re.compile(pattern) for pattern in (\n    r"\\bget\\b.{0,30}\\bupdates?\\b",\n    r"\\bjoin\\b.{0,40}\\bnewsletter\\b",\n    r"\\bsee\\b.{0,50}\\bin action\\b",\n    r"\\b(?:get|watch|request|book|schedule)\\b.{0,30}\\b(?:a |an |the |your )?(?:free )?demo\\b",\n    r"\\bpersonalized demo\\b",\n    r"\\b(?:reserva|reservar|solicita|solicitar|agenda|agendar)\\b.{0,30}\\b(?:tu |una |un )?demo\\b",\n    r"\\bpreview\\b.{0,80}\\b(?:home page|website|site)\\b",\n    r"\\bsubmit\\b.{0,20}\\b(?:your |a |the )?ticket\\b",\n    r"\\btry free for \\d+\\s+(?:day|days|week|weeks|month|months)\\b",\n    r"\\babsolutely free\\b",\n    r"\\bjoin\\b.{0,80}\\bfor free\\b",\n    r"\\b(?:get|download|access|view|receive)\\b.{0,30}\\b(?:guide|report|ebook|e book|whitepaper|white paper|checklist|webinar|resource)\\b",\n    r"\\b(?:press|media|abuse|partnership)\\b.{0,140}\\b(?:requests?|questions?|inquiries|inbox)\\b",\n    r"\\b(?:ccpa|california consumer privacy act|privacy)\\b.{0,100}\\b(?:opt out|delete|deletion|access|request)\\b",\n    r"\\bopt out form\\b",\n    r"\\b(?:schedule|book)\\b.{0,25}\\b(?:a |the )?(?:call|meeting)\\b",\n))\n_FORM_PURPOSE_ACCOUNT_SIGNAL = re.compile(\n    r"\\b(?:create|open)\\s+(?:a\\s+)?(?:free\\s+)?account\\b|"\n    r"\\b(?:crear|abre|abrir)\\s+(?:una\\s+)?cuenta\\b|"\n    r"\\bsign up(?:\\s+free|\\s+now)?\\b|"\n    r"\\b(?:register|registrarse|registrate)\\b|"\n    r"\\bget started\\b.{0,40}\\baccount\\b"\n)\n\n\n_FORM_PURPOSE_CONCRETE_PATTERNS = tuple(re.compile(pattern) for pattern in (\n'''
text = replace_once(text, anchor, strong, label="insert strong PRV-103 families")
text = replace_once(
    text,
    '    r"\\b(?:crear|create)\\b.{0,15}\\b(?:cuenta|account)\\b",\n',
    '',
    label="remove account creation from concrete",
)
text = replace_once(
    text,
    '    r"\\b(?:registrarse|register|postular|apply)\\b",\n',
    '    r"\\b(?:postular|apply)\\b",\n',
    label="keep applications concrete but not registration",
)
old_logic = '''    combined = " ".join(values)\n    if any(pattern.search(combined) for pattern in _FORM_PURPOSE_CONCRETE_PATTERNS):\n        return "concrete"\n    if (\n        _FORM_PURPOSE_SUPPORT_SIGNAL.search(combined)\n        and _FORM_PURPOSE_QUESTION_ACTION.search(combined)\n    ):\n        return "concrete"\n    if (\n        _FORM_PURPOSE_FREE_TRIAL.search(combined)\n        and _FORM_PURPOSE_TRIAL_ACTION.search(combined)\n    ):\n        return "concrete"\n'''
new_logic = '''    combined = " ".join(values)\n    # High-precision families observed in the consumed QA holdout take precedence\n    # over generic contact/account language when the same form states a specific\n    # result or action.\n    if any(pattern.search(combined) for pattern in _FORM_PURPOSE_STRONG_CONCRETE_PATTERNS):\n        return "concrete"\n    if (\n        _FORM_PURPOSE_SUPPORT_SIGNAL.search(combined)\n        and _FORM_PURPOSE_QUESTION_ACTION.search(combined)\n    ):\n        return "concrete"\n    if (\n        _FORM_PURPOSE_FREE_TRIAL.search(combined)\n        and _FORM_PURPOSE_TRIAL_ACTION.search(combined)\n    ):\n        return "concrete"\n    # Creating an account or signing up describes the mechanics of entry, not by\n    # itself the purpose for which the personal data is requested. A stronger\n    # observable purpose above (for example a free trial) may still be concrete.\n    if _FORM_PURPOSE_ACCOUNT_SIGNAL.search(combined):\n        return "generic"\n    if any(pattern.search(combined) for pattern in _FORM_PURPOSE_CONCRETE_PATTERNS):\n        return "concrete"\n'''
text = replace_once(text, old_logic, new_logic, label="reorder PRV-103 classifier")
write(path, text)


# 2. Conservative capture hygiene: exact transient UI labels are not form context.
path = "backend/src/mininode_api/web_inspector/extractor.py"
text = read(path)
old = '''def _bounded_text(tag: Tag, limit: int) -> str | None:\n    value = _text(tag)\n    return value[:limit] if value else None\n'''
new = '''def _bounded_text(tag: Tag, limit: int) -> str | None:\n    value = _text(tag)\n    operational = " ".join(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())\n    if operational in {"close", "loading", "cargando"}:\n        return None\n    return value[:limit] if value else None\n'''
text = replace_once(text, old, new, label="filter transient form context")
write(path, text)


# 3. Framework version changes because observable PRV-103 behavior changes.
path = "backend/src/mininode_api/domain_packs/privacy/controls.json"
text = read(path)
text = replace_once(text, '  "version": "0.8",', '  "version": "0.9",', label="framework 0.9")
write(path, text)

path = "backend/tests/domain_packs/privacy/test_versioning.py"
text = read(path).replace('"0.8"', '"0.9"')
write(path, text)

path = "backend/tests/domain_packs/privacy/test_privacy_diagnostic.py"
text = read(path)
text = replace_once(
    text,
    '    assert result["framework_version"] == "0.8"',
    '    assert result["framework_version"] == "0.9"',
    label="diagnostic framework expectation",
)
write(path, text)


# 4. Stable product documentation, not PR history.
path = "docs/privacy.md"
text = read(path)
old = '''La versión vigente del framework es `0.8`; el scoring permanece en `0.1`.\nFramework `0.8` amplía de forma acotada la captura estática de contexto asociado a formularios y el descubrimiento de páginas de acción para PRV-103; mantiene el clasificador determinístico, sin LLM, y no ejecuta JavaScript del sitio.\n'''
new = '''La versión vigente del framework es `0.9`; el scoring permanece en `0.1`.\nFramework `0.9` mantiene la captura estática introducida en `0.8` y ajusta el clasificador determinístico de PRV-103: reconoce familias observables adicionales de finalidad concreta (por ejemplo demo, soporte/ticket, recursos, privacidad/opt-out, prensa, actualizaciones y llamadas agendadas) y trata la creación de cuenta o el alta genérica como contexto genérico salvo que el mismo formulario exprese una finalidad específica. Mantiene LLM/shadow apagado y no ejecuta JavaScript del sitio.\nPRV-103 `0.9` debe superar un nuevo holdout independiente antes de considerarse validado y antes de cerrar Formularios V1.\n'''
text = replace_once(text, old, new, label="privacy docs framework 0.9")
write(path, text)


# 5. Consumed QA #223 becomes regression-only coverage. This is not a new QA.
regression = '''from __future__ import annotations\n\nimport pytest\n\nfrom mininode_api.domain_packs.privacy.evidence_adapter import _form_purpose_signal\nfrom mininode_api.web_inspector.models import FieldEvidence, FormEvidence\n\n\ndef _form(*, heading=None, legend=None, introductory_text=None, submit_text=None):\n    return FormEvidence(\n        source_url="https://consumed-qa.invalid/form",\n        action="https://consumed-qa.invalid/submit",\n        method="post",\n        fields=[FieldEvidence("email", "email", "Email", True)],\n        checkboxes=[],\n        nearby_text="",\n        privacy_links=[],\n        heading=heading,\n        legend=legend,\n        introductory_text=introductory_text,\n        submit_text=submit_text,\n    )\n\n\n# These examples come from the already-consumed independent QA #223. They are\n# regression fixtures only and must never be reported as a fresh QA metric.\n@pytest.mark.parametrize(\n    ("case_id", "kwargs", "expected"),\n    [\n        ("HF-S003-F01", {"introductory_text": "Get updates on Gorgias"}, "concrete"),\n        ("HF-S006-F01", {"introductory_text": "Join our newsletter Get CX insights, AI trends & product news delivered weekly.", "submit_text": "Subscribe"}, "concrete"),\n        ("HF-S006-F02", {"heading": "See Dixa in action", "submit_text": "Submit"}, "concrete"),\n        ("HF-S008-F01", {"submit_text": "Sign up free"}, "generic"),\n        ("HF-S008-F02", {"introductory_text": "Preview LiveChat® on your home page with one click", "submit_text": "Preview"}, "concrete"),\n        ("HF-S009-F01", {"heading": "Write to us", "introductory_text": "Fill in the form and the right team will pick it up. Press, abuse reports, and partnership questions all land in the right inbox.", "submit_text": "Send message"}, "concrete"),\n        ("HF-S015-F01", {"introductory_text": "Get a free demo", "submit_text": "Preview Bob (4:01)"}, "concrete"),\n        ("HF-S015-F02", {"introductory_text": "Watch a demo", "submit_text": "SKIP TO VIDEO | START VIDEO"}, "concrete"),\n        ("HF-S021-F03", {"heading": "Oh wait, did we mention that Freedcamp is absolutely free ?", "submit_text": "Start Now!"}, "concrete"),\n        ("HF-S022-F01", {"submit_text": "Try Free for 7 Days"}, "concrete"),\n        ("HF-S022-F04", {"introductory_text": "Join Over 250,000+ Smart Teams for Free", "submit_text": "Sign Up Now"}, "concrete"),\n        ("HF-S025-F01", {"submit_text": "Submit your ticket"}, "concrete"),\n        ("HF-S034-F02", {"heading": "Use the form to get in touch with the LogRocket team for a personalized demo.", "submit_text": "Get a demo"}, "concrete"),\n        ("HF-S040-F01", {"submit_text": "Sign up"}, "generic"),\n        ("HF-S045-F01", {"heading": "Reserva tu demo gratuita de Spendesk", "submit_text": "Enviar"}, "concrete"),\n        ("HF-S051-F03", {"introductory_text": "Get actionable BFCM tips and strategies for your team", "submit_text": "Get the Guide"}, "concrete"),\n        ("HF-S051-F04", {"introductory_text": "California Consumer Privacy Act Opt Out Form", "submit_text": "SUBMIT"}, "concrete"),\n        ("HF-S055-F03", {"heading": "Grow your list for free with signup forms", "introductory_text": "Start for free | No hidden fees | Privacy protected", "submit_text": "CREATE FREE ACCOUNT"}, "generic"),\n        ("HF-S061-F01", {"submit_text": "Create Account"}, "generic"),\n        ("HF-S067-F01", {"heading": "Contact Duo to get started", "legend": "How will you use Duo?*", "introductory_text": "Let’s make some headlines. Get in touch with our team for any press-related requests.", "submit_text": "Submit"}, "concrete"),\n        ("HF-S091-F01", {"heading": "Let's chat", "introductory_text": "Schedule a call to discuss your goals and how ButterCMS can help get there.", "submit_text": "Contact Us"}, "concrete"),\n        ("HF-S096-F01", {"heading": "Get started with your free Essentials account", "submit_text": "Create Account"}, "generic"),\n    ],\n)\ndef test_prv103_qa223_consumed_classifier_regressions(case_id, kwargs, expected):\n    assert _form_purpose_signal(_form(**kwargs)) == expected, case_id\n\n\ndef test_prv103_free_trial_remains_concrete_despite_signup_language():\n    assert _form_purpose_signal(_form(\n        heading="Sign up for a free trial",\n        submit_text="Create account",\n    )) == "concrete"\n'''
write("backend/tests/domain_packs/privacy/test_prv103_qa223_regression.py", regression)


# 6. Protect the conservative operational-context filter.
path = "backend/tests/web_inspector/test_form_context_capture.py"
text = read(path)
addition = '''\n\n@pytest.mark.parametrize("transient", ["Loading...", "Close", "Cargando..."])\ndef test_form_context_ignores_exact_transient_ui_text(transient):\n    html = f"""\n    <form>\n      <div>{transient}</div>\n      <input type="email" name="email">\n      <button type="submit">Get Started</button>\n    </form>\n    """\n\n    form = extract_page(html, "https://example.com/signup").forms[0]\n\n    assert form.introductory_text is None\n'''
if 'test_form_context_ignores_exact_transient_ui_text' in text:
    raise SystemExit("capture regression test already exists")
# Existing file has no pytest import yet.
text = replace_once(text, 'from mininode_api.web_inspector.extractor import extract_page\n', 'import pytest\n\nfrom mininode_api.web_inspector.extractor import extract_page\n', label="add pytest import")
text += addition
write(path, text)

print("PRV-103 v0.9 patch applied")
