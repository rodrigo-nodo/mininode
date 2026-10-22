/* PW-02 operator tools: backend owns authorization and entitlement rules. */
const grantForm = document.querySelector('#grant-search-form');
const grantResults = document.querySelector('#grant-sites');
const grantStatus = document.querySelector('#grant-status');
const grantSearch = document.querySelector('#grant-search');
const overviewStatus = document.querySelector('#grant-overview-status');
const overviewRows = document.querySelector('#grant-overview-rows');
const displayedGrantSites = new Map();
let selectedGrantSiteId = null;
let lastGrantHistory = [];
let overviewStarted = false;

async function grantApi(path, options = {}) {
  const auth = window.MininodeAuth;
  if (!auth) throw new Error('La sesión aún no está disponible.');
  const token = await auth.getToken();
  if (!token) throw new Error('Debes iniciar sesión en Mi espacio.');
  const response = await fetch(path, {
    ...options,
    headers: {
      Authorization: 'Bearer ' + token,
      Accept: 'application/json',
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 403) throw new Error('No tienes autorización para administrar cortesías.');
    if (response.status === 404) throw new Error('La función de cortesías no está disponible en este entorno. Verifica el despliegue del backend de dev.');
    throw new Error(typeof data.detail === 'string' ? data.detail : 'No pudimos completar la solicitud.');
  }
  return data;
}

function grantField(labelText, input) {
  const label = document.createElement('label');
  label.className = 'form-field admin-grants__field';
  input.classList.add('form-control');
  const title = document.createElement('span');
  title.className = 'form-label';
  title.textContent = labelText;
  label.append(title, input);
  return label;
}

function grantButton(text, type = 'button') {
  const button = document.createElement('button');
  button.type = type;
  button.textContent = text;
  button.className = 'btn btn--secondary';
  return button;
}

function grantDate(value) {
  return value ? new Date(value).toLocaleDateString('es-CL', { timeZone: 'America/Santiago' }) : 'Sin vencimiento';
}

function grantState(item) {
  if (item.status === 'revoked') return 'Revocada';
  if (item.status !== 'active') return 'No vigente';
  if (new Date(item.active_from) > new Date()) return 'Programada';
  if (item.active_until && new Date(item.active_until) <= new Date()) return 'Vencida';
  return 'Vigente';
}

function normalizeGrantSearch(value) {
  const trimmed = value.trim();
  if (!trimmed) return '';
  try {
    const candidate = trimmed.includes('://') ? trimmed : 'https://' + trimmed;
    return new URL(candidate).hostname.toLowerCase();
  } catch (_error) {
    return trimmed.toLowerCase();
  }
}

function confirmationCopy(site, days, reason, periods) {
  const now = new Date();
  const endDates = periods
    .filter(item => item.status === 'active' && item.active_until && new Date(item.active_until) > now)
    .map(item => new Date(item.active_until));
  const start = endDates.length ? new Date(Math.max(now.getTime(), ...endDates.map(d => d.getTime()))) : now;
  const end = new Date(start.getTime() + days * 24 * 60 * 60 * 1000);
  return 'Confirmar cortesía de Privacy Web\n\nSitio: ' + site.hostname +
    '\nEspacio: ' + site.workspace + '\nTitular: ' + (site.owner_emails || 'Sin titular registrado') + '\nDuración: ' + days + ' días' +
    '\nMotivo: ' + reason + '\nInicio estimado: ' + grantDate(start) +
    '\nTérmino estimado: ' + grantDate(end) +
    '\n\nLas fechas definitivas las determina el servidor al registrar. ¿Confirmar?';
}

async function loadGrantOverview() {
  overviewStatus.textContent = 'Cargando cortesías registradas…';
  try {
    const data = await grantApi('/api/access/operator/grants/overview');
    document.querySelector('#grant-current').textContent = data.totals.current;
    document.querySelector('#grant-scheduled').textContent = data.totals.scheduled;
    document.querySelector('#grant-historical').textContent = data.totals.historical;
    overviewRows.replaceChildren();
    if (!data.courtesies.length) {
      const tr = document.createElement('tr');
      const td = document.createElement('td');
      td.colSpan = 6;
      td.textContent = 'Todavía no hay cortesías registradas.';
      tr.append(td);
      overviewRows.append(tr);
    }
    // Keep each site/workspace together; current access before scheduled access.
    const stateRank = { Vigente: 0, Programada: 1, Vencida: 2, Revocada: 3, 'No vigente': 4 };
    const ordered = [...data.courtesies].sort((a, b) =>
      a.hostname.localeCompare(b.hostname, 'es') ||
      a.workspace.localeCompare(b.workspace, 'es') ||
      a.workspace_site_id.localeCompare(b.workspace_site_id) ||
      (stateRank[grantState(a)] ?? 5) - (stateRank[grantState(b)] ?? 5) ||
      (Date.parse(b.active_until || 0) - Date.parse(a.active_until || 0))
    );
    for (const item of ordered) {
      const tr = document.createElement('tr');
      for (const [label, value] of [['Sitio', item.hostname], ['Espacio', item.workspace], ['Titular', item.owner_emails || 'Sin titular registrado'], ['Estado', grantState(item)], ['Vencimiento', grantDate(item.active_until)]]) {
        const td = document.createElement('td');
        td.dataset.label = label;
        td.textContent = value;
        tr.append(td);
      }
      const cell = document.createElement('td');
      cell.dataset.label = 'Acción';
      const open = grantButton('Administrar');
      open.addEventListener('click', () => selectGrantSite({
        id: item.workspace_site_id, hostname: item.hostname, workspace: item.workspace, owner_emails: item.owner_emails,
      }));
      cell.append(open);
      tr.append(cell);
      overviewRows.append(tr);
    }
    overviewStatus.textContent = 'Cortesías actualizadas.';
  } catch (error) {
    overviewStatus.textContent = error.message;
    overviewRows.replaceChildren();
  }
}

async function selectGrantSite(site) {
  displayedGrantSites.set(site.id, site);
  selectedGrantSiteId = site.id;
  grantResults.replaceChildren();
  const container = document.createElement('article');
  container.className = 'card admin-grants__site';
  grantResults.append(container);
  try {
    await showGrantSite(site, container);
  } catch (error) {
    grantStatus.textContent = error.message;
  }
}

async function showGrantSite(site, container) {
  container.replaceChildren();
  const heading = document.createElement('h4');
  heading.textContent = site.hostname;
  const workspace = document.createElement('p');
  workspace.className = 'admin-grants__workspace';
  workspace.textContent = 'Espacio: ' + site.workspace + ' · Titular: ' + (site.owner_emails || 'Sin titular registrado');
  const history = document.createElement('div');
  history.className = 'admin-grants__history';
  const form = document.createElement('form');
  form.className = 'admin-grants__form';
  const days = document.createElement('input');
  days.type = 'number';
  days.min = '1';
  days.max = '365';
  days.value = '30';
  days.required = true;
  const reason = document.createElement('input');
  reason.placeholder = 'Motivo de la cortesía';
  reason.required = true;
  reason.minLength = 3;
  reason.maxLength = 1000;
  const submit = grantButton('Conceder cortesía', 'submit');
  const actions = document.createElement('div');
  actions.className = 'operator-actions';
  actions.append(submit);
  const grantNotice = document.createElement('p');
  grantNotice.className = 'admin-grants__notice';
  grantNotice.setAttribute('role', 'status');
  form.append(grantField('Duración (días)', days), grantField('Motivo', reason), actions, grantNotice);

  const refresh = async () => {
    const data = await grantApi('/api/access/operator/grant-sites/' + encodeURIComponent(site.id));
    lastGrantHistory = data.entitlements;
    history.replaceChildren();
    const current = data.entitlements.some(item => item.status === 'active' && item.active_until && new Date(item.active_until) > new Date());
    const scheduled = data.entitlements.find(item => grantState(item) === 'Programada');
    const indefinite = data.entitlements.some(item => item.status === 'active' && !item.active_until);
    submit.textContent = current ? 'Extender cortesía' : 'Conceder cortesía';
    submit.disabled = Boolean(scheduled || indefinite);
    grantNotice.textContent = scheduled
      ? 'No se puede extender todavía. Este sitio ya tiene una cortesía o acceso programado del ' + grantDate(scheduled.active_from) + ' al ' + grantDate(scheduled.active_until) + '.'
      : indefinite ? 'No se puede conceder otra cortesía: este sitio tiene acceso sin vencimiento.' : '';
    if (!data.entitlements.length) {
      const empty = document.createElement('p');
      empty.textContent = 'Este sitio no tiene accesos registrados.';
      history.append(empty);
    }
    for (const item of data.entitlements) {
      const record = document.createElement('div');
      record.className = 'admin-grants__period';
      const summary = document.createElement('p');
      const origin = item.source === 'internal_grant' ? 'Cortesía' : 'Acceso pagado';
      const state = grantState(item);
      summary.textContent = origin + ' · ' + state + ' · ' +
        grantDate(item.active_from) + ' → ' + grantDate(item.active_until) +
        (item.last_reason ? ' · ' + item.last_reason : '');
      record.append(summary);
      if (item.source === 'internal_grant' && item.status === 'active' && state !== 'Vencida') {
        const revokeReason = document.createElement('input');
        revokeReason.required = true;
        revokeReason.minLength = 3;
        revokeReason.maxLength = 1000;
        revokeReason.placeholder = 'Motivo de revocación';
        const revoke = grantButton('Revocar cortesía');
        revoke.addEventListener('click', async () => {
          if (revokeReason.value.trim().length < 3) {
            grantStatus.textContent = 'Indica un motivo de revocación de al menos 3 caracteres.';
            return;
          }
          const question = 'Revocar cortesía de Privacy Web\n\nSitio: ' + site.hostname +
            '\nEspacio: ' + site.workspace + '\nTitular: ' + (site.owner_emails || 'Sin titular registrado') + '\nMotivo: ' + revokeReason.value.trim() +
            '\nVencimiento actual: ' + grantDate(item.active_until) +
            '\n\n¿Confirmar revocación?';
          if (!window.confirm(question)) return;
          revoke.disabled = true;
          try {
            await grantApi('/api/access/operator/grants/' + encodeURIComponent(item.id) + '/revoke', {
              method: 'POST', body: JSON.stringify({ reason: revokeReason.value.trim() }),
            });
            grantStatus.textContent = 'Cortesía revocada.';
            await refresh();
            await loadGrantOverview();
          } catch (error) {
            grantStatus.textContent = error.message;
            revoke.disabled = false;
          }
        });
        const revokeActions = document.createElement('div');
        revokeActions.className = 'operator-actions';
        revokeActions.append(revoke);
        record.append(grantField('Motivo de revocación', revokeReason), revokeActions);
      }
      history.append(record);
    }
  };
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (submit.disabled) return;
    const daysValue = Number(days.value);
    if (!Number.isInteger(daysValue) || daysValue < 1 || daysValue > 365 || reason.value.trim().length < 3) {
      grantStatus.textContent = 'Indica entre 1 y 365 días y un motivo de al menos 3 caracteres.';
      return;
    }
    if (!window.confirm(confirmationCopy(site, daysValue, reason.value.trim(), lastGrantHistory))) return;
    submit.disabled = true;
    try {
      await grantApi('/api/access/operator/grants', {
        method: 'POST',
        body: JSON.stringify({ workspace_site_id: site.id, days: daysValue, reason: reason.value.trim() }),
      });
      grantStatus.textContent = 'Cortesía registrada.';
      reason.value = '';
      await refresh();
      await loadGrantOverview();
    } catch (error) {
      const conflict = /período futuro reservado/i.test(error.message);
      grantStatus.textContent = conflict
        ? 'No se puede extender todavía. Este sitio ya tiene una cortesía o acceso programado; revisa su historial.'
        : error.message;
      if (conflict) await refresh();
    } finally {
      if (!grantNotice.textContent) submit.disabled = false;
    }
  });
  const headingHistory = document.createElement('h5');
  headingHistory.textContent = 'Historial de accesos';
  container.append(heading, workspace, form, headingHistory, history);
  await refresh();
}

