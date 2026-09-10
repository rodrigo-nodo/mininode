from pathlib import Path
import importlib.util


SCRIPT = Path(__file__).parents[4] / ".github" / "scripts" / "privacy_prv103_qa7_capture.py"
spec = importlib.util.spec_from_file_location("privacy_prv103_qa7_capture", SCRIPT)
qa7 = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(qa7)


def test_qa7_targets_are_exactly_30_unique_sites():
    assert len(qa7.TARGETS) == 30
    urls = [row[4] for row in qa7.TARGETS]
    assert len(set(urls)) == 30


def test_unique_high_filters_confidence_and_semantic_duplicates():
    base = {
        "personal_confidence": "high",
        "heading": "Contact us",
        "legend": None,
        "introductory_text": None,
        "submit_text": "Send",
    }
    forms = [base, dict(base), {**base, "personal_confidence": "medium"}, {**base, "submit_text": "Request quote"}]
    result = qa7.unique_high(forms)
    assert len(result) == 2


def test_blind_item_exposes_only_approved_fields():
    form = {
        "heading": "Request quote",
        "legend": None,
        "introductory_text": "Tell us what you need",
        "submit_text": "Send",
        "hostname": "example.test",
        "action": "https://example.test/private",
        "fields": ["email"],
    }
    item = qa7.blind_item("QA7-001", form)
    assert set(item) == {"blind_id", *qa7.ALLOWED_FIELDS}
    serialized = str(item)
    assert "example.test" not in serialized
    assert "fields" not in serialized


def test_reviewer_markdown_does_not_add_site_metadata():
    text = qa7.reviewer_markdown([
        {
            "blind_id": "QA7-001",
            "heading": "Contact us",
            "legend": None,
            "introductory_text": None,
            "submit_text": "Send",
        }
    ])
    assert "QA7-001" in text
    assert "Contact us" in text
    assert "http" not in text
    assert "hostname" not in text
