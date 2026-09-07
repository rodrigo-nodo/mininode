import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

BACKEND_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.privacy_data.catalog import get_catalog  # noqa: E402
from mininode_api.privacy_data.models.activity import ActivityAnswers  # noqa: E402
from mininode_api.privacy_data.review import review_data_map  # noqa: E402
from mininode_api.privacy_data.services import data_maps  # noqa: E402

NOW = datetime.now(timezone.utc)


def stored_map():
    return data_maps.StoredDataMap(
        uuid4(), "draft", None, None, "1", NOW, NOW, NOW + timedelta(days=7)
    )


def activity(data_map, rights_handling=None):
    return data_maps.StoredActivity(
        uuid4(),
        data_map.id,
        "sales",
        "own_operations",
        0,
        {
            "retention": {"status": "defined"},
            "access_roles": ["owner_only"],
            "security_measures": ["passwords_device_lock"],
            "rights_handling": rights_handling,
            "has_third_parties": False,
            "third_parties": [],
            "may_include_minors": False,
        },
        NOW,
        NOW,
    )


def rights_codes(data_map, status):
    return [
        item.code
        for item in review_data_map(data_map, [activity(data_map, status)])
        if item.code in {"D11", "D12", "D13"}
    ]


def test_catalog_exposes_plain_language_rights_handling_options():
    options = get_catalog()["rights_handling"]
    assert options == [
        {"code": "defined", "label": "Sí, tengo una forma definida"},
        {"code": "case_by_case", "label": "Lo resolvemos caso a caso"},
        {"code": "none", "label": "No tenemos una forma definida"},
        {"code": "unknown", "label": "No estoy seguro"},
    ]


def test_rights_handling_defaults_to_unasked_none():
    assert ActivityAnswers().rights_handling is None


@pytest.mark.parametrize("status", ["defined", "case_by_case", "none", "unknown"])
def test_rights_handling_accepts_supported_statuses(status):
    assert ActivityAnswers(rights_handling=status).rights_handling == status


def test_rights_handling_rejects_unknown_catalog_value():
    with pytest.raises(ValidationError):
        ActivityAnswers(rights_handling="not-a-rights-status")


def test_unasked_rights_does_not_create_an_observation():
    data_map = stored_map()
    assert rights_codes(data_map, None) == []


def test_defined_rights_handling_does_not_create_a_review():
    data_map = stored_map()
    assert rights_codes(data_map, "defined") == []


def test_case_by_case_rights_handling_creates_d11():
    data_map = stored_map()
    result = review_data_map(data_map, [activity(data_map, "case_by_case")])
    observation = next(item for item in result if item.code == "D11")
    assert observation.topic == "Derechos"
    assert observation.action == "Define una forma simple y repetible para responder estas solicitudes."


def test_no_rights_process_creates_d12():
    data_map = stored_map()
    result = review_data_map(data_map, [activity(data_map, "none")])
    observation = next(item for item in result if item.code == "D12")
    assert observation.topic == "Derechos"
    assert observation.action == "Define cómo recibir y responder solicitudes sobre datos personales."


def test_unknown_rights_process_creates_d13():
    data_map = stored_map()
    result = review_data_map(data_map, [activity(data_map, "unknown")])
    observation = next(item for item in result if item.code == "D13")
    assert observation.topic == "Derechos"
    assert observation.action == "Aclara quién respondería y qué pasos seguiría ante una solicitud."


def test_rights_review_rules_are_mutually_exclusive():
    data_map = stored_map()
    assert rights_codes(data_map, "case_by_case") == ["D11"]
    assert rights_codes(data_map, "none") == ["D12"]
    assert rights_codes(data_map, "unknown") == ["D13"]
