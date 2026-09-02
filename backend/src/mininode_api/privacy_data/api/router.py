from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from mininode_api.privacy_data.catalog import get_catalog
from mininode_api.privacy_data.models import (
    ActivityCreate,
    ActivityResponse,
    ActivityUpdate,
    CreatedDataMapResponse,
    DataMapResponse,
    DataMapUpdate,
)
from mininode_api.privacy_data.services import data_maps

router = APIRouter(prefix="/privacy/data", tags=["Privacy Data"])


def require_database(request: Request) -> None:
    if not getattr(request.app.state, "privacy_data_ready", False):
        raise HTTPException(status_code=503, detail="Privacy Data is unavailable")


def _get_map(token: str):
    try:
        return data_maps.get_data_map(token)
    except data_maps.DataMapNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except data_maps.DataMapExpiredError as exc:
        raise HTTPException(status_code=410, detail=str(exc)) from exc


@router.get("/catalog")
def catalog():
    return get_catalog()


@router.post("/maps", response_model=CreatedDataMapResponse, status_code=201, dependencies=[Depends(require_database)])
def create_map():
    created = data_maps.create_data_map()
    return {"token": created.token, "map": created.data_map}


@router.get("/maps/{token}", response_model=DataMapResponse, dependencies=[Depends(require_database)])
def retrieve_map(token: str):
    return _get_map(token)


@router.patch("/maps/{token}", response_model=DataMapResponse, dependencies=[Depends(require_database)])
def patch_map(token: str, payload: DataMapUpdate):
    # The service resolves the capability token before applying this allow-listed update.
    return data_maps.update_data_map(_get_map(token), payload.model_dump(exclude_unset=True))


@router.get("/maps/{token}/activities", response_model=list[ActivityResponse], dependencies=[Depends(require_database)])
def get_activities(token: str):
    return data_maps.list_activities(_get_map(token))


@router.post("/maps/{token}/activities", response_model=ActivityResponse, status_code=201, dependencies=[Depends(require_database)])
def post_activity(token: str, payload: ActivityCreate):
    values = payload.model_dump(mode="json")
    return data_maps.create_activity(_get_map(token), values)


@router.patch("/maps/{token}/activities/{activity_id}", response_model=ActivityResponse, dependencies=[Depends(require_database)])
def patch_activity(token: str, activity_id: UUID, payload: ActivityUpdate):
    values = payload.model_dump(mode="json", exclude_unset=True)
    try:
        return data_maps.update_activity(_get_map(token), activity_id, values)
    except data_maps.ActivityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/maps/{token}/activities/{activity_id}", status_code=204, dependencies=[Depends(require_database)])
def remove_activity(token: str, activity_id: UUID):
    try:
        data_maps.delete_activity(_get_map(token), activity_id)
    except data_maps.ActivityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)
