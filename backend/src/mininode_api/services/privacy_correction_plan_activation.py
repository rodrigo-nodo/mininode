"""Manual Design Partner activation of a Privacy correction-plan order."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from mininode_api.services import privacy_correction_plan_flow
from mininode_api.services import privacy_correction_plan_order
from mininode_api.services import privacy_diagnostic_snapshot


class OrderAlreadyActivatedError(Exception):
    """The order already owns a correction plan."""


class OrderActivationStateError(Exception):
    """The order has a non-activatable or inconsistent state."""


@dataclass(frozen=True)
class ActivatedOrder:
    order_id: UUID
    status: str
    correction_plan_id: UUID
    plan_path: str


def activate_order(order_id: UUID) -> ActivatedOrder:
    """Build a plan from the order's immutable snapshot, without inspecting its URL."""
    with privacy_correction_plan_order.activation_lock(order_id):
        return _activate_locked_order(order_id)


def _activate_locked_order(order_id: UUID) -> ActivatedOrder:
    order = privacy_correction_plan_order.get_order(order_id)
    if order.status == "paid" and order.correction_plan_id is not None:
        raise OrderAlreadyActivatedError("Order already activated")
    if order.status != "pending_payment" or order.correction_plan_id is not None:
        raise OrderActivationStateError("Order cannot be activated")

    stored_diagnostic = privacy_diagnostic_snapshot.get_diagnostic_snapshot(
        order.diagnostic_id
    )
    created, _ = privacy_correction_plan_flow.build_and_store_correction_plan(
        stored_diagnostic.diagnostic_snapshot
    )
    try:
        activated = privacy_correction_plan_order.attach_correction_plan(
            order.id, created.id
        )
    except privacy_correction_plan_order.CorrectionPlanOrderStateError as exc:
        # A concurrent activation can win after the initial read. Never issue its
        # secret again or attempt to create another usable link.
        raise OrderAlreadyActivatedError("Order activation conflict") from exc
    return ActivatedOrder(
        order_id=activated.id,
        status=activated.status,
        correction_plan_id=created.id,
        plan_path=f"/privacy/plan/{created.access_token}",
    )
