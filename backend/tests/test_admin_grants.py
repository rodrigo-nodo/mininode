"""PW-02 contract tests: operator-only mutations and unified renewal."""
import inspect
from uuid import uuid4

import pytest
from fastapi import HTTPException

from mininode_api.api import access as api
from mininode_api.services import admin_grants, billing


def test_grant_endpoints_require_operator(monkeypatch):
    monkeypatch.setattr(api.site_group_operator, "is_operator", lambda email: False)
    user = type("User", (), {"id": uuid4(), "email": "member@example.com"})()
    with pytest.raises(HTTPException) as exc:
        api.operator_create_grant(api.AdminGrantRequest(
            workspace_site_id=uuid4(), reason="Cortesía de prueba"), user)
    assert exc.value.status_code == 403
    with pytest.raises(HTTPException) as exc:
        api.operator_grant_sites("example.com", user)
    assert exc.value.status_code == 403
    with pytest.raises(HTTPException) as exc:
        api.operator_revoke_grant(uuid4(), api.AdminRevokeRequest(reason="Fin de prueba"), user)
    assert exc.value.status_code == 403


def test_grants_are_audited_and_lock_site():
    sql = inspect.getsource(admin_grants.grant)
    assert "FOR UPDATE" in sql
    assert "internal_grant" in sql
    assert "entitlement_admin_events" in sql
    assert "future" in sql


def test_revocation_does_not_delete_entitlement():
    source = inspect.getsource(admin_grants.revoke)
    assert "status='revoked'" in source
    assert "DELETE FROM" not in source
    assert "entitlement_admin_events" in source


def test_billing_checks_future_periods_across_sources():
    source = inspect.getsource(billing.payment_confirmed)
    assert "active_from > %s" in source
    assert "source = 'payment'" not in source[source.index("SELECT max(active_until)"):source.index("start = max(")]
