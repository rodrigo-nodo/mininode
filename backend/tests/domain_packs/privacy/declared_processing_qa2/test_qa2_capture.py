from pathlib import Path


ROOT = Path(__file__).parent


def test_qa2_capture_is_passive_and_has_no_inference_dependency():
    source = (ROOT / "capture.py").read_text(encoding="utf-8")
    assert "client.get(" in source
    assert "client.post(" not in source
    assert "OPENAI_API_KEY" not in source
    assert "extract_declared_processing" not in source
