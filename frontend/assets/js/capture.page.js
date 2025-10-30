import { Stopwatch } from './lib/metrics.js';
import * as Ex from './util-export.js';

// Session p95 tracker (client-side)
const sessionTimings = [];
function pushTiming(ms) {
  sessionTimings.push(ms);
  if (sessionTimings.length > 200) sessionTimings.shift();
}
function p95(arr) {
  if (!arr.length) return 0;
  const a = [...arr].sort((x, y) => x - y);
  const idx = Math.ceil(0.95 * a.length) - 1;
  return a[Math.max(0, idx)];
}

const el = (id) => document.getElementById(id);
const drop = el('dropzone');
const fileInput = el('file-input');
const startBtn = el('start-btn');
const resultBox = el('result-box');
const jsonOut = el('json-out');
const preview = el('preview');
const err = el('err');
const perfBadge = el('perf-badge');
const diffBox = el('diff-box');
const diffOut = el('diff-out');
const docTypeSel = el('doc-type');
const copyBtn = el('copy-json');
const exportBtn = el('export-json');
const itemsBox = el('items-box');
const itemsMeta = el('items-meta');
const itemsTable = el('items-table');
const fileInfo = el('file-info');
const fileName = el('file-name');
const fileMeta = el('file-meta');
const thumb = el('thumb');
const summaryBox = el('summary-box');
const netoOut = el('neto-out');
const ivaOut = el('iva-out');
const totalOut = el('total-out');

let selectedFile = null;

function apiBase() {
  let base = (typeof window !== 'undefined' && window.MININODE_API_BASE) ? window.MININODE_API_BASE : '';
  if (!base) base = (location.protocol === 'file:') ? 'http://127.0.0.1:8000' : '/api';
  return String(base || '').replace(/\/$/, '');
}
function apiUrl(path) {
  const base = apiBase();
  const p = path.startsWith('/') ? path : '/' + path;
  return base + p;
}

function showError(msg) {
  if (!err) return;
  err.textContent = String(msg || 'Error');
  err.classList.remove('wr-hidden');
}
function clearError() {
  if (!err) return;
  err.textContent = '';
  err.classList.add('wr-hidden');
}
function setStartEnabled(ok) { if (startBtn) startBtn.disabled = !ok; }

function isHeic(type) { return type === 'image/heic' || type === 'image/heif'; }
function isWebp(type) { return type === 'image/webp'; }

async function readAsDataURL(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

async function webpToJpeg(file) {
  const dataUrl = await readAsDataURL(file);
  const img = new Image();
  img.decoding = 'async';
  img.src = dataUrl;
  await img.decode();
  const canvas = document.createElement('canvas');
  canvas.width = img.naturalWidth;
  canvas.height = img.naturalHeight;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(img, 0, 0);
  const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.9));
  return new File([blob], (file.name || 'image') + '.jpg', { type: 'image/jpeg' });
}

function setPreview(file) {
  const url = URL.createObjectURL(file);
  if (preview) preview.src = url;
}
function setThumb(file) {
  const url = URL.createObjectURL(file);
  if (thumb) thumb.src = url;
}

function humanSize(bytes) {
  if (!bytes && bytes !== 0) return '';
  const units = ['B', 'KB', 'MB', 'GB'];
  let i = 0; let n = bytes;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
  return `${n.toFixed(1)} ${units[i]}`;
}

function showFileInfo(file) {
  if (!fileInfo) return;
  if (fileName) fileName.textContent = file.name || 'archivo';
  if (fileMeta) fileMeta.textContent = `${file.type || 'tipo desconocido'} | ${humanSize(file.size)}`;
  fileInfo.classList.remove('wr-hidden');
}

