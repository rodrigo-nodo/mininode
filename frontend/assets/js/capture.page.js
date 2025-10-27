import { Stopwatch } from './lib/metrics.js';
import * as Ex from './util-export.js';

// Simple session-based p95 tracker (client-side only, MVP)
const sessionTimings = [];
function pushTiming(ms) {
  sessionTimings.push(ms);
  if (sessionTimings.length > 200) sessionTimings.shift();
}
function p95(arr) {
  if (!arr.length) return 0;
  const a = [...arr].sort((x,y)=>x-y);
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
  if (!base) {
    base = (location.protocol === 'file:') ? 'http://127.0.0.1:8000' : '/api';
  }
  return String(base || '').replace(/\/$/, '');
}
function apiUrl(path) {
  const base = apiBase();
  const p = path.startsWith('/') ? path : '/' + path;
  return base + p;
}

function showError(msg) {
  err.textContent = msg;
  err.classList.remove('wr-hidden');
}
function clearError() {
  err.textContent = '';
  err.classList.add('wr-hidden');
}
function setStartEnabled(ok) {
  startBtn.disabled = !ok;
}

function isHeic(type) {
  return type === 'image/heic' || type === 'image/heif';
}
function isWebp(type) {
  return type === 'image/webp';
}

async function readAsDataURL(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

async function webpToJpeg(file) {
  // Decode via ImageBitmap or HTMLImageElement, then draw to canvas and export JPEG
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

function onFileChosen(file) {
  clearError();
  if (!file) { setStartEnabled(false); return; }

  if (file.size > 5 * 1024 * 1024) {
    showError('El archivo supera 5 MB.');
    setStartEnabled(false);
    return;
  }

  if (isHeic(file.type)) {
    // No conversion in MVP, ask user to convert
    showError('Formato HEIC/HEIF no soportado en MVP. Convierte a JPG/PNG e inténtalo nuevamente.');
    setStartEnabled(false);
    return;
  }

  selectedFile = file;
  // Feedback inmediato: marcar dropzone y mostrar chip con nombre/size
  drop.classList.add('wr-drop--ready');
  try { setThumb(file); } catch {}
  showFileInfo(file);
  setStartEnabled(true);
}

drop.addEventListener('dragover', (e) => {
  e.preventDefault();
  drop.classList.add('wr-drop--hover');
});
drop.addEventListener('dragleave', () => drop.classList.remove('wr-drop--hover'));
drop.addEventListener('drop', (e) => {
  e.preventDefault();
  drop.classList.remove('wr-drop--hover');
  const f = e.dataTransfer.files && e.dataTransfer.files[0];
  onFileChosen(f);
});
fileInput.addEventListener('change', (e) => {
  const f = e.target.files && e.target.files[0];
  onFileChosen(f);
});

async function buildFormData(file) {
  let upFile = file;
  if (isWebp(file.type)) {
    try {
      upFile = await webpToJpeg(file);
    } catch (e) {
      showError('No se pudo convertir WEBP. Convierte a JPG/PNG e inténtalo.');
      throw e;
    }
  }
  const fd = new FormData();
  fd.append('file', upFile, upFile.name || 'image.jpg');
  return fd;
}

function setPreview(file) {
  const url = URL.createObjectURL(file);
  preview.src = url;
}

function setThumb(file) {
  const url = URL.createObjectURL(file);
  if (thumb) thumb.src = url;
}

function humanSize(bytes) {
  if (!bytes && bytes !== 0) return '';
  const units = ['B','KB','MB','GB'];
  let i = 0; let n = bytes;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
  return `${n.toFixed(1)} ${units[i]}`;
}

// Number parsing and formatting helpers (no decimals, thousands separator)
function parseNumberLike(v) {
  if (v === null || v === undefined) return null;
  if (typeof v === 'number' && Number.isFinite(v)) return v;
  let s = String(v).trim();
  if (!s) return null;
  // Remove currency/units; keep digits, separators and minus
  s = s.replace(/[^0-9,\.\-]/g, '');
  const lastComma = s.lastIndexOf(',');
  const lastDot = s.lastIndexOf('.');
  if (lastComma > -1 && lastDot > -1) {
    if (lastComma > lastDot) {
      // Comma as decimal separator; dots as thousands
      s = s.replace(/\./g, '').replace(',', '.');
    } else {
      // Dot as decimal; commas as thousands
      s = s.replace(/,/g, '');
    }
  } else if (lastComma > -1) {
    const parts = s.split(',');
    if (parts.length === 2 && parts[1].length <= 2) {
      // Likely decimal comma
      s = s.replace(',', '.');
    } else {
      // Likely thousands commas
      s = s.replace(/,/g, '');
    }
  } else if (lastDot > -1) {
    // Only dot present → decide by suffix length
    const dotCount = (s.match(/\./g) || []).length;
    if (dotCount > 1) {
      // Multiple dots: treat as thousands separators
      s = s.replace(/\./g, '');
    } else {
      const parts = s.split('.');
      const suffixLen = (parts[1] || '').length;
      if (suffixLen === 3 || suffixLen > 3) {
        // Likely thousands grouping (e.g., 169.660) → remove dot(s)
        s = s.replace(/\./g, '');
      } else {
        // 0–2 digits → treat as decimal dot
        // leave as is
      }
    }
  }
  const n = parseFloat(s);
  if (!Number.isFinite(n)) return null;
  return n;
}

const nf0 = new Intl.NumberFormat('es-CL', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
function fmt0(v) {
  const n = parseNumberLike(v);
  if (n === null) return (v ?? '');
  return nf0.format(Math.round(n));
}

function pick(it, keys) {
  for (const k of keys) {
    if (it && it[k] !== undefined && it[k] !== null && String(it[k]).trim() !== '') return it[k];
  }
  return undefined;
}

function showFileInfo(file) {
  if (!fileInfo) return;
  fileName.textContent = file.name || 'archivo';
  fileMeta.textContent = `${file.type || 'tipo desconocido'} • ${humanSize(file.size)}`;
  fileInfo.classList.remove('wr-hidden');
}

function formatMs(ms) { return `${(ms/1000).toFixed(1)}s`; }

startBtn.addEventListener('click', async () => {
  clearError();
  if (!selectedFile) return;
  setStartEnabled(false);
  resultBox.classList.remove('wr-hidden');
  diffBox.classList.add('wr-hidden');
  diffOut.textContent = '';
  jsonOut.textContent = 'Procesando...';

  const sw = new Stopwatch();
  try {
    const fd = await buildFormData(selectedFile);
    setPreview(selectedFile);

    const docType = docTypeSel.value || 'boleta';
    const url = apiUrl(`/capture?doc_type=${encodeURIComponent(docType)}&usar_fallback=true`);

    const resp = await fetch(url, {
      method: 'POST',
      body: fd,
    });
    const text = await resp.text();
    if (!resp.ok) {
      showError(`Error ${resp.status}: ${text}`);
      jsonOut.textContent = '';
      return;
    }
    const data = JSON.parse(text);

    // Show JSON
    jsonOut.textContent = JSON.stringify(data, null, 2);

    // Header summary formatting (neto/iva/total) if present
    try {
      const f = data.fields || {};
      const netoVal = f.neto?.value ?? f.neto;
      const ivaVal = f.iva?.value ?? f.iva;
      const totalVal = f.total?.value ?? f.total;
      if (summaryBox && (netoVal != null || ivaVal != null || totalVal != null)) {
        if (netoOut) netoOut.textContent = netoVal != null ? fmt0(netoVal) : '';
        if (ivaOut) ivaOut.textContent = ivaVal != null ? fmt0(ivaVal) : '';
        if (totalOut) totalOut.textContent = totalVal != null ? fmt0(totalVal) : '';
        summaryBox.classList.remove('wr-hidden');
      }
    } catch (_) {}

    // Render items table if present
    try {
      const items = Array.isArray(data.items) ? data.items : [];
      const tbody = itemsTable?.querySelector('tbody');
      if (tbody) tbody.innerHTML = '';
      if (items.length) {
        items.forEach((it) => {
          const tr = document.createElement('tr');
          const td = (v, align='left') => {
            const c = document.createElement('td');
            c.style.padding = '6px';
            c.style.borderBottom = '1px solid var(--border)';
            c.style.textAlign = align;
            c.textContent = v ?? '';
            return c;
          };
          const vCantidad = pick(it, ['cantidad', 'cant']);
          const vPU = pick(it, ['precio_unitario', 'p_unitario', 'p_unit', 'pu', 'precio']);
          const vTotal = pick(it, ['total_linea', 'total', 'importe', 'monto']);

          tr.appendChild(td(it.codigo || ''));
          tr.appendChild(td(it.descripcion || ''));
          tr.appendChild(td(fmt0(vCantidad) || '', 'right'));
          tr.appendChild(td(fmt0(vPU) || '', 'right'));
          tr.appendChild(td(fmt0(vTotal) || '', 'right'));
          tbody.appendChild(tr);
        });
        if (itemsBox) itemsBox.classList.remove('wr-hidden');
        if (itemsMeta) itemsMeta.textContent = `Filas: ${items.length}`;
      } else {
        if (itemsBox) itemsBox.classList.add('wr-hidden');
        if (itemsMeta) itemsMeta.textContent = '';
      }
    } catch (_) {}

    // Differences section (if any): relies on consistency.notes or checks if delta exists in future
    // For MVP, if checks has false values, surface them
    const beforeBad = Object.entries(data.consistency?.checks || {}).filter(([,v]) => v === false).map(([k])=>k);
    const afterBad = Object.entries(data.consistency_after_fallback?.checks || {}).filter(([,v]) => v === false).map(([k])=>k);
    const adjusted = Array.isArray(data.adjusted_fields) ? data.adjusted_fields : [];
    const applied = !!data.fallback_applied;
    const lines = [];
    if (beforeBad.length) { lines.push('Checks fallidos (antes):'); beforeBad.forEach(k=>lines.push(`- ${k}`)); }
    if (applied) {
      lines.push('', `Fallback aplicado: ${adjusted.length ? adjusted.join(', ') : '(sin cambios reportados)'}`);
      if (afterBad.length) { lines.push('Checks fallidos (después):'); afterBad.forEach(k=>lines.push(`- ${k}`)); }
      else { lines.push('Checks después: OK'); }
    }
    if (lines.length) {
      diffBox.classList.remove('wr-hidden');
      diffOut.textContent = lines.join('\n');
    }

    // Perf badge
    const totalMs = data.timings?.total || sw.elapsed();
    pushTiming(totalMs);
    const p95Ms = p95(sessionTimings);
    perfBadge.textContent = `Total ${formatMs(totalMs)} | p95(sess) ${formatMs(p95Ms)}`;
    perfBadge.title = `Etapas: upload+preproc cliente ≈, OCR ${formatMs(data.timings?.ocr||0)}, LLM-mini ${formatMs(data.timings?.llm_mini||0)}, validación ${formatMs(data.timings?.validate_ms||0)}`;
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
  exportBtn.addEventListener('click', () => {
    dropdown.classList.toggle('open');
  });
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.wr-dropdown')) dropdown.classList.remove('open');
  });
  menu?.addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-export]');
    if (!btn) return;
    const kind = btn.getAttribute('data-export');
    const txt = jsonOut?.textContent || '';
    if (!txt.trim()) return;
    if (kind === 'json') Ex.downloadText(txt, 'capture.json', 'application/json');
  });
}
