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


def activity(data_map, security_measures):
    return data_maps.StoredActivity(
        uuid4(),
        data_map.id,
        "sales",
        "own_operations",
        0,
        {
            "retention": {"status": "defined"},
            "access_roles": ["owner_only"],
            "security_measures": security_measures,
            "has_third_parties": False,
            "third_parties": [],
            "may_include_minors": False,
        },
        NOW,
        NOW,
    )


def test_catalog_exposes_plain_language_security_measures():
    measures = get_catalog()["security_measures"]
    codes = {item["code"] for item in measures}
    assert {
        "passwords_device_lock",
        "individual_accounts",
        "two_factor_auth",
        "backups",
        "updates_antivirus",
        "encryption",
        "locked_storage",
        "none",
        "unknown",
    } <= codes
    assert any(item["label"] == "No tengo medidas definidas" for item in measures)
    assert any(item["label"] == "No estoy seguro" for item in measures)


def test_security_measures_default_to_unasked_empty_list():
    assert ActivityAnswers().security_measures == []


def test_security_measures_validate_catalog_codes():
    answers = ActivityAnswers(security_measures=["passwords_device_lock", "backups"])
    assert answers.security_measures == ["passwords_device_lock", "backups"]
    with pytest.raises(ValidationError):
        ActivityAnswers(security_measures=["not-a-security-measure"])


@pytest.mark.parametrize("exclusive", ["none", "unknown"])
def test_none_and_unknown_are_exclusive_security_answers(exclusive):
    with pytest.raises(ValidationError):
        ActivityAnswers(security_measures=[exclusive, "backups"])


def test_unasked_security_does_not_create_an_observation():
    data_map = stored_map()
    result = review_data_map(data_map, [activity(data_map, [])])
    assert not any(item.code in {"D09", "D10"} for item in result)


def test_security_unknown_creates_d09():
    data_map = stored_map()
    result = review_data_map(data_map, [activity(data_map, ["unknown"])])
    observation = next(item for item in result if item.code == "D09")
    assert observation.topic == "Seguridad"
    assert observation.action == "Aclara qué medidas protegen esta información."


def test_security_none_creates_d10():
    data_map = stored_map()
    result = review_data_map(data_map, [activity(data_map, ["none"])])
    observation = next(item for item in result if item.code == "D10")
    assert observation.topic == "Seguridad"
    assert observation.action == "Define medidas básicas para proteger esta información."


def test_known_security_measures_do_not_create_security_review():
    data_map = stored_map()
    result = review_data_map(
        data_map,
        [activity(data_map, ["passwords_device_lock", "backups"])],
    )
    assert not any(item.code in {"D09", "D10"} for item in result)
