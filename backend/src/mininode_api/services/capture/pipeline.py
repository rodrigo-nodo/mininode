# SPDX-License-Identifier: MIT
# Pipeline “limpio”: mini visión + OCR/anchors + combinación + fallback 4o

from __future__ import annotations
import base64, io, os, re, time
from typing import Dict, Any, List, Tuple, Optional

from PIL import Image, ImageOps, ImageFilter
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
    _OPENAI = OpenAI(timeout=8.0, max_retries=1)
except Exception:
    _OPENAI = None  # permitimos correr sólo OCR/anchors si no está configurado


# =========================
# Config & costos (ajusta a tu realidad)
# =========================
# Ruta opcional vía env; si falta, se usa el recurso del paquete
ANCHORS_PATH = os.getenv("CAPTURE_ANCHORS_PATH")
TIME_BUDGET_MS = int(os.getenv("CAPTURE_TIME_BUDGET_MS", "14000"))

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

def _downscale(img: Image.Image, max_side: int = 1600) -> Image.Image:
    w, h = img.size
    m = max(w, h)
    if m <= max_side:
        return img
    scale = max_side / float(m)
    new_size = (int(w * scale), int(h * scale))
    return img.resize(new_size)

def _norm_money(s: str) -> Optional[int]:
    if not s:
        return None
    s2 = s.replace("$", "").replace(" ", "").replace(".", "").replace("\u00A0", "")
    s2 = s2.replace(",", "")  # CLP sin decimales
    return int(s2) if s2.isdigit() else None

def _norm_number_float(s: str) -> Optional[float]:
    if not s:
        return None
    txt = str(s).strip()
    txt = txt.replace('$', '').replace(' ', '').replace('\u00A0', '')
    if '.' in txt and ',' in txt:
        last_dot = txt.rfind('.')
        last_com = txt.rfind(',')
        if last_com > last_dot:
            txt = txt.replace('.', '').replace(',', '.')
        else:
            txt = txt.replace(',', '')
    else:
        if ',' in txt:
            parts = txt.split(',')
            if len(parts[-1]) in (1, 2):
                txt = txt.replace('.', '').replace(',', '.')
            else:
                txt = txt.replace(',', '')
        elif '.' in txt:
            parts = txt.split('.')
            if len(parts[-1]) not in (1, 2):
                txt = txt.replace('.', '')
    try:
        return float(txt)
    except Exception:
        return None

