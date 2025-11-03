# Steps atómicos. Hoy sólo upload (pipeline 1).
from __future__ import annotations
from typing import Any, Dict, Tuple
from pathlib import Path
from ...core import config
from ...core.measure import now_ms, elapsed_ms
from ...core.ids import new_id

SUPPORTED_OPS = {"deskew", "binarize", "denoise"}

def _uploads_dir() -> Path:
    d = Path(config.DATA_DIR).joinpath("uploads")
    d.mkdir(parents=True, exist_ok=True)
    return d

def _bucket_dir(name: str) -> Path:
    d = Path(config.DATA_DIR).joinpath(name)
    d.mkdir(parents=True, exist_ok=True)
    return d

def step_upload(ctx: Dict[str, Any], args: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    t0 = now_ms()
    upf = ctx.get("file")
    if upf is None:
        raise ValueError("Se requiere 'file' en el contexto para step 'upload'.")

    file_id = new_id("upl")
    dst = _bucket_dir("uploads").joinpath(file_id)
    size = 0
    chunk = upf.file.read(1024 * 1024)
    with open(dst, "wb") as f:
        while chunk:
            size += len(chunk)
            f.write(chunk)
            chunk = upf.file.read(1024 * 1024)

    out = {"file_id": file_id, "filename": getattr(upf, "filename", None),
           "mime": getattr(upf, "content_type", None), "size": size}
    return out, elapsed_ms(t0)

def step_optimize(ctx: Dict[str, Any], args: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """
    MVP: toma ctx['file_id'] (generado por upload), copia a optimized/ y marca ops_applied.
    """
    t0 = now_ms()
    src_id = ctx.get("file_id")
    if not src_id:
        raise ValueError("Falta 'file_id' en el contexto para 'optimize' (ejecuta 'upload' antes).")

    src = _bucket_dir("uploads").joinpath(src_id)
    if not src.exists():
        raise ValueError(f"file_id no existe en uploads: {src_id}")

    ops_req: List[str] = list(args.get("ops", []))
    ops_applied = [op for op in ops_req if op in SUPPORTED_OPS]

    dst_id = new_id("opt")
    dst = _bucket_dir("optimized").joinpath(dst_id)

    with open(src, "rb") as r, open(dst, "wb") as w:
        for chunk in iter(lambda: r.read(1024 * 1024), b""):
            w.write(chunk)

    ctx["file_id"] = dst_id
    out = {
        "src_file_id": src_id,
        "file_id": dst_id,
        "ops_requested": ops_req,
        "ops_applied": ops_applied,
    }
    return out, elapsed_ms(t0)
