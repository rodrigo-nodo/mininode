# Steps atómicos. Hoy sólo upload (pipeline 1).
from __future__ import annotations
from typing import Any, Dict, Tuple
from pathlib import Path
from ...core import config
from ...core.measure import now_ms, elapsed_ms
from ...core.ids import new_id

def _uploads_dir() -> Path:
    d = Path(config.DATA_DIR).joinpath("uploads")
    d.mkdir(parents=True, exist_ok=True)
    return d

def step_upload(ctx: Dict[str, Any], args: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """
    Requiere ctx['file'] = UploadFile. Devuelve file_id y metadatos.
    """
    t0 = now_ms()
    upf = ctx.get("file")
    if upf is None:
        raise ValueError("Se requiere 'file' en el contexto para step 'upload'.")

    file_id = new_id("upl")
    dst = _uploads_dir().joinpath(file_id)
    size = 0
    # Nota: upf.file es un SpooledTemporaryFile; leemos en binario.
    chunk = upf.file.read(1024 * 1024)
    with open(dst, "wb") as f:
        while chunk:
            size += len(chunk)
            f.write(chunk)
            chunk = upf.file.read(1024 * 1024)

    out = {"file_id": file_id, "filename": getattr(upf, "filename", None),
           "mime": getattr(upf, "content_type", None), "size": size}
    return out, elapsed_ms(t0)
