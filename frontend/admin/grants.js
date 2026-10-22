/* PW-02 operator tools: backend owns authorization and entitlement rules. */
const grantForm = document.querySelector('#grant-search-form');
const grantResults = document.querySelector('#grant-sites');
const grantStatus = document.querySelector('#grant-status');
const grantSearch = document.querySelector('#grant-search');
const displayedGrantSites = new Map();

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

async function showGrantSite(site, container) {
  container.replaceChildren();
  const heading = document.createElement('h4');
  heading.textContent = site.hostname;
  const workspace = document.createElement('p');
  workspace.className = 'admin-grants__workspace';
  workspace.textContent = 'Espacio: ' + site.workspace;
  const history = document.createElement('div');
  history.className = 'admin-grants__history';

  const refresh = async () => {
    const data = await grantApi('/api/access/operator/grant-sites/' + encodeURIComponent(site.id));
    history.replaceChildren();
    if (!data.entitlements.length) {
      const empty = document.createElement('p');
      empty.textContent = 'Este espacio todavía no tiene períodos registrados.';
      history.append(empty);
    }
    for (const item of data.entitlements) {
      const record = document.createElement('div');
      record.className = 'admin-grants__period';
      const summary = document.createElement('p');
      const origin = item.source === 'internal_grant' ? 'Cortesía' : 'Acceso pagado';
      const state = item.status === 'revoked' ? 'Revocada' :
        item.status !== 'active' ? item.status :
        new Date(item.active_from) > new Date() ? 'Programada' :
        item.active_until && new Date(item.active_until) <= new Date() ? 'Vencida' : 'Vigente';
      summary.textContent = origin + ' · ' + state + ' · ' +
        grantDate(item.active_from) + ' → ' + grantDate(item.active_until) +
        (item.last_reason ? ' · ' + item.last_reason : '');
      record.append(summary);
      if (item.source === 'internal_grant' && item.status === 'active') {
        const reason = document.createElement('input');
        reason.required = true;
        reason.minLength = 3;
        reason.maxLength = 1000;
        reason.placeholder = 'Motivo de revocación';
        const revoke = grantButton('Revocar cortesía');
        revoke.addEventListener('click', async () => {
          if (reason.value.trim().length < 3) {
            grantStatus.textContent = 'Indica un motivo de revocación de al menos 3 caracteres.';
            return;
          }
          if (!window.confirm('¿Revocar la cortesía de ' + site.hostname + ' en ' + site.workspace + '?')) return;
          revoke.disabled = true;
          try {
            await grantApi('/api/access/operator/grants/' + encodeURIComponent(item.id) + '/revoke', {
              method: 'POST', body: JSON.stringify({ reason: reason.value.trim() }),
            });
            grantStatus.textContent = 'Cortesía revocada.';
            await refresh();
          } catch (error) {
            grantStatus.textContent = error.message;
            revoke.disabled = false;
          }
        });
        const actions = document.createElement('div');
        actions.className = 'operator-actions';
        actions.append(revoke);
        record.append(grantField('Motivo de revocación', reason), actions);
      }
      history.append(record);
    }
  };

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
  const submit = grantButton('Habilitar acceso', 'submit');
  const actions = document.createElement('div');
  actions.className = 'operator-actions';
  actions.append(submit);
  form.append(grantField('Duración (días)', days), grantField('Motivo', reason), actions);
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (!window.confirm('¿Habilitar acceso para ' + site.hostname + ' en ' + site.workspace + '?')) return;
    submit.disabled = true;
    try {
      await grantApi('/api/access/operator/grants', {
        method: 'POST',
        body: JSON.stringify({ workspace_site_id: site.id, days: Number(days.value), reason: reason.value.trim() }),
      });
      grantStatus.textContent = 'Cortesía registrada.';
      await refresh();
    } catch (error) {
      grantStatus.textContent = error.message;
    } finally {
      submit.disabled = false;
    }
  });
  container.append(heading, workspace, form, history);
  await refresh();
}

function normalizeGrantSearch(value) {
  const trimmed = value.trim();
  if (!trimmed) return '';
  try {
    // Search by hostname, whether the operator typed a URL or a simple domain.
    const candidate = trimmed.includes('://') ? trimmed : 'https://' + trimmed;
    return new URL(candidate).hostname.toLowerCase();
  } catch (_error) {
    return trimmed.toLowerCase();
  }
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
    grantStatus.textContent = data.sites.length + ' sitio(s) encontrado(s). Se conservan los sitios consultados en esta sesión.';
    for (const site of data.sites) {
      let container = displayedGrantSites.get(site.id);
      if (!container) {
        container = document.createElement('article');
        container.className = 'operator-review admin-grants__site';
        displayedGrantSites.set(site.id, container);
        grantResults.prepend(container);
        await showGrantSite(site, container);
      } else {
        // Bring the selected site into view without discarding previously loaded sites.
        grantResults.prepend(container);
      }
    }
  } catch (error) {
    grantStatus.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});
