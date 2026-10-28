import json
import re
import subprocess
import unittest
from pathlib import Path


PRIVACY_DIR = Path(__file__).parent
FRONTEND_DIR = PRIVACY_DIR.parent
APP = (PRIVACY_DIR / "app.js").read_text(encoding="utf-8")
HTML = (PRIVACY_DIR / "index.html").read_text(encoding="utf-8")
CSS = (PRIVACY_DIR / "styles.css").read_text(encoding="utf-8")
DATA_HTML = (PRIVACY_DIR / "data" / "index.html").read_text(encoding="utf-8")
HOME_HTML = (PRIVACY_DIR.parent / "index.html").read_text(encoding="utf-8")
REDIRECTS = (FRONTEND_DIR / "_redirects").read_text(encoding="utf-8")
CORE_AUTH = (FRONTEND_DIR / "assets" / "js" / "core-auth.js").read_text(encoding="utf-8")


class PrivacyResultStaticTests(unittest.TestCase):
    def test_all_21_controls_have_one_shared_ux_name_and_description(self):
        ux_source = (PRIVACY_DIR / "control-ux.js").read_text(encoding="utf-8")
        result = subprocess.run(
            ["node", "-e", "globalThis.window = {};\n"
             + ux_source + "\nprocess.stdout.write(JSON.stringify(window.MininodePrivacyControlUX.entries));"],
            text=True, capture_output=True, check=True,
        )
        entries = json.loads(result.stdout)
        technical = json.loads((FRONTEND_DIR.parent /
            "backend/src/mininode_api/domain_packs/privacy/controls.json").read_text(encoding="utf-8"))
        expected_codes = {control["code"] for control in technical["controls"]}
        self.assertEqual(len(expected_codes), 21)
        self.assertEqual(set(entries), expected_codes)
        for code, entry in entries.items():
            self.assertEqual(set(entry), {"name", "description"})
            self.assertTrue(entry["name"].strip(), code)
            self.assertTrue(entry["description"].strip(), code)
        # The technical framework contract remains separate from customer copy.
        self.assertNotIn("result:", ux_source)

    def test_all_control_views_load_the_shared_catalog_before_renderers(self):
        pages = (
            ("index.html", 'src="app.js?v=ux21-priorities-2"'),
            ("plan/index.html", 'src="/privacy/plan-assets/app.js?v=c4b-1"'),
            ("plan-demo/index.html", 'src="app.js?v=ux21-1"'),
        )
        for page, renderer in pages:
            html = (PRIVACY_DIR / page).read_text(encoding="utf-8")
            self.assertLess(html.index("control-ux.js?v=ux21-1"), html.index(renderer))
        for path in ("app.js", "plan-assets/app.js", "plan-demo/app.js"):
            script = (PRIVACY_DIR / path).read_text(encoding="utf-8")
            self.assertIn("MininodePrivacyControlUX", script)
            self.assertNotIn("displayNames", script)
        plan = (PRIVACY_DIR / "plan-assets/app.js").read_text(encoding="utf-8")
        self.assertIn("description(item.control_code)", plan)
        self.assertIn("name(item.control_code, item.name)", plan)
        self.assertIn("control.code, control.name", APP)
        self.assertIn("description(control.code)", APP)


    def test_free_priority_renderer_regression(self):
        # Exercise the actual priority renderer without unrelated auth/commercial paths.
        result = subprocess.run(
            ["node", "--test", str(PRIVACY_DIR / "test_priority_ux.mjs")],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_priorities_use_shared_ux_catalog_for_known_codes(self):
        self.assertIn(
            "window.MininodePrivacyControlUX?.name(priority.control_code, priority.name || 'Acción prioritaria')",
            APP,
        )
        self.assertNotIn(
            "appendTextElement(content, 'h4', priority.name || 'Acción prioritaria')",
            APP,
        )

    def test_priorities_heading_tracks_visible_count(self):
        self.assertIn('id="actions-title">Acciones prioritarias</h3>', HTML)
        self.assertIn("const actionsTitle = document.querySelector('#actions-title');", APP)
        self.assertIn("const count = visiblePriorities.length;", APP)
        self.assertIn("count === 0 ? 'Sin acciones prioritarias'", APP)
        self.assertIn("count === 1 ? 'cosa que haría primero' : 'cosas que haría primero'", APP)
        self.assertIn(".slice(0, 3)", APP)
        self.assertIn('src="app.js?v=ux21-priorities-2"', HTML)


    def test_continuation_layout_uses_current_local_styles_and_equal_actions(self):
        self.assertIn('href="styles.css?v=ux21-1"', HTML)
        self.assertIn('class="btn privacy-secondary privacy-choice-button"', HTML)
        self.assertEqual(HTML.count('class="btn privacy-secondary privacy-choice-button"'), 4)
        self.assertIn("#privacy-correction-offer .privacy-next", CSS)
        self.assertIn("#privacy-correction-offer .privacy-save-choice", CSS)
        self.assertIn("grid-template-columns: minmax(0, 1fr) 148px", CSS)
        self.assertIn("background: var(--privacy-primary)", CSS)
        self.assertIn("@media (max-width: 620px)", CSS)
        summary = HTML.split('class="privacy-next__summary"', 1)[1].split('class="privacy-next__action"', 1)[0]
        self.assertIn('class="privacy-offer-details"', summary)

    def test_saved_review_copy_identifies_exact_analyzed_hostname(self):
        self.assertIn('app.js?v=ux21-priorities-2', HTML)
        self.assertIn('id="privacy-saved-note-description"', HTML)
        self.assertIn('id="privacy-saved-standalone-description"', HTML)
        self.assertNotIn('Este resultado ya está en tu espacio Mininode.', HTML)
        self.assertIn("new URL(diagnostic.site_url || websiteUrl).hostname", APP)
        self.assertIn("La última revisión de ${reviewHostname} está disponible en tu espacio Mininode.", APP)
        self.assertIn("savedNoteDescription.textContent = savedReviewDescription;", APP)
        self.assertIn("savedStandaloneDescription.textContent = savedReviewDescription;", APP)

    def test_saved_and_anonymous_result_states_are_distinct(self):
        # A workspace-linked review is already saved even though it has no claim token.
        self.assertIn('id="privacy-saved-note"', HTML)
        self.assertIn('id="privacy-saved-standalone"', HTML)
        self.assertIn('id="privacy-activation-notice"', HTML)
        self.assertIn("const isSaved = Boolean(currentPersistedWorkspaceSiteId);", APP)
        self.assertIn("const canClaim = Boolean(currentDiagnosticId && currentClaimToken && !isSaved);", APP)
        self.assertIn("savedSiteId || authenticatedWorkspaceSiteId", APP)
        self.assertIn("saveDiagnosticNote.hidden = !hasOffer || !canClaim;", APP)
        self.assertIn("savedDiagnosticNote.hidden = !hasOffer || !isSaved;", APP)
        self.assertIn("savedStandaloneNote.hidden = hasOffer || !isSaved;", APP)
        self.assertIn("if (intent === 'activate' && currentPersistedWorkspaceSiteId)", APP)
        self.assertIn("void prepareActivationForSavedSite();", APP)
        self.assertIn("Estamos actualizando el diagnóstico de tu sitio antes de continuar.", APP)
        self.assertIn("prepare-activation", APP)
        self.assertIn("const verifyEntitlementForSavedSite = async (siteId, knownToken = null) => {", APP)
        self.assertIn("showEntitlementLookupError()", APP)
        self.assertIn("Reintentar acceso →", APP)
        self.assertNotIn("Disponible para activar durante 24 horas", APP)
        self.assertNotIn("Disponible para activar durante 24 horas", HTML)
        self.assertIn("activationNotice.hidden = false;", APP)
        self.assertNotIn("intent === 'activate' && !currentClaimToken && authenticatedWorkspaceSiteId", APP)
        self.assertIn("privacyQuery.get('activation') === 'pending'", APP)
        self.assertIn("privacy-saved-choice[hidden]", CSS)

    def test_access_auto_saves_pending_diagnostic_after_login(self):
        account = (FRONTEND_DIR / "access" / "app.js").read_text(encoding="utf-8")
        self.assertIn("if (pending && !pendingWorkspaceChoice) void savePendingDiagnostic();", account)
        self.assertIn("workspaces.length > 1", account)
        self.assertIn("Selecciona un espacio para guardar", account)
        self.assertIn("if (sessionStorage.getItem(PENDING_CLAIM_KEY))", account)
        self.assertIn("void savePendingDiagnostic();", account)
        self.assertIn("if (claimInFlight) return;", account)
        self.assertIn("workspacePicker.disabled = true;", account)
        self.assertIn("workspacePicker.disabled = false;", account)
        self.assertIn("if (claimTitle) claimTitle.textContent = 'Guardando tu diagnóstico…';", account)
        self.assertIn("sessionStorage.removeItem(PENDING_CLAIM_KEY);", account)
        self.assertIn("Reintentar guardado", account)

    def test_free_claim_payload_exactly_matches_forbidden_extra_backend_contract(self):
        # Prevent reintroducing '...claim': intent is browser state, not a backend field.
        account = (FRONTEND_DIR / "access" / "app.js").read_text(encoding="utf-8")
        request = re.search(
            r"api\('/api/privacy/diagnostic-claims',\s*\{.*?JSON\.stringify\(\{(.*?)\}\)",
            account, re.S,
        )
        self.assertIsNotNone(request)
        frontend_fields = set(re.findall(r"^\s*(\w+)\s*:", request.group(1), re.M))
        api_source = (FRONTEND_DIR.parent / "backend" / "src" / "mininode_api" / "api" / "privacy.py").read_text(encoding="utf-8")
        model = api_source.split("class ClaimAnonymousDiagnosticRequest(BaseModel):", 1)[1].split(
            "class ClaimedDiagnosticResponse(BaseModel):", 1
        )[0]
        backend_fields = set(re.findall(r"^    (\w+):", model, re.M))
        self.assertEqual(frontend_fields, {"diagnostic_id", "workspace_id", "claim_token"})
        self.assertEqual(frontend_fields, backend_fields)
        self.assertIn('ConfigDict(extra="forbid")', model)
        self.assertIn("if (claim.intent === 'activate')", account)

    def test_saved_result_has_same_row_and_cta_as_free_save(self):
        self.assertEqual(HTML.count('class="privacy-saved-choice__summary"'), 2)
        self.assertEqual(HTML.count('class="btn privacy-secondary privacy-choice-button" href="/access/"'), 2)
        self.assertEqual(HTML.count('Mis sitios →'), 2)
        self.assertIn("#privacy-correction-offer .privacy-saved-choice", CSS)
        self.assertIn("grid-template-columns: minmax(0, 1fr) 148px", CSS)
        self.assertIn(".privacy-saved-choice--standalone .btn.privacy-choice-button { width: 100%; }", CSS)

    def test_saved_result_is_preserved_and_pending_activation_prepares_fresh_diagnosis(self):
        self.assertIn("const prepareActivationForSavedSite = async () => {", APP)
        self.assertIn("await prepareActivationForSavedSite();", APP)
        self.assertIn("if (entitlementVerified && privacyQuery.get('activation') === 'pending' && !activePrivacyEntitlement && !correctionOffer.hidden)", APP)
        self.assertIn("if (prepared.refreshed)", APP)
        self.assertIn("renderDiagnostic(prepared.diagnostic", APP)
        self.assertNotIn("if (purchaseExpired && !correctionOffer.hidden)", APP)

    def test_commercial_notice_appears_only_inside_conditions(self):
        intro = HTML.split('class="privacy-offer-details"', 1)[0]
        self.assertNotIn("Sin renovación automática. El pago en línea", intro)
        detail = HTML.split('class="privacy-offer-details"', 1)[1].split("</details>", 1)[0]
        self.assertIn("El pago en línea estará disponible próximamente.", detail)
        self.assertIn("Sin renovación automática.", detail)

    def test_free_anonymous_diagnostic_save_flow(self):
        account = (FRONTEND_DIR / "access" / "app.js").read_text(encoding="utf-8")
        account_html = (FRONTEND_DIR / "access" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="privacy-save-diagnostic"', HTML)
        self.assertIn('id="privacy-save-standalone-button"', HTML)
        self.assertIn('id="privacy-next-steps"', HTML)
        self.assertIn('¿Cómo quieres continuar?', HTML)
        self.assertIn('<summary>Ver qué incluye y condiciones</summary>', HTML)
        self.assertIn('Guardar diagnóstico gratis', HTML)
        self.assertIn('El pago en línea estará disponible próximamente.', HTML)
        self.assertNotIn('Opción principal · Privacy Web activo', HTML)
        self.assertIn('nextSteps.hidden = !hasOffer && saveStandalone.hidden && savedStandaloneNote.hidden;', APP)
        self.assertIn('id="pending-claim-button"', account_html)
        self.assertIn("diagnostic.claim_token", APP)
        self.assertIn("sessionStorage.setItem(PENDING_CLAIM_KEY", APP)
        self.assertIn("sessionStorage.getItem(PENDING_CLAIM_KEY)", account)
        self.assertIn("'/api/privacy/diagnostic-claims'", account)
        self.assertIn("workspace_id: activeWorkspaceId", account)
        self.assertIn("sessionStorage.removeItem(PENDING_CLAIM_KEY)", account)
        self.assertIn("showSavedDiagnosticConfirmation(saved.workspace_site_id)", account)
        self.assertIn("claimSuccessResult.href = `/privacy/?workspace_site_id=", account)
        self.assertIn("&view=latest`;", account)
        self.assertIn("if (claim.intent === 'activate')", account)
        self.assertIn("renderPriorities(diagnostic.priorities)", APP)
        self.assertIn("renderCommercialOffer(diagnostic.priorities)", APP)
        self.assertNotIn("payment_confirmed", account)

    def test_authenticated_workspace_site_entry_uses_access_identity(self):
        self.assertNotIn('data-clerk-publishable-key="pk_test_', HTML)
        self.assertNotIn('clerk.accounts.dev', HTML)
        self.assertNotIn("fetch('/clerk-config'", APP)
        self.assertNotIn("@clerk/", APP)
        self.assertNotIn("Clerk.", APP)
        self.assertIn("window.MininodeAuth = api", CORE_AUTH)
        self.assertIn("fetch('/clerk-config'", CORE_AUTH)
        self.assertIn("publishableKey.startsWith('pk_live_')", CORE_AUTH)
        self.assertIn("waitForMininodeAuth", APP)
        self.assertIn("auth.getToken()", APP)
        self.assertIn("get('workspace_site_id')", APP)
        self.assertIn("fetch('/api/access/context'", APP)
        self.assertIn('/api/privacy/workspace-sites/', APP)
        self.assertIn('encodeURIComponent(authenticatedWorkspaceSiteId)', APP)
        self.assertIn('Authorization: `Bearer ${token}`', APP)
        self.assertIn('urlInput.readOnly = true', APP)
        self.assertIn("fetch('/api/privacy/diagnose'", APP)

    def test_authenticated_free_diagnosis_auto_associates_site_to_workspace(self):
        self.assertIn("get('workspace_id')", APP)
        self.assertIn("resolveWorkspaceForDiagnosis", APP)
        self.assertIn("fetch('/api/access/context'", APP)
        self.assertIn("fetch('/api/access/onboarding'", APP)
        self.assertIn("/api/privacy/workspaces/", APP)
        self.assertIn("JSON.stringify({ url: websiteUrl })", APP)
        self.assertIn("workspace_selection_required", APP)
        self.assertIn("Selecciona el espacio desde tu cuenta", APP)


    def test_account_latest_review_can_be_reopened_without_rerunning_diagnosis(self):
        self.assertIn("privacyQuery.get('view') === 'latest'", APP)
        self.assertIn("/latest-review", APP)
        self.assertIn("requestedLatestReview", APP)
        self.assertIn("renderDiagnostic(latestDiagnostic", APP)
        self.assertIn("resultCard.hidden = false", APP)

    def test_signed_out_diagnosis_keeps_public_endpoint(self):
        self.assertIn("if (!token) return null;", APP)
        self.assertIn("fetch('/api/privacy/diagnose'", APP)

    def test_obsolete_complete_diagnosis_offer_is_removed(self):
        obsolete_dir = PRIVACY_DIR / "diagnostico-completo"
        self.assertFalse((obsolete_dir / "index.html").exists())
        self.assertFalse((obsolete_dir / "styles.css").exists())

        productive_files = [
            path for path in FRONTEND_DIR.rglob("*")
            if path.is_file() and path.suffix in {".html", ".js", ".css"}
        ]
        productive_content = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for path in productive_files
        )
        self.assertNotIn("/privacy/diagnostico-completo/", productive_content)
        self.assertNotIn("$39.900", productive_content)
        self.assertIn("$9.900", HTML)
        self.assertTrue((PRIVACY_DIR / "index.html").is_file())
        self.assertTrue((PRIVACY_DIR / "plan" / "index.html").is_file())

        rules = [line.split() for line in REDIRECTS.splitlines() if line.strip()]
        obsolete_redirect = [
            "/privacy/diagnostico-completo/", "/privacy/", "301"
        ]
        plan_rewrite = ["/privacy/plan/:token", "/privacy/plan/", "200"]
        self.assertIn(obsolete_redirect, rules)
        self.assertIn(plan_rewrite, rules)
        self.assertLess(rules.index(obsolete_redirect), rules.index(plan_rewrite))
        self.assertTrue((FRONTEND_DIR / "functions" / "api" / "[[path]].js").is_file())

    def test_human_status_uses_backend_score_boundaries(self):
        function = re.search(
            r"const getHumanStatus = \(score\) => \{.*?\n\};",
            APP,
            re.DOTALL,
        ).group()
        boundaries = [0, 39, 40, 69, 70, 84, 85, 100]
        script = f"{function}\nconsole.log(JSON.stringify({boundaries}.map(getHumanStatus)));"
        result = subprocess.run(
            ["node", "-e", script],
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertEqual(json.loads(result.stdout), [
            "Hay aspectos importantes por mejorar",
            "Hay aspectos importantes por mejorar",
            "Hay aspectos que puedes mejorar",
            "Hay aspectos que puedes mejorar",
            "Bien",
            "Bien",
            "Bien",
            "Bien",
        ])

    def test_human_status_does_not_interpret_backend_status_text(self):
        function = APP.split("const getHumanStatus", 1)[1].split("const renderPriorities", 1)[0]

        self.assertNotIn("status", function)
        self.assertNotIn("includes", function)
        self.assertIn("getHumanStatus(score)", APP)

    def test_configures_the_complete_matrix_in_five_areas(self):
        config = APP.split("const privacyAreas = [", 1)[1].split("const resultLabels", 1)[0]
        codes = re.findall(r"code: '(PRV-\d+)'", config)

        self.assertEqual(len(codes), 19)
        self.assertEqual(len(set(codes)), 19)
        self.assertEqual(config.count("name: 'Transparencia'"), 1)
        self.assertEqual(config.count("name: 'Formularios'"), 1)
        self.assertEqual(config.count("name: 'Cookies'"), 1)
        self.assertEqual(config.count("name: 'Contacto'"), 1)
        self.assertEqual(config.count("name: 'Seguridad'"), 1)
        self.assertEqual(config.count("name: '") - 19, 5)
        self.assertEqual(len(re.findall(r"PRV-0\d\d", config)), 14)
        self.assertEqual(len(re.findall(r"PRV-10[14]", config)), 2)
        self.assertEqual(config.count("PRV-201"), 1)
        self.assertEqual(config.count("PRV-301"), 1)
        self.assertEqual(config.count("PRV-501"), 1)

    def test_area_information_uses_one_accessible_reusable_modal(self):
        area_info = APP.split("const AREA_INFO = {", 1)[1].split("const resultLabels", 1)[0]

        self.assertEqual(HTML.count('role="dialog"'), 1)
        self.assertEqual(HTML.count('id="privacy-modal-content"'), 1)
        self.assertEqual(HTML.count("Qué revisamos"), 0)
        for area in ("Transparencia", "Formularios", "Cookies", "Contacto", "Seguridad"):
            self.assertIn(f"{area}: {{", area_info)
        self.assertEqual(area_info.count("what:"), 5)
        self.assertEqual(area_info.count("why:"), 5)
        self.assertEqual(area_info.count("basis:"), 5)
        self.assertIn("appendModalBlock('Qué revisamos', info.what)", APP)
        self.assertIn("appendModalBlock('Por qué importa', info.why)", APP)
        self.assertIn("appendModalBlock('Fundamento normativo', info.basis, 'secondary')", APP)
        self.assertIn("appendTextElement(areaSummary, 'button'", APP)
        self.assertIn("Información sobre el área ${area.name}", APP)
        self.assertIn("areaInfoButton.type = 'button'", APP)
        self.assertNotIn("W2.1", APP)

    def test_context_controls_are_informational(self):
        self.assertRegex(APP, r"code: 'PRV-004'.*informational: true")
        self.assertRegex(APP, r"code: 'PRV-009'.*informational: true")
        self.assertIn("Informativo · no afecta el resultado", APP)
        self.assertIn("'privacy-control__note'", APP)
        self.assertIn(".privacy-control__note", CSS)
        self.assertIn("color: var(--color-muted);", CSS)

    def test_control_detail_typographic_hierarchy(self):
        self.assertRegex(CSS, r"\.privacy-control-area h4 \{[^}]*font-weight: 700;")
        self.assertRegex(CSS, r"\.privacy-control__name \{[^}]*font-weight: 400;")
        self.assertRegex(CSS, r"\.privacy-controls \{[^}]*gap: var\(--space-8\);")

    def test_all_backend_results_have_human_labels(self):
        expected = {
            "detected": "Bien",
            "partial": "Puede mejorar",
            "not_detected": "Necesita atención",
            "not_evaluable": "No pudimos revisarlo",
            "not_applicable": "No aplica",
        }
        for result, label in expected.items():
            self.assertRegex(APP, rf"{result}: {{ label: '{label}'")

    def test_result_ui_hides_codes_and_technical_coverage(self):
        self.assertNotIn("PRV-", HTML)
        self.assertNotIn("diagnostic-coverage", HTML)
        self.assertIn("Ver qué revisamos", HTML)
        self.assertIn("19 puntos en 5 áreas", HTML)

    def test_priorities_and_commercial_paths_are_preserved(self):
        self.assertIn(".slice(0, 3)", APP)
        self.assertIn("Array.isArray(priorities) && priorities.length > 0", APP)
        self.assertNotIn("Plan de corrección", HTML)
        self.assertIn("$9.900", HTML)
        self.assertNotIn("$49.900", HTML)
        self.assertIn("nuevas revisiones durante un mes.", HTML)
        self.assertNotIn("pago único", HTML)
        self.assertIn("Vigencia de 1 mes desde la compra. Sin renovación automática.", HTML)
        self.assertIn("Accede a todas las mejoras, instrucciones para corregirlas y nuevas revisiones durante un mes.", HTML)
        self.assertIn("Todas las mejoras detectadas", HTML)
        self.assertIn("Instrucciones concretas para cada mejora", HTML)
        self.assertIn("Cómo comprobar los cambios", HTML)
        self.assertIn("Comparación antes/después", HTML)
        self.assertIn("Seguimiento de tus avances", HTML)
        self.assertNotIn("1 comprobación", HTML)
        self.assertNotIn("30 días", HTML)
        self.assertIn('id="correction-order-open">Continuar →</button>', HTML)
        self.assertIn("sin desbloquear las demás mejoras ni incluir nuevas revisiones.", HTML)
        self.assertIn("continueWithDiagnostic('activate')", APP)
        self.assertIn("continueWithDiagnostic('save')", APP)
        account = (FRONTEND_DIR / "access" / "app.js").read_text(encoding="utf-8")
        self.assertIn("claim.intent === 'activate'", account)
        self.assertEqual(HTML.count("Vigencia de 1 mes desde la compra. Sin renovación automática."), 2)
        self.assertIn('id="correction-order-validity"', HTML)
        self.assertIn('id="correction-order-expired-validity"', HTML)
        self.assertNotIn("6 meses", HTML)
        self.assertNotIn("suscripción automática", HTML.lower())
        self.assertNotIn("billing", HTML.lower())
        self.assertIn('name="email"', HTML)
        self.assertIn("Se utilizará para gestionar la activación y entregar el acceso.", HTML)
        self.assertIn("fetch('/api/privacy/correction-plan-orders'", APP)
        self.assertIn("JSON.stringify({ diagnostic_id: diagnosticId, email: orderEmail.value })", APP)
        self.assertNotIn("site_url:", APP)
        self.assertNotIn("amount:", APP)
        self.assertNotIn("currency:", APP)
        self.assertNotIn("product_code:", APP)
        self.assertIn("Solicitud preparada", HTML)
        self.assertIn("El pago en línea estará disponible próximamente.", HTML)
        self.assertIn("Si es necesario, actualizaremos el diagnóstico antes de continuar.", HTML)
        self.assertIn("Si es necesario, actualizaremos el diagnóstico antes de continuar.", APP)
        self.assertIn("Para activar Privacy Web necesitas una revisión reciente", HTML)
        self.assertIn("Esta revisión sigue disponible.", HTML)
        self.assertIn('id="correction-order-expired-date"', HTML)
        self.assertIn("Revisar nuevamente", HTML)
        self.assertIn(".privacy-next__action > [hidden]", CSS)
        self.assertIn("display: none !important;", CSS)
        self.assertIn("background: var(--color-primary-soft);", CSS)
        self.assertNotIn("background: #f8fbfb;", CSS)
        self.assertNotIn("La ventana de activación de este diagnóstico ya finalizó.", APP)
        self.assertNotIn("Este diagnóstico tiene más de 24 horas.", HTML)
        self.assertNotIn("countdown", APP.lower())
        self.assertNotIn("recheck", APP.lower())
        self.assertNotIn("recheck_expires_at", HTML)
        self.assertNotIn("Le queda 1 revisión", HTML)
        self.assertNotIn("Solo puede volver a analizar una vez", HTML)
        self.assertIn("La implementación técnica no está incluida.", HTML)
        self.assertNotIn("acompañamiento para resolver dudas", HTML.lower())
        self.assertIn("¿Necesita ayuda para realizar los cambios?", HTML)
        self.assertIn("ese servicio se evalúa por separado", HTML)
        self.assertIn("Consultar apoyo técnico", HTML)
        self.assertIn('id="privacy-no-priorities"', HTML)

    def test_privacy_data_is_an_unconditional_next_step(self):
        self.assertIn('href="/privacy/data/">Conocer Privacy Data</a>', HTML)
        self.assertEqual(HTML.count('href="/privacy/data/"'), 1)
        self.assertIn("Próximamente", HTML)
        privacy_data = HTML.split('<section class="privacy-data-next-step"', 1)[1]
        self.assertNotIn("score", privacy_data.split("</section>", 1)[0])
        self.assertNotIn("priorities", privacy_data.split("</section>", 1)[0])

    def test_product_names_and_privacy_data_public_copy(self):
        self.assertIn('<p class="privacy-tag">Privacy Web</p>', HTML)
        self.assertNotIn("Mininode Privacy", HTML)
        self.assertIn('<form class="privacy-form" id="privacy-form">', HTML)
        self.assertIn("fetch('/api/privacy/diagnose'", APP)
        self.assertNotIn("Plan de corrección", HTML)
        self.assertIn('<span class="product-row__name">Privacy Web</span>', HOME_HTML)
        self.assertIn('<span class="product-row__name">Privacy Data</span>', HOME_HTML)
        self.assertNotIn("Mininode Privacy", HOME_HTML)
        self.assertIn('<span class="product-status">Próximamente</span>', HOME_HTML)
        self.assertIn("Ordena cómo tu negocio maneja los datos personales por dentro.", DATA_HTML)
        self.assertIn("Construye un mapa simple de dónde aparecen los datos personales en tu negocio y cómo los utilizas.", DATA_HTML)
        self.assertIn("<li>Gratis</li>", DATA_HTML)
        self.assertIn("<li>Sin registro</li>", DATA_HTML)
        self.assertNotIn("En desarrollo", HOME_HTML)
        self.assertNotIn("En desarrollo", DATA_HTML)

        for technical_name in (
            "Metadata Scanner",
            "Data Classifier",
            "Data Mapper",
            "Risk Engine",
            "Connectors",
            "Local Scanner",
        ):
            self.assertNotIn(technical_name, DATA_HTML)

    def test_order_form_minimizes_data_and_keeps_commercial_fields_server_side(self):
        order_form = HTML.split('id="correction-order-form"', 1)[1].split("</form>", 1)[0]
        self.assertEqual(order_form.count("<input"), 1)
        self.assertIn('name="email"', order_form)
        for field in ('name="name"', 'name="empresa"', 'name="rut"', 'name="telefono"', 'name="site_url"'):
            self.assertNotIn(field, order_form)

        request = APP.split("fetch('/api/privacy/correction-plan-orders'", 1)[1].split("});", 1)[0]
        self.assertIn("diagnostic_id: diagnosticId", request)
        self.assertIn("email: orderEmail.value", request)
        for field in ("site_url", "amount", "currency", "status", "product_code", "score", "snapshot"):
            self.assertNotIn(f"{field}:", request)

    def test_each_diagnosis_owns_and_resets_its_commercial_state(self):
        submit_flow = APP.split("form.addEventListener('submit'", 1)[1]
        self.assertIn("resetCommercialState();", submit_flow.split("fetch('/api/privacy/diagnose'", 1)[0])
        self.assertIn("currentDiagnosticId = '';", APP)
        self.assertIn("orderEmail.value = '';", APP)
        self.assertIn("correctionOffer.hidden = true;", APP)
        self.assertIn("const diagnosticId = currentDiagnosticId;", APP)
        self.assertIn("if (!diagnosticId || correctionOffer.hidden)", APP)

    def test_unavailable_privacy_web_has_explanatory_state_instead_of_priced_card(self):
        unavailable = HTML.split('id="privacy-correction-unavailable"', 1)[1].split('</div>', 1)[0]
        self.assertIn("Privacy Web no disponible", unavailable)
        self.assertIn("No fue posible habilitar Privacy Web para este diagnóstico.", unavailable)
        self.assertIn("Realizar nuevo diagnóstico", unavailable)
        self.assertNotIn("$49.900", unavailable)
        self.assertIn("correctionUnavailable.hidden = !hasPriorities || planAvailable;", APP)

    def test_commercial_section_uses_privacy_identity_and_approved_copy(self):
        commercial = HTML.split('id="privacy-correction-offer"', 1)[1].split('class="privacy-result__note"', 1)[0]
        styles = (PRIVACY_DIR / "styles.css").read_text(encoding="utf-8").lower()
        self.assertIn("var(--color-primary)", styles)
        self.assertNotRegex(commercial.lower(), r"violet|purple|#6c4df4")

    def test_api_and_backend_score_remain_inputs(self):
        self.assertIn("fetch('/api/privacy/diagnose'", APP)
        self.assertIn("const score = diagnostic.score;", APP)
        self.assertNotRegex(APP, r"diagnostic\.score\s*=")

    def test_app_script_is_cache_busted_with_the_result_markup(self):
        self.assertRegex(HTML, r'<script src="app\.js\?v=[^"&]+" defer></script>')

    def test_local_stylesheet_is_cache_busted(self):
        self.assertRegex(
            HTML,
            r'<link rel="stylesheet" href="styles\.css\?v=[^"&]+">',
        )

    def test_flow_errors_are_distinguished_without_exposing_internal_codes(self):
        for code in ("api_request_failed", "invalid_api_response", "render_failed"):
            self.assertIn(f"reportFlowError('{code}'", APP)
            self.assertNotIn(code, HTML)
        self.assertIn("Recibimos el diagnóstico, pero no pudimos mostrar el resultado.", APP)


if __name__ == "__main__":
    unittest.main()
