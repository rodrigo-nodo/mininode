# SPDX-License-Identifier: MIT
# Módulo de “anclas + ventana” para lectura de campos en documentos.
# Decisión: mantenemos reglas simples y deterministas (OCR + ventanas).
# - No reescribe anchors.yml; los “overrides” viven aparte (storage/DB).

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
import importlib.resources as resources
import re
import os

try:
    import yaml  # dependencia pequeña; si no está, solo carga dicts directos en tests
except ImportError:
    yaml = None


# -----------------------------
# Tipos
# -----------------------------
BBox = Tuple[float, float, float, float]  # (x, y, w, h) normalizado 0..1

@dataclass
class OCRWord:
    text: str
    bbox: BBox  # coords normalizadas

@dataclass
class AnchorHit:
    text: str
    bbox: BBox
    score: float  # similitud simple

@dataclass
class Window:
    bbox: BBox
    strategy: str  # right_of | below | left_of | above

@dataclass
class FieldResult:
    field: str
    value: Optional[str]
    confidence: float
    source: str  # "ocr|anchored|right_of", "llm|crop", etc.
    anchor: Optional[AnchorHit]
    window: Optional[Window]
    uncertain: bool


# -----------------------------
# Carga config (anchors + overrides)
# -----------------------------
def load_anchors_yaml(path: Optional[str] = None) -> Dict[str, Any]:
    """Carga anchors.yml desde un path explícito o desde recursos del paquete.

    - Si `path` es una ruta válida en el filesystem, carga desde allí.
    - Si `path` es None, usa el recurso empaquetado
      `mininode_api.services.capture.templates/anchors.yml`.
    """
    if yaml is None:
        raise RuntimeError("PyYAML no instalado. Instala 'pyyaml' o provee config dict en memoria.")

    # Caso 1: path explícito
    if path:
        if not os.path.exists(path):
            raise FileNotFoundError(f"anchors.yml no encontrado: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data or {}

    # Caso 2: recurso del paquete
    pkg = "mininode_api.services.capture.templates"
    try:
        res = resources.files(pkg).joinpath("anchors.yml")  # type: ignore[attr-defined]
        with res.open("r", encoding="utf-8") as f:  # type: ignore[assignment]
            data = yaml.safe_load(f)
        return data or {}
    except Exception as e:
        raise FileNotFoundError("anchors.yml no encontrado en recursos del paquete") from e

def merge_overrides(base_cfg: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """Fusión superficial: overrides pisa campos del mismo nivel."""
    if not overrides:
        return base_cfg
    merged = {**base_cfg}
    # v1: fusiona por document_types -> <doc> -> fields -> <field>
    for doc_type, doc_cfg in overrides.get("document_types", {}).items():
        merged.setdefault("document_types", {}).setdefault(doc_type, {}).setdefault("fields", {})
        for field, f_cfg in doc_cfg.get("fields", {}).items():
            merged["document_types"][doc_type]["fields"].setdefault(field, {})
            merged["document_types"][doc_type]["fields"][field].update(f_cfg)
    return merged


# -----------------------------
# Utilidades geométricas
# -----------------------------
def _intersects(b1: BBox, b2: BBox) -> bool:
    x1, y1, w1, h1 = b1
    x2, y2, w2, h2 = b2
    return not (x1 + w1 < x2 or x2 + w2 < x1 or y1 + h1 < y2 or y2 + h2 < y1)

def _inside(b_small: BBox, b_big: BBox) -> bool:
    x, y, w, h = b_small
    X, Y, W, H = b_big
    return x >= X and y >= Y and x + w <= X + W and y + h <= Y + H


# -----------------------------
# Búsqueda de ancla y ventana
# -----------------------------
def _norm(s: str) -> str:
    return s.strip().lower().replace("á", "a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u")

def find_anchor(ocr_words: List[OCRWord], anchors: List[str]) -> Optional[AnchorHit]:
    norm_anchors = [_norm(a) for a in anchors]
    for w in ocr_words:
        if _norm(w.text) in norm_anchors:
            return AnchorHit(text=w.text, bbox=w.bbox, score=1.0)
    # búsqueda contiene (tolerante)
    for w in ocr_words:
        t = _norm(w.text)
        for a in norm_anchors:
            if a in t and len(a) >= 3:
                return AnchorHit(text=w.text, bbox=w.bbox, score=0.7)
    return None

def build_window(anchor: AnchorHit, strategy: str, dx: float, dy: float) -> Window:
    ax, ay, aw, ah = anchor.bbox
    if strategy == "right_of":
        win = (ax + aw, ay, dx, max(dy, ah * 1.2))  # mismo renglón
    elif strategy == "below":
        win = (ax, ay + ah, dx, dy)
    elif strategy == "left_of":
        win = (max(0.0, ax - dx), ay, dx, max(dy, ah * 1.2))
    elif strategy == "above":
        win = (ax, max(0.0, ay - dy), dx, dy)
    else:
        # default razonable: derecha
        win = (ax + aw, ay, dx, max(dy, ah * 1.2))
    # recorta a página 0..1
    x, y, w, h = win
    x = max(0.0, min(1.0, x)); y = max(0.0, min(1.0, y))
    if x + w > 1.0: w = max(0.0, 1.0 - x)
    if y + h > 1.0: h = max(0.0, 1.0 - y)
    return Window(bbox=(x, y, w, h), strategy=strategy)


# -----------------------------
# Lectura dentro de ventana
# -----------------------------
def _collect_tokens_in_window(ocr_words: List[OCRWord], window: Window) -> List[OCRWord]:
    wx, wy, ww, wh = window.bbox
    wb = (wx, wy, ww, wh)
    return [w for w in ocr_words if _inside(w.bbox, wb) or _intersects(w.bbox, wb)]

def _pick_candidate_text(tokens: List[OCRWord]) -> str:
    # Heurística: concatena tokens por orden de x,y (línea por línea)
    tokens_sorted = sorted(tokens, key=lambda t: (round(t.bbox[1], 3), t.bbox[0]))
    return " ".join(t.text for t in tokens_sorted).strip()

def _validate_with_regex(text: str, regex: str) -> Optional[str]:
    if not regex:
        return text if text else None
    m = re.search(regex, text)
    return m.group(0) if m else None

def read_value_in_window(
    ocr_words: List[OCRWord],
    window: Window,
    field_name: str,
    regex: str
) -> Tuple[Optional[str], float, str]:
    tokens = _collect_tokens_in_window(ocr_words, window)
    if not tokens:
        return None, 0.0, "ocr|anchored|no_tokens"
    raw = _pick_candidate_text(tokens)
    val = _validate_with_regex(raw, regex)
    if val:
        return val, 0.93, f"ocr|anchored|{window.strategy}"
    # intento con limpieza básica
    clean = raw.replace(" ", "").replace("$", "")
    val = _validate_with_regex(clean, regex)
    if val:
        return val, 0.85, f"ocr|anchored_clean|{window.strategy}"
    return None, 0.4, f"ocr|anchored_fail|{window.strategy}"


# -----------------------------
# API principal de extracción
# -----------------------------
def extract_field(
    ocr_words: List[OCRWord],
    cfg_for_field: Dict[str, Any],
    field_name: str
) -> FieldResult:
    anchors: List[str] = cfg_for_field.get("anchors", [])
    strategy: str = cfg_for_field.get("strategy", "right_of")
    window_cfg: Dict[str, float] = cfg_for_field.get("window", {"dx": 0.2, "dy": 0.06})
    regex: str = cfg_for_field.get("regex", "")

    anchor = find_anchor(ocr_words, anchors)
    if not anchor:
        return FieldResult(
            field=field_name,
            value=None,
            confidence=0.0,
            source="cfg|no_anchor",
            anchor=None,
            window=None,
            uncertain=True,
        )

    win = build_window(anchor, strategy=strategy, dx=float(window_cfg.get("dx", 0.2)), dy=float(window_cfg.get("dy", 0.06)))
    val, conf, source = read_value_in_window(ocr_words, win, field_name, regex)

    return FieldResult(
        field=field_name,
        value=val,
        confidence=conf,
        source=source,
        anchor=anchor,
        window=win,
        uncertain=(val is None or conf < 0.8),
    )


# -----------------------------
# Punto de entrada por documento
# -----------------------------
def extract_fields_for_doc(
    ocr_words: List[OCRWord],
    anchors_config: Dict[str, Any],
    doc_type: str,
    fields: Optional[List[str]] = None,
) -> Dict[str, FieldResult]:
    """Extrae múltiples campos definidos en anchors.yml para un doc_type."""
    doc_cfg = anchors_config.get("document_types", {}).get(doc_type, {})
    fields_cfg = doc_cfg.get("fields", {})
    target_fields = fields or list(fields_cfg.keys())
    results: Dict[str, FieldResult] = {}
    for fname in target_fields:
        cfg = fields_cfg.get(fname, None)
        if not cfg:
            results[fname] = FieldResult(
                field=fname, value=None, confidence=0.0,
                source="cfg|missing_field", anchor=None, window=None, uncertain=True
            )
            continue
        results[fname] = extract_field(ocr_words, cfg, fname)
    return results
