import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).parents[4]
SCRIPT = ROOT / ".github/scripts/privacy_prv103_qa09_artifact_a.py"
spec = importlib.util.spec_from_file_location("privacy_prv103_qa09_artifact_a", SCRIPT)
qa = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(qa)


def _form(**overrides):
    values = {
        "source_url": "https://example.test/contact",
        "heading": "Contact Example",
        "legend": None,
        "introductory_text": "Tell Example what you need",
        "submit_text": "Send",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_frozen_pool_contract_and_hash():
    candidates = qa.load_frozen_candidates(ROOT)

    assert len(candidates) == 99
    assert len(set(candidates)) == 99
    assert qa.FROZEN_POOL_SHA256 == "33383fc229068633915d215404f0c9e0d368a1c7d2d968ad7047b97c1136b14a"


def test_artifact_a_exposes_only_allowed_blind_fields_and_redacts_identity():
    item = qa.artifact_a_item("QA09-A-001", _form(), "example.test")

    assert set(item) == {"blind_id", *qa.ALLOWED_FIELDS}
    serialized = json.dumps(item)
    assert "example.test" not in serialized.casefold()
    assert "example" not in serialized.casefold()
    assert "source_url" not in serialized


def test_high_forms_are_filtered_and_deduplicated(monkeypatch):
    duplicate = _form()
    other = _form(submit_text="Request demo")
    medium = _form(submit_text="Subscribe")
    confidence = {id(duplicate): (True, "high"), id(other): (True, "high"), id(medium): (True, "medium")}
    monkeypatch.setattr(qa, "_personal_form", lambda form: confidence[id(form)])

    selected = qa._deduplicated_high_forms([duplicate, duplicate, other, medium])

    assert [index for index, _ in selected] == [0, 2]


def test_capture_separates_blind_artifact_from_internal_manifest(tmp_path, monkeypatch):
    candidates = [f"site-{index}.example" for index in range(99)]
    monkeypatch.setattr(qa, "load_frozen_candidates", lambda root=None: candidates)
    monkeypatch.setattr(
        qa,
        "inspect_candidate",
        lambda hostname: (
            {"hostname": hostname, "requested_url": f"https://{hostname}/", "status": "captured"},
            [(0, _form(source_url=f"https://{hostname}/contact", heading="Contact"))],
        ),
    )

    summary = qa.capture(tmp_path)
    artifact = json.loads((tmp_path / "artifact-a.json").read_text())
    internal = json.loads((tmp_path / "internal-manifest.json").read_text())

    assert summary["sites_processed"] == 99
    assert summary["eligible_high_forms"] == 99
    assert summary["sufficient"] is True
    assert all(set(item) == {"blind_id", *qa.ALLOWED_FIELDS} for item in artifact)
    assert "site-0.example" not in json.dumps(artifact)
    assert internal["sites"][0]["hostname"] == "site-0.example"
    assert summary["prv103_executed"] is False


def test_capture_script_does_not_import_or_run_prv103():
    source = SCRIPT.read_text()

    assert "run_privacy_diagnostic" not in source
    assert "_form_purpose_signal" not in source
