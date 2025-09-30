import uuid, re
from typing import Any, Dict, Optional
from .schemas import Image2JsonResult

def _maybe_llm():
    try:
        from mininode_api.core.llm import LLMClient, ChatMessage
        return LLMClient(), ChatMessage
    except Exception:
        return None, None

async def run_image2json(image_bytes: bytes) -> Image2JsonResult:
    # 1) OCR stub
    ocr_text = "NUM_DOC: 12345\nRUT: 12.345.678-5\nFECHA: 2025-09-20\nTOTAL: 45.990"

    # 2) Regex baseline
    def _extract(pat: str) -> Optional[str]:
        m = re.search(pat, ocr_text, flags=re.IGNORECASE)
        return m.group(1) if m else None

    data: Dict[str, Any] = {
        "num_doc": _extract(r"NUM_DOC[:\s]+(\d+)"),
        "rut_emisor": _extract(r"RUT[:\s]+([0-9.\-Kk]+)"),
        "fecha": _extract(r"FECHA[:\s]+([\d\-/]+)"),
        "total": _extract(r"TOTAL[:\s]+([\d.,]+)"),
    }

    llm, ChatMessage = _maybe_llm()
    if llm and ChatMessage:
        try:
            system = ChatMessage(role="system", content="Normaliza campos de un comprobante chileno.")
            user = ChatMessage(role="user", content=f"OCR:\n{ocr_text}\nCampos:\n{data}")
            _ = await llm.chat([system, user])
        except Exception:
            pass

    confidences = {k: (0.9 if v else 0.3) for k, v in data.items()}
    notes = "Pipeline: OCR(stub)→regex→(LLM opcional)."

    return Image2JsonResult(
        id=str(uuid.uuid4()),
        json=data,
        confidences=confidences,
        notes=notes,
    )
