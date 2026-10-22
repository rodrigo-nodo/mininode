const grantForm = document.querySelector('#grant-search-form');
const grantResults = document.querySelector('#grant-sites');
const grantStatus = document.querySelector('#grant-status');
async function grantApi(path, options = {}) {
  const token = await window.MininodeAuth.getToken();
  if (!token) throw new Error('Sesión requerida');
  const response = await fetch(path, { ...options, headers: {
    Authorization: 'Bearer ' + token, Accept: 'application/json',
    ...(options.body ? { 'Content-Type': 'application/json' } : {}),
  }});
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || 'Error de solicitud');
  return data;
}
async function showGrantSite(site, container) {
  container.replaceChildren();
  const title = document.createElement('h4');
  title.textContent = site.hostname + ' · ' + site.workspace;
  container.append(title);
  const history = document.createElement('div');
  const refresh = async () => {
    const data = await grantApi('/api/access/operator/grant-sites/' + site.id);
    history.replaceChildren();
    for (const item of data.entitlements) {
      const line = document.createElement('p');
      line.textContent = item.source + ' · ' + item.status + ' · ' +
        new Date(item.active_from).toLocaleDateString('es-CL') + ' → ' +
        (item.active_until ? new Date(item.active_until).toLocaleDateString('es-CL') : 'sin vencimiento') +
        (item.last_reason ? ' · ' + item.last_reason : '');
      history.append(line);
      if (item.source === 'internal_grant' && item.status === 'active') {
        const revoke = document.createElement('button');
        revoke.type = 'button'; revoke.textContent = 'Revocar';
        const reason = document.createElement('input');
        reason.placeholder = 'Motivo de revocación'; reason.minLength = 3;
        revoke.addEventListener('click', async () => {
          if (reason.value.trim().length < 3) return;
          revoke.disabled = true;
          try {
            await grantApi('/api/access/operator/grants/' + item.id + '/revoke', {
              method: 'POST', body: JSON.stringify({ reason: reason.value.trim() }),
            });
            await refresh();
          } catch (error) { grantStatus.textContent = error.message; revoke.disabled = false; }
        });
        history.append(reason, revoke);
      }
    }
  };
  const form = document.createElement('form');
  const days = document.createElement('input');
  days.type = 'number'; days.min = '1'; days.max = '365'; days.value = '30'; days.required = true;
  days.setAttribute('aria-label', 'Días de cortesía');
  const reason = document.createElement('input');
  reason.placeholder = 'Motivo de la cortesía'; reason.required = true; reason.minLength = 3;
  const submit = document.createElement('button');
  submit.textContent = 'Habilitar acceso';
  form.append(days, reason, submit);
  form.addEventListener('submit', async event => {
    event.preventDefault(); submit.disabled = true;
    try {
      await grantApi('/api/access/operator/grants', { method: 'POST',
        body: JSON.stringify({ workspace_site_id: site.id, days: Number(days.value), reason: reason.value.trim() }) });
      grantStatus.textContent = 'Cortesía registrada'; await refresh();
    } catch (error) { grantStatus.textContent = error.message; }
    finally { submit.disabled = false; }
  });
  container.append(form, history);
  await refresh();
}
grantForm.addEventListener('submit', async event => {
  event.preventDefault(); grantResults.replaceChildren();
  try {
    const q = document.querySelector('#grant-search').value.trim();
    const data = await grantApi('/api/access/operator/grant-sites?q=' + encodeURIComponent(q));
    grantStatus.textContent = data.sites.length + ' sitio(s) encontrado(s)';
    for (const site of data.sites) {
      const container = document.createElement('section');
      grantResults.append(container);
      await showGrantSite(site, container);
    }
  } catch (error) { grantStatus.textContent = error.message; }
});
