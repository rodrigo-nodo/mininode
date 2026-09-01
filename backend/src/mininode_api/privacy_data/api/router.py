from fastapi import APIRouter, Depends, HTTPException, Request

from mininode_api.privacy_data.catalog import get_catalog
from mininode_api.privacy_data.models import CreatedDataMapResponse, DataMapResponse
from mininode_api.privacy_data.services import data_maps

router = APIRouter(prefix="/privacy/data", tags=["Privacy Data"])


def require_database(request: Request) -> None:
    if not getattr(request.app.state, "privacy_data_ready", False):
        raise HTTPException(status_code=503, detail="Privacy Data is unavailable")


@router.get("/catalog")
def catalog():
    return get_catalog()


@router.post("/maps", response_model=CreatedDataMapResponse, status_code=201, dependencies=[Depends(require_database)])
def create_map():
    created = data_maps.create_data_map()
    return {"token": created.token, "map": created.data_map}


@router.get("/maps/{token}", response_model=DataMapResponse, dependencies=[Depends(require_database)])
def retrieve_map(token: str):
    try:
        return data_maps.get_data_map(token)
    except data_maps.DataMapNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except data_maps.DataMapExpiredError as exc:
        raise HTTPException(status_code=410, detail=str(exc)) from exc
