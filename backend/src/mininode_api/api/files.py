from fastapi import APIRouter, UploadFile, File, Header, HTTPException
from pathlib import Path
from ..core import config
from ..core.measure import now_ms, elapsed_ms
from ..core.ids import new_id
from ..models.api_base import ApiResponse, MetaObj, ErrorObj
from ..models.files import UploadOut

router = APIRouter(prefix="/files", tags=["files"])

def _enforce_api_key(x_api_key: str | None):
    # En prod exigimos X-Api-Key; en dev puedes dejar MININODE_API_KEY vacío.
    if not config.MININODE_API_KEY:
        return
    if not x_api_key or x_api_key != config.MININODE_API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")

def _uploads_dir() -> Path:
    d = Path(config.DATA_DIR).joinpath("uploads")
    d.mkdir(parents=True, exist_ok=True)
    return d

@router.post("/upload", response_model=ApiResponse[UploadOut])
async def upload_file(
    file: UploadFile = File(...),
    x_api_key: str | None = Header(default=None, convert_underscores=False)
):
    _enforce_api_key(x_api_key)
    t0 = now_ms()

    file_id = new_id("upl")
    dst = _uploads_dir().joinpath(file_id)
    size = 0
    with open(dst, "wb") as f:
        chunk = await file.read(1024 * 1024)
        while chunk:
            size += len(chunk)
            f.write(chunk)
            chunk = await file.read(1024 * 1024)

    out = UploadOut(file_id=file_id, filename=file.filename, mime=file.content_type, size=size)
    return ApiResponse(
        ok=True,
        time_ms=elapsed_ms(t0),
        data=out,
        error=None,
        meta=MetaObj(request_id=new_id("req"), version=config.API_VERSION),
    )
