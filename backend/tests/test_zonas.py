# SPDX-License-Identifier: MIT
# Tests humo para zonas.py (ancla + ventana).
import math
from src.mininode_api.services.capture.zonas import OCRWord, extract_fields_for_doc

def _w(text, x, y, w, h):
    return OCRWord(text=text, bbox=(x, y, w, h))

def test_total_below_extraction():
    # Escenario: "Total" con valor justo debajo.
    ocr = [
        _w("Total", 0.40, 0.30, 0.08, 0.02),
        _w("$",     0.41, 0.35, 0.01, 0.02),
        _w("123.456", 0.42, 0.35, 0.10, 0.02),
        _w("irrelevante", 0.05, 0.90, 0.10, 0.02),
    ]
    cfg = {
        "document_types": {
            "guia": {
                "fields": {
                    "total": {
                        "anchors": ["Total", "Total a pagar"],
                        "strategy": "below",
                        "window": {"dx": 0.30, "dy": 0.08},
                        "regex": r"^\$?\s?[0-9\.]{3,12}(,[0-9]{2})?$",
                    }
                }
            }
        }
    }
    res = extract_fields_for_doc(ocr, cfg, doc_type="guia", fields=["total"])
    out = res["total"]
    assert out.value in ("123.456", "$123.456")
    assert out.source.startswith("ocr|anchored")
    assert out.uncertain is False
    assert out.confidence >= 0.85

def test_folio_right_of_extraction():
    # Escenario: "Folio" con valor a la derecha en misma línea.
    ocr = [
        _w("Folio", 0.10, 0.10, 0.08, 0.02),
        _w("98765", 0.20, 0.10, 0.06, 0.02),
    ]
    cfg = {
        "document_types": {
            "guia": {
                "fields": {
                    "folio": {
                        "anchors": ["Folio", "N°", "Nº Folio"],
                        "strategy": "right_of",
                        "window": {"dx": 0.15, "dy": 0.04},
                        "regex": r"^[0-9]{4,10}$",
                    }
                }
            }
        }
    }
    res = extract_fields_for_doc(ocr, cfg, doc_type="guia", fields=["folio"])
    out = res["folio"]
    assert out.value == "98765"
    assert out.uncertain is False
