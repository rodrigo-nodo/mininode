# SPDX-License-Identifier: MIT
# Pipeline “limpio”: mini visión + OCR/anchors + combinación + fallback 4o

from __future__ import annotations
import base64, io, os, re, time
from typing import Dict, Any, List, Tuple, Optional

from PIL import Image
import pytesseract

from pydantic import BaseModel

from mininode_api.services.capture.schemas import (
    CaptureRequest, CaptureResponse, FieldOut, ConsistencyReport, CostBreakdown, TimingMs
)
from mininode_api.services.capture.zonas import (
    OCRWord, extract_fields_for_doc, load_anchors_yaml, merge_overrides
)

# --- OpenAI (usa la lib oficial 1.x)
try:
    from openai import OpenAI
    _OPENAI = OpenAI()
except Exception:
    _OPENAI = None  # permitimos correr sólo OCR/anchors si no está configurado


# =========================
# Config & costos (ajusta a tu realidad)
# =========================
# Ruta opcional vía env; si falta, se usa el recurso del paquete
ANCHORS_PATH = os.getenv("CAPTURE_ANCHORS_PATH")

TOKEN_COSTS = {
    "gpt-4o-mini": {"input": 0.00000015, "output": 0.00000060},
    "gpt-4o":      {"input": 0.00000500, "output": 0.00001500},
}

CRITICAL_FIELDS = {
    "guia":   ["folio", "rut_emisor", "total"],
    "boleta": ["folio", "total"],
    "factura":["folio", "rut_emisor", "total"],
}


# =========================
# Utilidades
# =========================
def _img_from_bytes_or_path(data_or_path: bytes | str) -> Image.Image:
    if isinstance(data_or_path, (bytes, bytearray)):
        return Image.open(io.BytesIO(data_or_path)).convert("RGB")
    return Image.open(data_or_path).convert("RGB")

def _b64_from_image(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode("utf-8")

def _norm_money(s: str) -> Optional[int]:
    if not s:
        return None
    s2 = s.replace("$", "").replace(" ", "").replace(".", "").replace("\u00A0", "")
    s2 = s2.replace(",", "")  # CLP sin decimales
    return int(s2) if s2.isdigit() else None


# =========================
# OCR tokens (palabra + bbox normalizado 0..1)
# =========================
def ocr_words(img: Image.Image) -> List[OCRWord]:
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, lang="spa+eng")
    W, H = img.size
    words: List[OCRWord] = []
    n = len(data.get("text", []))
    for i in range(n):
        text = (data["text"][i] or "").strip()
        if not text:
            continue
        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        if w <= 0 or h <= 0:
            continue
        words.append(OCRWord(text=text, bbox=(x / W, y / H, w / W, h / H)))
    return words


# =========================
# Paso 1: mini con imagen (visión)
# =========================
def proceso_imagen_mini(img: Image.Image, doc_type: str) -> Dict[str, Any]:
    if _OPENAI is None:
        return {}
    b64 = _b64_from_image(img)
    prompt = (
        f"Extrae en JSON los campos de un documento tipo '{doc_type}'. "
        "Responde SOLO JSON, sin texto adicional. Claves: folio, rut_emisor, rut_receptor, "
        "fecha_emision, neto, iva, total. Valores en string; si falta, usa null."
    )
    start = time.time()
    resp = _OPENAI.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.0,
        messages=[
            {"role": "system", "content": "Eres un extractor estricto. Devuelves SOLO JSON válido."},
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}" }}
            ]}
        ],
        response_format={"type": "json_object"},
    )
    took = int((time.time() - start) * 1000)
    content = resp.choices[0].message.content or "{}"
    try:
        import json as _json
        data = _json.loads(content)
    except Exception:
        data = {}
    usage = getattr(resp, "usage", None)
    return {
        "data": data,
        "took_ms": took,
        "usage": {
            "model": "gpt-4o-mini",
            "prompt": getattr(usage, "prompt_tokens", 0) if usage else 0,
            "completion": getattr(usage, "completion_tokens", 0) if usage else 0,
            "total": getattr(usage, "total_tokens", 0) if usage else 0,
        },
    }


# =========================
# Paso 2: OCR + anclas
# =========================
def proceso_tesseract_mini(img: Image.Image, doc_type: str, anchors_cfg: Dict[str, Any]) -> Dict[str, Any]:
    words = ocr_words(img)
    doc_cfg = anchors_cfg
    fields = extract_fields_for_doc(words, doc_cfg, doc_type=doc_type)
    out: Dict[str, Any] = {k: v.value for k, v in fields.items()}
    return {"data": out}


