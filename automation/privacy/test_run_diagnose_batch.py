import csv
import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("run_diagnose_batch.py")
spec = importlib.util.spec_from_file_location("privacy_batch", MODULE_PATH)
privacy_batch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(privacy_batch)


def test_parse_urls_deduplicates_and_ignores_blanks():
    raw = "\nhttps://a.example/\n# note\nhttps://a.example/\nhttps://b.example/\n"
    assert privacy_batch.parse_urls(raw) == ["https://a.example/", "https://b.example/"]


def test_write_outputs_creates_json_and_csv(tmp_path):
    results = [
        {
            "url": "https://a.example/",
            "http_status": 200,
            "success": True,
            "error_code": None,
            "detail": None,
            "response": {"score": 80},
        },
        {
            "url": "https://b.example/",
            "http_status": 400,
            "success": False,
            "error_code": "unsafe_target",
            "detail": "Target is not allowed",
            "response": {"detail": {"code": "unsafe_target"}},
        },
    ]

    json_path, csv_path = privacy_batch.write_outputs(results, tmp_path, "education-14")

    assert json.loads(json_path.read_text(encoding="utf-8")) == results
    with csv_path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["url"] == "https://a.example/"
    assert rows[1]["error_code"] == "unsafe_target"
