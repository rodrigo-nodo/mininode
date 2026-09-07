from pathlib import Path

HERE = Path(__file__).parent
HTML = (HERE / "index.html").read_text()
RESUME = (HERE / "resume-map.js").read_text()


def test_completed_map_reentry_controller_is_loaded_before_wizard():
    assert "resume-map.js?v=199f" in HTML
    assert HTML.index("resume-map.js") < HTML.index("wizard.js")


def test_reentry_requires_phase_one_completion():
    for field in [
        "people_categories",
        "personal_data_types",
        "purposes",
        "data_origins",
        "storage_locations",
    ]:
        assert field in RESUME
    assert "may_include_minors == null" in RESUME
    assert "has_third_parties == null" in RESUME
    assert "data_context === 'unconfirmed'" in RESUME
    assert "third.relationships" in RESUME


def test_completed_map_opens_existing_result_without_saving():
    assert "triggerWizardAction('retention-back')" in RESUME
    assert "triggerWizardAction('result-map')" in RESUME
    assert "method: 'PATCH'" not in RESUME
    assert "POST" not in RESUME


def test_incomplete_or_unavailable_maps_remain_owned_by_wizard():
    assert "if (!phaseOneComplete(activities)) return" in RESUME
    assert "The wizard owns recovery/error handling" in RESUME