// UI locale/decimals (paramétrico por país)
function getQueryParam(name) { try { return new URL(location.href).searchParams.get(name); } catch { return null; } }
const UI_LOCALE = (window.MININODE_LOCALE || getQueryParam('locale') || 'es-CL');
const UI_DECIMALS = (() => {
  const q = getQueryParam('decimals_ui');
  if (q !== null && q !== undefined && q !== '') return Math.max(0, Number(q));
  if (typeof window.MININODE_DECIMALS_UI === 'number') return Math.max(0, window.MININODE_DECIMALS_UI | 0);
  return UI_LOCALE.toLowerCase().startsWith('es-cl') ? 0 : 2;
})();
const nfUI = new Intl.NumberFormat(UI_LOCALE, { minimumFractionDigits: UI_DECIMALS, maximumFractionDigits: UI_DECIMALS });
function parseNumberLike(v) {
  if (v === null || v === undefined) return null;
  if (typeof v === 'number' && Number.isFinite(v)) return v;
  let s = String(v).trim();
  if (!s) return null;
  s = s.replace(/[^0-9,\.\-]/g, '');
  const lastComma = s.lastIndexOf(',');
  const lastDot = s.lastIndexOf('.');
  if (lastComma > -1 && lastDot > -1) {
    if (lastComma > lastDot) { s = s.replace(/\./g, '').replace(',', '.'); }
    else { s = s.replace(/,/g, ''); }
  } else if (lastComma > -1) {
    const parts = s.split(',');
    if (parts.length === 2 && parts[1].length <= 2) s = s.replace(',', '.');
    else s = s.replace(/,/g, '');
  } else if (lastDot > -1) {
    const dotCount = (s.match(/\./g) || []).length;
    if (dotCount > 1) s = s.replace(/\./g, '');
    else {
      const parts = s.split('.');
      const suffixLen = (parts[1] || '').length;
      if (suffixLen === 3 || suffixLen > 3) s = s.replace(/\./g, '');
    }
  }
  const n = parseFloat(s);
  return Number.isFinite(n) ? n : null;
}
function fmtUI(v) {
  const n = parseNumberLike(v);
  if (n === null) return v ?? '';
  const factor = Math.pow(10, UI_DECIMALS);
  const r = factor ? Math.round(n * factor) / factor : Math.round(n);
  return nfUI.format(r);
}
function pick(it, keys) {
  for (const k of keys) {
    if (it && it[k] !== undefined && it[k] !== null && String(it[k]).trim() !== '') return it[k];
  }
  return undefined;
}

function onFileChosen(file) {
  clearError();
  if (!file) { setStartEnabled(false); return; }

  if (file.size > 5 * 1024 * 1024) {
    showError('El archivo supera 5 MB.');
    setStartEnabled(false);
    return;
  }

  if (isHeic(file.type)) {
    showError('Formato HEIC/HEIF no soportado en MVP. Convierte a JPG/PNG e inténtalo nuevamente.');
    setStartEnabled(false);
    return;
  }

  selectedFile = file;
  drop?.classList.add('wr-drop--ready');
  try { setThumb(file); } catch {}
  showFileInfo(file);
  setStartEnabled(true);
  // Warmup backend (no bloquea)
  try { fetch(apiUrl('/health')).catch(() => {}); } catch {}
}

drop?.addEventListener('dragover', (e) => { e.preventDefault(); drop.classList.add('wr-drop--hover'); });
drop?.addEventListener('dragleave', () => drop.classList.remove('wr-drop--hover'));
drop?.addEventListener('drop', (e) => { e.preventDefault(); drop.classList.remove('wr-drop--hover'); const f = e.dataTransfer.files && e.dataTransfer.files[0]; onFileChosen(f); });
fileInput?.addEventListener('change', (e) => { const f = e.target.files && e.target.files[0]; onFileChosen(f); });

async function buildFormData(file) {
  let upFile = file;
  if (isWebp(file.type)) {
    try { upFile = await webpToJpeg(file); }
    catch (e) { showError('No se pudo convertir WEBP. Convierte a JPG/PNG e inténtalo.'); throw e; }
  }
  const fd = new FormData();
  fd.append('file', upFile, upFile.name || 'image.jpg');
  return fd;
}

function formatMs(ms) { return `${(ms / 1000).toFixed(1)}s`; }

