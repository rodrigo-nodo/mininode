# SPDX-License-Identifier: MIT
import io
from PIL import Image, ImageDraw
from fastapi.testclient import TestClient
import os, sys

# Ensure src in path when running tests manually
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from app import app


def _fake_img_bytes():
    img = Image.new("RGB", (600, 400), "white")
    d = ImageDraw.Draw(img)
    d.text((200, 140), "Total", fill=(0, 0, 0))
    d.text((210, 180), "123.456", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_capture_endpoint_multipart_basic():
    c = TestClient(app)
    files = {"file": ("sample.png", _fake_img_bytes(), "image/png")}
    r = c.post("/capture?doc_type=guia&usar_fallback=false", files=files)
    assert r.status_code == 200
    data = r.json()
    assert data["doc_type"] == "guia"
    assert "fields" in data
    assert "timings" in data
    assert data["timings"]["total"] >= 0

