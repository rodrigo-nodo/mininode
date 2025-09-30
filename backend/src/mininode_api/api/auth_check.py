from fastapi import APIRouter, Depends
from mininode_api.core.auth import require_api_key

router = APIRouter()

@router.get("/auth/check", dependencies=[Depends(require_api_key)])
def auth_check():
    # No devolvemos la clave. Opcional: un ID sintético/constante.
    return {"ok": True}
