from fastapi import APIRouter, Header, HTTPException
from pathlib import Path
from typing import List
import hashlib

from ..core import config
from ..core.measure import now_ms, elapsed_ms
from ..core.ids import new_id
from ..models.api_base import ApiResponse, MetaObj, ErrorObj
from ..models.imaging import OptimizeIn, OptimizeOut, OptimizeMetrics
from ..services.pipeline.steps import _sha256 as _sha256_file, _apply_ops_and_save, SUPPORTED_OPS

router = APIRouter(prefix="/image", tags=["image"])

SUPPORTED_OPS = SUPPORTED_OPS

def _enforce_api_key(x_api_key: str | None):
    if not config.MININODE_API_KEY:
        return
    if not x_api_key or x_api_key != config.MININODE_API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")

def _bucket_dir(name: str) -> Path:
    d = Path(config.DATA_DIR).joinpath(name)
    d.mkdir(parents=True, exist_ok=True)
    return d

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

@router.post("/optimize", response_model=ApiResponse[OptimizeOut])
async def optimize_image(
    body: OptimizeIn,
    x_api_key: str | None = Header(default=None, convert_underscores=False),
):
    """
    MVP: copia uploads/ → optimized/ y reporta métricas (hash, size, delta).
    Comentario: aunque hoy algunas 'ops' sean no-op, el contrato ya reporta el aporte.
    """
    _enforce_api_key(x_api_key)
    t0 = now_ms()

    src = _bucket_dir("uploads").joinpath(body.file_id)
    if not src.exists():
        return ApiResponse(
            ok=False,
            time_ms=elapsed_ms(t0),
            data=None,
            error=ErrorObj(code="NOT_FOUND", message=f"file_id no existe en uploads: {body.file_id}"),
            meta=MetaObj(request_id=new_id("req"), version=config.API_VERSION),
        )

    ops_req: List[str] = list(body.ops or [])
    ops_applied = [op for op in ops_req if op in SUPPORTED_OPS]

    # Antes
    bytes_before = src.stat().st_size
    sha_before = _sha256_file(src)

    # Optimización real (deskew/binarize/denoise + re-encode)
    dst_id = new_id("opt")
    dst = _bucket_dir("optimized").joinpath(dst_id)
    _ = _apply_ops_and_save(src, dst, ops_applied)

    # Después
    bytes_after = dst.stat().st_size
    sha_after = _sha256_file(dst)
    size_delta_pct = round(((bytes_after - bytes_before) / max(1, bytes_before)) * 100.0, 2)
    changed = (sha_before != sha_after)

    out = OptimizeOut(
        src_file_id=body.file_id,
        file_id=dst_id,
        ops_requested=ops_req,
        ops_applied=ops_applied,
        metrics=OptimizeMetrics(
            changed=changed,
            bytes_before=bytes_before,
            bytes_after=bytes_after,
            size_delta_pct=size_delta_pct,
            sha256_before=sha_before,
            sha256_after=sha_after,
        )
    )
    return ApiResponse(
        ok=True,
        time_ms=elapsed_ms(t0),
        data=out,
        error=None,
        meta=MetaObj(request_id=new_id("req"), version=config.API_VERSION),
    )
