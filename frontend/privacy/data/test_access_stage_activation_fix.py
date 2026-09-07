from pathlib import Path

HERE = Path(__file__).parent
HTML = (HERE / "index.html").read_text()
FIX = (HERE / "access-phase2-stage-fix.js").read_text()


def test_stage_fix_loads_after_access_controller_and_before_wizard():
    assert "access-phase2-stage-fix.js?v=199d" in HTML
    assert HTML.index("access-phase2.js") < HTML.index("access-phase2-stage-fix.js") < HTML.index("wizard.js")


def test_access_is_activated_only_after_conservation_is_reviewed():
    assert "Revisada en todas las actividades de tu mapa." in FIX
    assert "stageByTitle('Conservación')" in FIX
    assert "stageByTitle('Accesos')" in FIX
    assert "button.disabled = false" in FIX
    assert "button.dataset.phase2AccessStart" in FIX


def test_fix_runs_after_actions_rerenders_without_mutation_observer():
    assert "document.addEventListener('click', schedule, true)" in FIX
    assert "setTimeout(activateAccessStageWhenReady, 0)" in FIX
    assert "MutationObserver" not in FIX
