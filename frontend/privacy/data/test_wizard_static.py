from pathlib import Path

HERE = Path(__file__).parent
HTML = (HERE / "index.html").read_text()
JS = (HERE / "wizard.js").read_text()


def test_accessible_shell_and_privacy_copy():
    assert 'lang="es"' in HTML
    assert 'aria-live="polite"' in HTML
    assert "No ingreses nombres, RUT ni datos personales" in JS
    assert 'type="${type}"' in JS


def test_catalog_and_map_contracts_are_consumed():
    assert "request('/catalog')" in JS
    assert "request('/maps',{method:'POST'" in JS
    assert "request(`/maps/${token}`)" in JS
    assert "request(`/maps/${token}/activities`)" in JS
    assert "method:'PATCH'" in JS
    assert "method:'POST'" in JS


def test_token_is_local_only_and_not_rendered():
    assert "mininode_privacy_data_token" in JS
    assert "localStorage.setItem(TOKEN_KEY,this.token)" in JS
    assert "this.shell(`${this.token}" not in JS


def test_out_of_scope_features_absent():
    lowered = (HTML + JS).lower()
    for word in ("scoring", "recommendations", "r01", "billing"):
        assert word not in lowered


def test_errors_are_friendly_and_expired_tokens_removed():
    for status in (404, 410, 422, 503):
        assert str(status) in JS
    assert "localStorage.removeItem(TOKEN_KEY)" in JS
    assert "response.json()" in JS
