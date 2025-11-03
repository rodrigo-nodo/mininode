from fastapi import APIRouter, Header, HTTPException
from pathlib import Path
from typing import List
from ..core import config
from ..core.measure import now_ms, elapsed_ms
from ..core.ids import new_id
from ..models.api_base import ApiResponse, MetaObj, ErrorObj
from ..models.imaging import OptimizeIn, OptimizeOut

router = APIRouter(prefix="/image", tags=["image"])

SUPPORTED_OPS = {"deskew", "binarize", "denoise"}

def _enforce_api_key(x_api_key: str | None):
    if not config.MININODE_API_KEY:
        return
    if not x_api_key or x_api_key != config.MININODE_API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")

def _bucket_dir(name: str) -> Path:
    d = Path(config.DATA_DIR).joinpath(name)
    d.mkdir(parents=True, exist_ok=True)
    return d

@router.post("/optimize", response_model=ApiResponse[OptimizeOut])
async def optimize_image(
    body: OptimizeIn,
    x_api_key: str | None = Header(default=None, convert_underscores=False),
):
    """
    MVP: copia el binario de uploads/ a optimized/ y marca ops_applied (filtra por SUPPORTED_OPS).
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

    dst_id = new_id("opt")
    dst = _bucket_dir("optimized").joinpath(dst_id)

    with open(src, "rb") as r, open(dst, "wb") as w:
        for chunk in iter(lambda: r.read(1024 * 1024), b""):
            w.write(chunk)

    out = OptimizeOut(
        src_file_id=body.file_id,
        file_id=dst_id,
        ops_requested=ops_req,
        ops_applied=ops_applied,
    )
    return ApiResponse(
        ok=True,
        time_ms=elapsed_ms(t0),
        data=out,
        error=None,
        meta=MetaObj(request_id=new_id("req"), version=config.API_VERSION),
    )
