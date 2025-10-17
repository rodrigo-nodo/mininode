# SPDX-License-Identifier: MIT
import io
from PIL import Image, ImageDraw, ImageFont

from mininode_api.services.capture.pipeline import procesar_documento
from mininode_api.services.capture.schemas import CaptureRequest

def _fake_img():
    # Imagen blanca con texto "Total" y "123.456" debajo (simula un caso feliz simple)
    img = Image.new("RGB", (800, 600), "white")
    d = ImageDraw.Draw(img)
    d.text((320, 200), "Total", fill=(0,0,0))
    d.text((330, 240), "123.456", fill=(0,0,0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def test_pipeline_minimo_solo_ocr():
    # Forzamos a que OpenAI no esté: si en CI no hay key, mini y fallback devolverán vacío, quedando OCR/anclas.
    req = CaptureRequest(doc_type="guia", usar_fallback=False)
    res = procesar_documento(_fake_img(), req)
    assert res.doc_type == "guia"
    assert "total" in res.fields
    # No garantizamos OCR perfecto, pero chequeamos que no reviente:
    assert res.timings.total >= 0