grantForm.addEventListener('submit', async event => {
  event.preventDefault();
  const button = grantForm.querySelector('button');
  button.disabled = true;
  grantStatus.textContent = 'Buscando sitios…';
  try {
    const data = await grantApi('/api/access/operator/grant-sites?q=' + encodeURIComponent(normalizeGrantSearch(grantSearch.value)));
    if (!data.sites.length) {
      grantStatus.textContent = 'No hay sitios asociados a espacios para ese dominio.';
      return;
    }
    grantStatus.textContent = data.sites.length + ' sitio(s) encontrado(s). Selecciona el espacio correcto.';
    // Same hostname in different workspaces remains distinct via workspace-site ID.
    if (data.sites.length === 1) {
      await selectGrantSite(data.sites[0]);
    } else {
      grantResults.replaceChildren();
      for (const site of data.sites) {
        const select = grantButton(site.hostname + ' · ' + site.workspace + ' · ' + (site.owner_emails || 'Sin titular registrado'));
        select.addEventListener('click', () => selectGrantSite(site));
        grantResults.append(select);
      }
    }
  } catch (error) {
    grantStatus.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});

// Do not read operator-only data before the existing admin access gate opens.
const grantAdminOperations = document.querySelector('#admin-operations');
function startGrantOverview() {
  if (overviewStarted || grantAdminOperations.hidden) return;
  overviewStarted = true;
  loadGrantOverview();
}
const grantGateObserver = new MutationObserver(startGrantOverview);
grantGateObserver.observe(grantAdminOperations, { attributes: true, attributeFilter: ['hidden'] });
startGrantOverview();
