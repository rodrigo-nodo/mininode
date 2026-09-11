from pathlib import Path
import importlib.util


SCRIPT = Path(__file__).parents[4] / ".github" / "scripts" / "privacy_prv103_qa8_capture.py"
spec = importlib.util.spec_from_file_location("privacy_prv103_qa8_capture", SCRIPT)
qa8 = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(qa8)


def test_qa8_freezes_100_unique_candidates_and_30_site_target():
    assert qa8.MAX_SITES == 100
    assert qa8.TARGET_SITES == 30
    assert len(qa8.CANDIDATES) == 100
    urls = [row[3] for row in qa8.CANDIDATES]
    assert len(set(urls)) == 100
    assert len({qa8._host(url) for url in urls}) == 100


def test_qa8_candidates_are_absent_from_recorded_historical_corpus():
    qa8.assert_fresh_candidates(Path(__file__).parents[4])


def test_unique_high_filters_confidence_and_semantic_duplicates():
    base = {
        "personal_confidence": "high",
        "heading": "Contact us",
        "legend": None,
        "introductory_text": None,
        "submit_text": "Send",
    }
    forms = [base, dict(base), {**base, "personal_confidence": "medium"}, {**base, "submit_text": "Request demo"}]
    result = qa8.unique_high(forms)
    assert len(result) == 2


def test_blind_item_exposes_only_approved_fields():
    form = {
        "heading": "Request demo",
        "legend": None,
        "introductory_text": "Tell us what you need",
        "submit_text": "Send",
        "hostname": "example.test",
        "action": "https://example.test/private",
        "fields": ["email"],
    }
    item = qa8.blind_item("QA8-001", form)
    assert set(item) == {"blind_id", *qa8.ALLOWED_FIELDS}
    serialized = str(item)
    assert "example.test" not in serialized
    assert "fields" not in serialized


def test_reviewer_markdown_contains_no_site_metadata():
    text = qa8.reviewer_markdown([
        {
            "blind_id": "QA8-001",
            "heading": "Contact us",
            "legend": None,
            "introductory_text": None,
            "submit_text": "Send",
        }
    ])
    assert "QA8-001" in text
    assert "Contact us" in text
    assert "http" not in text
    assert "example.test" not in text
