/* Operator decisions are always enforced by the backend's verified identity.
   Do not store operator roles, tokens, or authorization decisions in the browser. */
const statusNode = document.querySelector('#operator-status');
const listNode = document.querySelector('#operator-reviews');
let auth;

function waitForAuth() {
  if (window.MininodeAuth) return Promise.resolve(window.MininodeAuth);
  return new Promise((resolve) => window.addEventListener(
    'mininode:auth-api-ready', () => resolve(window.MininodeAuth), { once: true },
  ));
}

async function request(path, options = {}) {
  const token = await auth.getToken();
  if (!token) throw new Error('Debes iniciar sesión en Mininode.');
  const response = await fetch(path, {
    ...options,
    headers: {
      Accept: 'application/json',
      Authorization: `Bearer ${token}`,
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 403) throw new Error('Tu cuenta no tiene permisos de operador.');
    throw new Error(typeof body.detail === 'string' ? body.detail : 'No pudimos completar la solicitud.');
  }
  return body;
}

const localDate = (value) => {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleString('es-CL', { timeZone: 'America/Santiago' });
};

function makeCard(item) {
  const card = document.createElement('article');
  card.className = 'operator-review';
  const title = document.createElement('h2');
  title.textContent = `${item.first_hostname} ↔ ${item.second_hostname}`;
  const meta = document.createElement('p');
  meta.textContent = `${item.workspace} · ${localDate(item.requested_at)} · ${item.status}`;
  card.append(title, meta);
  if (item.status !== 'pending') {
    const note = document.createElement('p');
    note.textContent = `Decisión: ${item.note || 'Sin motivo'} · ${localDate(item.reviewed_at)}`;
    card.append(note);
    return card;
  }
  const label = document.createElement('label');
  label.textContent = 'Motivo de la decisión';
  const reason = document.createElement('textarea');
  reason.maxLength = 1000;
  reason.required = true;
  reason.placeholder = 'Indica la evidencia o motivo (mínimo 3 caracteres)';
  label.append(reason);
  const buttons = document.createElement('div');
  buttons.className = 'operator-actions';
  const failure = document.createElement('p');
  failure.className = 'operator-review__error';
  failure.setAttribute('role', 'alert');

  for (const action of ['approved', 'rejected']) {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = action === 'approved' ? 'Aprobar agrupación' : 'Rechazar';
    button.addEventListener('click', async () => {
      const note = reason.value.trim();
      if (note.length < 3) { failure.textContent = 'Indica un motivo de al menos 3 caracteres.'; return; }
      if (action === 'approved' && !window.confirm(
        '¿Aprobar? Mininode verificará la redirección y solo agrupará si no existen vínculos comerciales.',
      )) return;
      const allButtons = [...buttons.querySelectorAll('button')];
      allButtons.forEach((element) => { element.disabled = true; });
      failure.textContent = '';
      try {
        await request(`/api/access/operator/site-group-reviews/${encodeURIComponent(item.id)}/decision`, {
          method: 'POST', body: JSON.stringify({ decision: action, note }),
        });
        await loadReviews();
      } catch (error) {
        failure.textContent = error instanceof Error ? error.message : 'No pudimos resolver la solicitud.';
        allButtons.forEach((element) => { element.disabled = false; });
      }
    });
    buttons.append(button);
  }
  card.append(label, buttons, failure);
  return card;
}

async function loadReviews() {
  const data = await request('/api/access/operator/site-group-reviews');
  listNode.replaceChildren();
  if (!Array.isArray(data.reviews) || data.reviews.length === 0) {
    statusNode.textContent = 'No hay solicitudes para revisar.';
    return;
  }
  const pending = data.reviews.filter((item) => item.status === 'pending').length;
  statusNode.textContent = `${pending} solicitud(es) pendientes · ${data.reviews.length} en total`;
  data.reviews.forEach((item) => listNode.append(makeCard(item)));
}

window.addEventListener('load', async () => {
  try {
    auth = await waitForAuth();
    await auth.ready({ ui: false });
    if (!auth.session()) {
      statusNode.textContent = 'Debes iniciar sesión desde Mi espacio para acceder al panel.';
      return;
    }
    await loadReviews();
  } catch (error) {
    statusNode.textContent = error instanceof Error ? error.message : 'No pudimos verificar tu acceso.';
  }
});