def _extract_items_fast(words: List[OCRWord]) -> List[Dict[str, Optional[str]]]:
    if not words:
        return []
    rows: Dict[int, List[OCRWord]] = {}
    for w in words:
        y = int(round(w.bbox[1] * 200))
        rows.setdefault(y, []).append(w)
    sorted_rows = sorted(rows.items(), key=lambda kv: kv[0])
    items: List[Dict[str, Optional[str]]] = []
    header_seen = False
    for _, toks in sorted_rows:
        toks = sorted(toks, key=lambda t: t.bbox[0])
        texts = [t.text for t in toks]
        line = ' '.join(texts).lower()
        if not header_seen and any(k in line for k in ['cantidad', 'cant', 'p.u', 'precio', 'total']):
            header_seen = True
            continue
        if not header_seen:
            continue
        # detect code first
        codigo = None
        for t in toks:
            if any(ch.isalnum() for ch in t.text):
                codigo = t.text
                break
        # collect numeric tokens
        nums = []
        for t in toks:
            st = t.text.replace('$','').replace('%','').strip()
            if any(ch.isdigit() for ch in st):
                val = _norm_number_float(st)
                if val is not None:
                    nums.append((t, val))
        if len(nums) < 2:
            continue
        nums_sorted = sorted(nums, key=lambda x: x[0].bbox[0])
        total_token, total_val = nums_sorted[-1]

        # quantity: first integer-like not equal to code token
        cantidad_val = None
        for tok, val in nums_sorted:
            if codigo and tok.text == codigo:
                continue
            if abs(val - int(val)) < 1e-6:
                cantidad_val = val
                break

        # Choose unit price robustly, ignoring discount column if present
        # Prefer candidate to the left of total that best matches total/cantidad
        precio_val = None
        try:
            # tokens with a percent sign are likely discounts; ignore them
            percent_tokens = {t for t in toks if '%' in t.text}
            price_candidates = [(tok, val) for (tok, val) in nums_sorted
                                 if tok.bbox[0] < total_token.bbox[0] and tok not in percent_tokens]
            if price_candidates:
                if cantidad_val and cantidad_val > 0:
                    target = float(total_val) / float(cantidad_val)
                    precio_val = min(price_candidates, key=lambda tv: abs(tv[1] - target))[1]
                else:
                    # Fallback: pick the rightmost candidate (closest to total), excluding discounts
                    precio_val = price_candidates[-1][1]
        except Exception:
            pass
        desc_tokens = []
        seen_code = False
        for t in toks:
            if not seen_code and codigo and t.text == codigo:
                seen_code = True
                continue
            if seen_code and t.bbox[0] < total_token.bbox[0]:
                vt = _norm_number_float(t.text)
                if vt is None:
                    desc_tokens.append(t.text)
        descripcion = ' '.join(desc_tokens).strip() or None
        item = {
            'codigo': codigo,
            'descripcion': descripcion,
            'cantidad': str(int(cantidad_val)) if cantidad_val is not None else None,
            'precio_unitario': (f"{precio_val:.2f}" if isinstance(precio_val, float) else None),
            'total_linea': (f"{total_val:.2f}" if isinstance(total_val, float) else None),
        }
        items.append(item)
    return items

def _preprocess_for_ocr(img: Image.Image) -> Image.Image:
    """Preprocesado ligero para OCR: gris, autocontraste y filtro mediano.
    Devuelve una copia procesada; si falla, retorna la original.
    """
    try:
        g = ImageOps.grayscale(img)
        g = ImageOps.autocontrast(g, cutoff=1)
        g = g.filter(ImageFilter.MedianFilter(size=3))
        return g
    except Exception:
        return img


# =========================
# OCR tokens (palabra + bbox normalizado 0..1)
# =========================
def ocr_words(img: Image.Image) -> List[OCRWord]:
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, lang="spa")
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

