import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from contextlib import nullcontext

BACKEND_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.services import privacy_correction_plan_activation as activation  # noqa: E402
from mininode_api.services import privacy_correction_plan as plans  # noqa: E402
from mininode_api.services import privacy_correction_plan_order as orders  # noqa: E402
from mininode_api.services import privacy_diagnostic_snapshot as snapshots  # noqa: E402


def records(*, status="pending_payment", plan_id=None, expired=True):
    now = datetime.now(timezone.utc)
    diagnostic_id = uuid4()
    snapshot = {"site_url": "https://original.example/", "score": 42, "controls": [{"id": "PRV-001"}]}
    diagnostic = snapshots.StoredPrivacyDiagnostic(
        diagnostic_id, snapshot["site_url"], snapshot, 42, now - timedelta(days=2),
        now - timedelta(days=1) if expired else now + timedelta(hours=24),
    )
    order = orders.CorrectionPlanOrder(
        uuid4(), diagnostic_id, plan_id, "https://ignored.example/", "buyer@example.com",
        orders.PRODUCT_CODE, 49900, "CLP", status, now, now,
    )
    return order, diagnostic


@pytest.fixture(autouse=True)
def no_database_activation_lock(monkeypatch):
    monkeypatch.setattr(orders, "activation_lock", lambda _: nullcontext())


def test_activation_uses_original_snapshot_and_does_not_recheck_purchase_window(monkeypatch):
    order, diagnostic = records(expired=True)
    created = plans.CreatedCorrectionPlan(uuid4(), "one-time-secret")
    calls = []
    monkeypatch.setattr(orders, "get_order", lambda order_id: calls.append(("order", order_id)) or order)
    monkeypatch.setattr(snapshots, "get_diagnostic_snapshot", lambda diagnostic_id: calls.append(("snapshot", diagnostic_id)) or diagnostic)
    monkeypatch.setattr(activation.privacy_correction_plan_flow, "build_and_store_correction_plan", lambda value: calls.append(("build", value)) or (created, {}))
    monkeypatch.setattr(orders, "attach_correction_plan", lambda order_id, plan_id: calls.append(("attach", order_id, plan_id)) or orders.CorrectionPlanOrder(**{**order.__dict__, "correction_plan_id": plan_id, "status": "paid"}))

    result = activation.activate_order(order.id)

    assert calls == [("order", order.id), ("snapshot", order.diagnostic_id), ("build", diagnostic.diagnostic_snapshot), ("attach", order.id, created.id)]
    assert result.plan_path == "/privacy/plan/one-time-secret"
    assert result.status == "paid" and result.correction_plan_id == created.id
    assert "one-time-secret" not in order.__dict__.values()


@pytest.mark.parametrize("status,plan_id,error", [
    ("paid", uuid4(), activation.OrderAlreadyActivatedError),
    ("paid", None, activation.OrderActivationStateError),
    ("cancelled", None, activation.OrderActivationStateError),
])
def test_invalid_states_never_build_a_plan(monkeypatch, status, plan_id, error):
    order, _ = records(status=status, plan_id=plan_id)
    monkeypatch.setattr(orders, "get_order", lambda _: order)
    monkeypatch.setattr(activation.privacy_correction_plan_flow, "build_and_store_correction_plan", lambda _: pytest.fail("plan must not be built"))
    with pytest.raises(error):
        activation.activate_order(order.id)


def test_missing_order_never_builds_a_plan(monkeypatch):
    monkeypatch.setattr(orders, "get_order", lambda _: (_ for _ in ()).throw(orders.CorrectionPlanOrderNotFoundError()))
    monkeypatch.setattr(activation.privacy_correction_plan_flow, "build_and_store_correction_plan", lambda _: pytest.fail("plan must not be built"))
    with pytest.raises(orders.CorrectionPlanOrderNotFoundError):
        activation.activate_order(uuid4())
