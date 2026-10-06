"""Authenticated Billing endpoints. Provider callbacks are implemented by provider adapters."""
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from mininode_api.core.access_auth import require_access_user
from mininode_api.services import access, billing, mercadopago

router = APIRouter(prefix="/billing", tags=["billing"])

class CreateOrderRequest(BaseModel):
    workspace_site_id: UUID
    diagnostic_id: UUID

class OrderResponse(BaseModel):
    id: UUID
    workspace_site_id: UUID
    diagnostic_id: UUID
    product_code: str
    amount: int
    currency: str
    status: str

def _response(order: billing.Order) -> OrderResponse:
    return OrderResponse(**{name: getattr(order, name) for name in OrderResponse.model_fields})

@router.post("/orders", response_model=OrderResponse)
def create_order(body: CreateOrderRequest, user: access.StoredUser = Depends(require_access_user)):
    try:
        return _response(billing.create_order(user.id, body.workspace_site_id, body.diagnostic_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

@router.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: UUID, user: access.StoredUser = Depends(require_access_user)):
    order = billing.get_order(user.id, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return _response(order)

class EntitlementResponse(BaseModel):
    active: bool
    active_from: object | None = None
    active_until: object | None = None
    source: str | None = None

@router.get("/sites/{workspace_site_id}/entitlement", response_model=EntitlementResponse)
def entitlement(workspace_site_id: UUID, user: access.StoredUser = Depends(require_access_user)):
    row = billing.current_entitlement(user.id, workspace_site_id)
    if row is None:
        return EntitlementResponse(active=False)
    return EntitlementResponse(active=True, active_from=row[1], active_until=row[2], source=row[3])


class CheckoutResponse(BaseModel):
    checkout_url: str

@router.post("/orders/{order_id}/checkout", response_model=CheckoutResponse)
def start_checkout(order_id: UUID, user: access.StoredUser = Depends(require_access_user)):
    order = billing.get_order(user.id, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    try:
        _, checkout_url = mercadopago.create_checkout(order, payer_email=user.email)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return CheckoutResponse(checkout_url=checkout_url)

@router.post("/webhooks/mercadopago", include_in_schema=False)
def mercadopago_webhook(
    data_id: str = Query(alias="data.id"),
    type_: str = Query(alias="type"),
    x_signature: str = Header(alias="x-signature"),
    x_request_id: str = Header(alias="x-request-id"),
):
    if type_ != "order":
        return {"accepted": True}
    if not mercadopago.validate_webhook_signature(
        x_signature=x_signature, x_request_id=x_request_id, data_id=data_id
    ):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    try:
        mercadopago.process_order_notification(data_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"accepted": True}