def proceso_imagen_4o_header(img: Image.Image, doc_type: str) -> Dict[str, Any]:
    """Extrae cabecera con gpt-4o (visión): folio, RUTs, fecha, neto, iva, total."""
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
        model="gpt-4o",
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
            "model": "gpt-4o",
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
    # Meta de confianza/estado por campo (para decisiones de fallback)
    meta = {
        k: {
            "confidence": (v.confidence or 0.0),
            "uncertain": bool(v.uncertain),
            "source": v.source,
        }
        for k, v in fields.items()
    }
    return {"data": out, "meta": meta}


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
    img = _downscale(img)

    # anchors base + overrides
    anchors_base = load_anchors_yaml(ANCHORS_PATH)
    anchors_cfg = merge_overrides(anchors_base, overrides_cfg or {})

    # 1) mini visión
    t1 = time.time()
    hdr_mini = proceso_imagen_mini(img, doc_type=req.doc_type)
    t_llmmini = int((time.time() - t1) * 1000)

    # 2) OCR + anclas
    t2 = time.time()
    img_ocr = _preprocess_for_ocr(img)
    ocr_res = proceso_tesseract_mini(img_ocr, doc_type=req.doc_type, anchors_cfg=anchors_cfg)
    ocr_res["took_ms"] = int((time.time() - t2) * 1000)
    # 2.5) Items (ROI l�gico sobre tokens OCR)
    t_items = time.time()
    words_all = ocr_words(img_ocr)
    items = _extract_items_fast(words_all)
    roi_table_ms = int((time.time() - t_items) * 1000)

    # 3) combinar
    combinado = combinar_json(hdr_mini, ocr_res)

    # 4) validar
    t3 = time.time()
    consistency = validar_consistencia(req.doc_type, combinado)
    t_validate = int((time.time() - t3) * 1000)

    # 5) críticos faltantes -> fallback
    faltantes: List[str] = []
    for f in CRITICAL_FIELDS.get(req.doc_type, []):
        if combinado.get(f) in (None, "", []):
            faltantes.append(f)

    # Reglas extra de calidad para fallback
    has_failed_checks = any(v is False for v in (consistency.checks or {}).values())
    ocr_meta = ocr_res.get("meta") or {}
    low_conf_crit: List[str] = []
    for f in CRITICAL_FIELDS.get(req.doc_type, []):
        m = ocr_meta.get(f) or {}
        if m.get("confidence", 0.0) < 0.6:
            low_conf_crit.append(f)

    uso_list = []
    if hdr_mini.get("usage"): uso_list.append(hdr_mini["usage"]) 

    fallback_tokens = None
    fallback_took_total_ms = 0
    adjusted_fields: List[str] = []
    elapsed_ms = int((time.time() - t0) * 1000)
    time_left = TIME_BUDGET_MS - elapsed_ms
    if req.usar_fallback and faltantes and time_left > 2500:
        _t_fb = time.time()
        fb = fallback_con_4o(img, faltantes=faltantes, doc_type=req.doc_type)
        for k, v in (fb.get("data") or {}).items():
            if k in faltantes and v not in (None, "", []):
                combinado[k] = v
                adjusted_fields.append(k)
        if fb.get("usage"):
            uso_list.append(fb["usage"]) 
        fallback_tokens = fb.get("usage", {})
        fallback_took_total_ms += int((time.time() - _t_fb) * 1000)

    # Fallback adicional si hubo fallas de consistencia o baja confianza en críticos
    elapsed_ms = int((time.time() - t0) * 1000)
    time_left = TIME_BUDGET_MS - elapsed_ms
    if req.usar_fallback and (has_failed_checks or low_conf_crit) and time_left > 2500:
        _t_fb2 = time.time()
        fb2 = fallback_con_4o(img, faltantes=CRITICAL_FIELDS.get(req.doc_type, []), doc_type=req.doc_type)
        for k, v in (fb2.get("data") or {}).items():
            if v in (None, "", []):
                continue
            if (k in low_conf_crit) or has_failed_checks:
                combinado[k] = v
                if k not in adjusted_fields:
                    adjusted_fields.append(k)
        if fb2.get("usage"):
            uso_list.append(fb2["usage"]) 
        fallback_took_total_ms += int((time.time() - _t_fb2) * 1000)

    # 6) salida (recalcular consistencia post-fallback si hubo ajustes)
    consistency_after = None
    if adjusted_fields:
        t3b = time.time()
        consistency_after = validar_consistencia(req.doc_type, combinado)
        t_validate += int((time.time() - t3b) * 1000)

    # 7) construir salida
    campos = req.return_fields or list(set(combinado.keys()))
    fields_out: Dict[str, FieldOut] = {}
    for k in campos:
        raw_val = combinado.get(k)
        val = None if raw_val is None else (raw_val if isinstance(raw_val, str) else str(raw_val))
        uncertain = (val in (None, "", []))
        source = "merge(ocr|mini)" if not uncertain else "merge|missing"
        fields_out[k] = FieldOut(
            value=val, confidence=0.9 if not uncertain else 0.0, source=source, uncertain=uncertain
        )

    timings = TimingMs(
        ocr=ocr_res["took_ms"],
        llm_mini=t_llmmini,
        llm_fallback=fallback_took_total_ms,
        validate_ms=t_validate,
        total=int((time.time() - t0) * 1000),
    )
    cost = _sumar_costos(uso_list)

    return CaptureResponse(
    doc_type=req.doc_type,
    fields=fields_out,
    consistency=consistency,
    consistency_after_fallback=consistency_after,
    cost=cost,
    timings=timings,
    fallback_applied=bool(adjusted_fields),
    adjusted_fields=adjusted_fields,
    items=items if 'items' in locals() else [],
    )