startBtn?.addEventListener('click', async () => {
  clearError();
  if (!selectedFile) return;
  setStartEnabled(false);
  resultBox?.classList.remove('wr-hidden');
  diffBox?.classList.add('wr-hidden');
  if (diffOut) diffOut.textContent = '';
  if (jsonOut) jsonOut.textContent = 'Procesando...';

  const sw = new Stopwatch();
  try {
    const fd = await buildFormData(selectedFile);
    setPreview(selectedFile);

    const docType = docTypeSel?.value || 'boleta';
    const url = apiUrl(`/capture?doc_type=${encodeURIComponent(docType)}&usar_fallback=true&mode=fast`);

    const resp = await fetch(url, { method: 'POST', body: fd });
    const text = await resp.text();
    if (!resp.ok) { showError(`Error ${resp.status}: ${text}`); if (jsonOut) jsonOut.textContent = ''; return; }
    const data = JSON.parse(text);

    // JSON pretty
    if (jsonOut) jsonOut.textContent = JSON.stringify(data, null, 2);

    // Header summary
    try {
      const f = data.fields || {};
      const netoVal = f.neto?.value ?? f.neto;
      const ivaVal = f.iva?.value ?? f.iva;
      const totalVal = f.total?.value ?? f.total;
      if (summaryBox && (netoVal != null || ivaVal != null || totalVal != null)) {
        if (netoOut) netoOut.textContent = netoVal != null ? fmtUI(netoVal) : '';
        if (ivaOut) ivaOut.textContent = ivaVal != null ? fmtUI(ivaVal) : '';
        if (totalOut) totalOut.textContent = totalVal != null ? fmtUI(totalVal) : '';
        summaryBox.classList.remove('wr-hidden');
      }
    } catch {}

    // Items (if any)
    try {
      let items = Array.isArray(data.items) ? data.items : [];
      // Remove IVA line
      items = items.filter((it) => {
        const cod = String(it.codigo || '').trim().toLowerCase();
        if (cod === 'iva') return false;
        if (/(^|\b)iva(\b|:)/i.test(String(it.descripcion || ''))) return false;
        return true;
      });
      const tbody = itemsTable?.querySelector('tbody');
      if (tbody) tbody.innerHTML = '';
      if (items.length && tbody) {
        items.forEach((it) => {
          const tr = document.createElement('tr');
          const td = (v, align = 'left') => { const c = document.createElement('td'); c.style.padding = '6px'; c.style.borderBottom = '1px solid var(--border)'; c.style.textAlign = align; c.textContent = v ?? ''; return c; };
          const vCantidad = pick(it, ['cantidad', 'cant']);
          const vPU = pick(it, ['precio_unitario', 'p_unitario', 'p_unit', 'pu', 'precio']);
          const vTotal = pick(it, ['total_linea', 'total', 'importe', 'monto']);
          tr.appendChild(td(it.codigo || ''));
          tr.appendChild(td(it.descripcion || ''));
          tr.appendChild(td(fmtUI(vCantidad) || '', 'right'));
          tr.appendChild(td(fmtUI(vPU) || '', 'right'));
          tr.appendChild(td(fmtUI(vTotal) || '', 'right'));
          tbody.appendChild(tr);
        });
        itemsBox?.classList.remove('wr-hidden');
        if (itemsMeta) itemsMeta.textContent = `Filas: ${items.length}`;
      } else {
        itemsBox?.classList.add('wr-hidden');
        if (itemsMeta) itemsMeta.textContent = '';
      }
    } catch {}

    // Differences
    const beforeBad = Object.entries(data.consistency?.checks || {}).filter(([, v]) => v === false).map(([k]) => k);
    const lines = [];
    if (beforeBad.length) { lines.push('Checks fallidos:', ...beforeBad.map(k => `- ${k}`)); }
    if (lines.length) { diffBox?.classList.remove('wr-hidden'); if (diffOut) diffOut.textContent = lines.join('\n'); }

    // Perf badge
    const totalMs = data.timings?.server_total || data.timings?.total || sw.elapsed();
    pushTiming(totalMs);
    const p95Ms = p95(sessionTimings);
    if (perfBadge) {
      perfBadge.textContent = `Srv ${formatMs(totalMs)} | p95 ${formatMs(p95Ms)}`;
      perfBadge.title = `Srv decode ${data.timings?.decode_ms || 0}ms, preproc ${data.timings?.preproc_ms || 0}ms, OCR ${formatMs(data.timings?.ocr || 0)}, LLM-mini ${formatMs(data.timings?.llm_mini || 0)}, validar ${formatMs(data.timings?.validate_ms || 0)}`;
    }
  } catch (e) {
    showError(String(e));
  } finally {
    setStartEnabled(true);
  }
});

// Copy JSON
copyBtn?.addEventListener('click', async () => {
  const txt = jsonOut?.textContent || '';
  if (!txt.trim()) return;
  await Ex.copyToClipboard(txt);
  copyBtn.textContent = 'Copiado';
  setTimeout(() => (copyBtn.textContent = 'Copiar JSON'), 1200);
});

// Export dropdown
if (exportBtn) {
  const dropdown = exportBtn.parentElement;
  const menu = dropdown?.querySelector('.wr-menu');
  exportBtn.addEventListener('click', () => { dropdown.classList.toggle('open'); });
  document.addEventListener('click', (e) => { if (!e.target.closest('.wr-dropdown')) dropdown.classList.remove('open'); });
  menu?.addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-export]');
    if (!btn) return;
    const kind = btn.getAttribute('data-export');
    const txt = jsonOut?.textContent || '';
    if (!txt.trim()) return;
    if (kind === 'json') Ex.downloadText(txt, 'capture.json', 'application/json');
  });
}