# =========================
# Paso 3: combinación simple
# =========================
def combinar_json(mini: Dict[str, Any], ocr: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    out.update(ocr.get("data") or {})
    for k, v in (mini.get("data") or {}).items():
        if not out.get(k) and v not in (None, "", []):
            out[k] = v
    return out


# =========================
# Paso 4: validación básica
# =========================
def validar_consistencia(doc_type: str, data: Dict[str, Any]) -> ConsistencyReport:
    checks: Dict[str, bool] = {}
    notes: List[str] = []
    # ejemplo: total >= neto
    try:
        n = _norm_money(str(data.get("neto") or ""))
        t = _norm_money(str(data.get("total") or ""))
        if n is not None and t is not None:
            checks["total>=neto"] = bool(t >= n)
    except Exception:
        notes.append("no_se_pudo_validar_total_neto")
    return ConsistencyReport(checks=checks, notes=notes)


# =========================
# Paso 5: Fallback 4o
# =========================
def fallback_con_4o(img: Image.Image, faltantes: List[str], doc_type: str) -> Dict[str, str]:
    if _OPENAI is None or not faltantes:
        return {}
    b64 = _b64_from_image(img)
    prompt = (
        f"Del siguiente documento tipo '{doc_type}', devuelve SOLO JSON con estas claves faltantes: "
        f"{', '.join(faltantes)}. Si no se ve con claridad, usa null."
    )
    resp = _OPENAI.chat.completions.create(
        model="gpt-4o",
        temperature=0.0,
        messages=[
            {"role": "system", "content": "Extractor estricto. Devuelve SOLO JSON sin texto adicional."},
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}" }}
            ]}
        ],
        response_format={"type": "json_object"},
    )
    content = resp.choices[0].message.content or "{}"
    try:
        import json as _json
        data = _json.loads(content)
    except Exception:
        data = {}
    usage = getattr(resp, "usage", None)
    return {
        "data": data,
        "usage": {
            "model": "gpt-4o",
            "prompt": getattr(usage, "prompt_tokens", 0) if usage else 0,
            "completion": getattr(usage, "completion_tokens", 0) if usage else 0,
            "total": getattr(usage, "total_tokens", 0) if usage else 0,
        }
    }


# =========================
# Costeo / tiempos
# =========================
def _sumar_costos(uso_list: List[Dict[str, Any]]) -> CostBreakdown:
    tokens: Dict[str, int] = {}
    usd: Dict[str, float] = {}
    total = 0.0
    for u in uso_list:
        if not u:
            continue
        model = u.get("model")
        if not model:
            continue
        inp = u.get("prompt", 0)
        out = u.get("completion", 0)
        total_tokens = u.get("total", inp + out)
        tokens[model] = tokens.get(model, 0) + total_tokens
        costo = inp * TOKEN_COSTS[model]["input"] + out * TOKEN_COSTS[model]["output"]
        usd[model] = usd.get(model, 0.0) + costo
        total += costo
    return CostBreakdown(tokens=tokens, usd=usd, total_usd=round(total, 6))


# =========================
# Orquestador principal
# =========================
def procesar_documento(
    file_or_bytes: str | bytes,
    req: CaptureRequest,
    overrides_cfg: Optional[Dict[str, Any]] = None
) -> CaptureResponse:
    t0 = time.time()
    img = _img_from_bytes_or_path(file_or_bytes)

    # anchors base + overrides
    anchors_base = load_anchors_yaml(ANCHORS_PATH)
    anchors_cfg = merge_overrides(anchors_base, overrides_cfg or {})

    # 1) mini visión
    t1 = time.time()
    mini = proceso_imagen_mini(img, doc_type=req.doc_type)
    t_mini = int((time.time() - t1) * 1000)

    # 2) OCR + anclas
    t2 = time.time()
    ocr_res = proceso_tesseract_mini(img, doc_type=req.doc_type, anchors_cfg=anchors_cfg)
    ocr_res["took_ms"] = int((time.time() - t2) * 1000)

    # 3) combinar
    combinado = combinar_json(mini, ocr_res)

    # 4) validar
    t3 = time.time()
    consistency = validar_consistencia(req.doc_type, combinado)
    t_validate = int((time.time() - t3) * 1000)

    # 5) críticos faltantes -> fallback
    faltantes: List[str] = []
    for f in CRITICAL_FIELDS.get(req.doc_type, []):
        if combinado.get(f) in (None, "", []):
            faltantes.append(f)

    uso_list = []
    if mini.get("usage"): uso_list.append(mini["usage"])

    fallback_tokens = None
    if req.usar_fallback and faltantes:
        fb = fallback_con_4o(img, faltantes=faltantes, doc_type=req.doc_type)
        for k, v in (fb.get("data") or {}).items():
            if k in faltantes and v not in (None, "", []):
                combinado[k] = v
        if fb.get("usage"):
            uso_list.append(fb["usage"])
        fallback_tokens = fb.get("usage", {})

    # 6) salida
    campos = req.return_fields or list(set(combinado.keys()))
    fields_out: Dict[str, FieldOut] = {}
    for k in campos:
        val = combinado.get(k)
        uncertain = (val in (None, "", []))
        source = "merge(ocr|mini)" if not uncertain else "merge|missing"
        fields_out[k] = FieldOut(
            value=val, confidence=0.9 if not uncertain else 0.0, source=source, uncertain=uncertain
        )

    timings = TimingMs(
        ocr=ocr_res["took_ms"],
        llm_mini=t_mini,
        llm_fallback=int(fallback_tokens.get("took_ms", 0)) if fallback_tokens else 0,
        validate=t_validate,
        total=int((time.time() - t0) * 1000),
    )
    cost = _sumar_costos(uso_list)

    return CaptureResponse(
        doc_type=req.doc_type,
        fields=fields_out,
        consistency=consistency,
        cost=cost,
        timings=timings,
    )
