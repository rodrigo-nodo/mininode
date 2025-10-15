import { injectPartials } from '/assets/js/core-partials.js';
import { attachGoNavigation } from '/assets/js/core-go-nav.js';
import * as Ex from '/assets/js/util-export.js';

const LS_KEY = 'mininode_write_prefs_v1';
const API_URL = '/api/write/draft'; // proxy a /redaccion/draft
const ANALYZE_PROXY = '/api/analisis/summary'; // proxy a /analisis/summary
const ANALYZE_URL = 'https://api.mininode.io/analisis/summary'; // fallback directo

// --- util: URLs (máx 3, normaliza y deduplica) ---
function extractUrls(text) {
  const re = /\bhttps?:\/\/[^\s)]+/gi;
  const found = (text || '').match(re) || [];
  const norm = found.map(u => u.trim().replace(/[),.;]+$/, ''));
  return Array.from(new Set(norm)).slice(0, 3);
}

function loadPrefs() {
  try { return JSON.parse(localStorage.getItem(LS_KEY)) || {}; } catch { return {}; }
}
function savePrefs(p) {
  try { localStorage.setItem(LS_KEY, JSON.stringify(p)); } catch {}
}

// Llama análisis vía proxy; si falla y hay MININODE_API_KEY en LS, usa endpoint directo.
async function analyzeOne(url, lang = 'es') {
  const body = {
    urls: [url],
    scope: 'page',
    lang,
    prompt: 'Resume en 3–5 viñetas: qué hace, público objetivo y propuesta de valor.'
  };

  // 1) Proxy same-origin (no requiere header)
  try {
    const r = await fetch(ANALYZE_PROXY, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    if (r.ok) {
      const d = await r.json();
      return d.text || d.result || d.output || '';
    }
  } catch (_) { /* sigue al fallback */ }

  // 2) Fallback directo con X-Api-Key (opcional si existe en LS)
  const key = localStorage.getItem('MININODE_API_KEY') || '';
  if (!key) throw new Error('No hay proxy /api/analisis/summary y falta MININODE_API_KEY para el fallback.');
  const rr = await fetch(ANALYZE_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Api-Key': key },
    body: JSON.stringify(body)
  });
  if (!rr.ok) throw new Error(`Analisis HTTP ${rr.status}`);
  const dd = await rr.json();
  return dd.text || dd.result || dd.output || '';
}

async function init() {
  await injectPartials();
  attachGoNavigation(document);

  // UI elements (existen tras injectPartials)
  const analyzeToggle = document.getElementById('analyzeToggle');
  const urlInfo       = document.getElementById('urlInfo');

  const $txt     = document.getElementById('wr-texto');
  const $size    = document.getElementById('wr-size');
  const $tone    = document.getElementById('wr-tone');
  const $lang    = document.getElementById('wr-lang'); // oculto en v1 (default 'es')
  const $gen     = document.getElementById('wr-generate');
  const $resBox  = document.getElementById('wr-result-box');
  const $res     = document.getElementById('wr-result');
  const $err     = document.getElementById('wr-error');
  const $copy    = document.getElementById('wr-copy');
  const $exportBtn  = document.getElementById('wr-export');
  const $exportMenu = $exportBtn?.parentElement?.querySelector('.wr-menu');

  // Estado del toggle (respeta override manual)
  let userTouchedToggle = false;
  analyzeToggle?.addEventListener('change', () => { userTouchedToggle = true; });

  // AUTO-ON cuando se escribe el prompt (usa $txt)
  $txt?.addEventListener('input', () => {
    const urls = extractUrls($txt.value);
    if (urlInfo) {
      if (urls.length > 0) {
        urlInfo.textContent = `URLs detectadas: ${urls.length}`;
        urlInfo.classList.remove('wr-hidden');
      } else {
        urlInfo.textContent = '';
        urlInfo.classList.add('wr-hidden');
      }
    }
    if (!userTouchedToggle && analyzeToggle) analyzeToggle.checked = urls.length > 0;
  });

  // Defaults
  const prefs = { tamaño: 'micro', tono: 'simple', idioma: 'es', ...loadPrefs() };
  if ($size) $size.value = prefs.tamaño;
  if ($tone) $tone.value = prefs.tono;
  if ($lang) $lang.value = prefs.idioma;

  // UI limpia al cargar
  if ($err)   { $err.textContent = ''; $err.classList.add('wr-hidden'); }
  if ($resBox){ $resBox.classList.add('wr-hidden'); }
  if ($res)   { $res.textContent = ''; }

  // Persistencia básica
  $size?.addEventListener('change', () => { prefs.tamaño = $size.value; savePrefs(prefs); });
  $tone?.addEventListener('change', () => { prefs.tono   = $tone.value; savePrefs(prefs); });
  $lang?.addEventListener('change', () => { prefs.idioma = $lang.value; savePrefs(prefs); });

  // Export
  if ($exportBtn && $exportMenu) {
    $exportBtn.addEventListener('click', () => {
      $exportBtn.parentElement.classList.toggle('open');
    });
    document.addEventListener('click', (e) => {
      if (!e.target.closest('.wr-dropdown')) $exportBtn.parentElement.classList.remove('open');
    });
    $exportMenu.addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-export]');
      if (!btn) return;
      const kind = btn.getAttribute('data-export');
      if (!$res?.textContent?.trim()) return;
      if (kind === 'txt') Ex.downloadText($res.textContent, 'borrador.txt');
      else if (kind === 'md') Ex.downloadMarkdown($res.textContent, 'borrador.md');
    });
  }

  // Copiar
  $copy?.addEventListener('click', async () => {
    if (!$res?.textContent) return;
    await Ex.copyToClipboard($res.textContent);
    $copy.textContent = 'Copiado ✓';
    setTimeout(() => ($copy.textContent = 'Copiar'), 1200);
  });

  // === ÚNICO punto que llama a la API: clic del botón ===
  $gen?.addEventListener('click', async () => {
    // Ocultar errores y resultado al empezar
    $err.classList.add('wr-hidden'); 
    $err.textContent = '';
    $resBox.classList.add('wr-hidden'); 
    $res.textContent = '';

    const raw = ($txt.value || '').trim();
    if (!raw) {
      $err.textContent = 'Por favor escribe algo en el input.';
      $err.classList.remove('wr-hidden');
      return;
    }

    const size = $size.value || 'micro';
    const tone = $tone.value || 'simple';
    const lang = ($lang && $lang.value) || 'es';

    const sizeGuide = {
      micro: '120–180 palabras, 1–2 párrafos. ',
      medio: '300–500 palabras, secciones cortas (H2). ',
      largo: '600–800 palabras, estructura clara con H2/H3. ',
    }[size];

    const toneGuide = {
      simple: 'tono claro y directo, sin jergas. ',
      formal: 'tono formal y preciso. ',
      inspirador: 'tono motivador con lenguaje positivo. ',
      'técnico': 'tono técnico y específico cuando corresponda. ',
    }[tone];

    // Prompt base (sin contexto)
    const basePrompt =
      `Escribe un borrador en español con ${sizeGuide}${toneGuide}` +
      `Transforma estas ideas en un texto coherente y útil. ` +
      `Evita saludos genéricos.\n` +
      `Contenido base:\n` + raw;

    $gen.disabled = true; 
    $gen.textContent = 'Generando…';

    try {
      // (1) Análisis previo opcional (si toggle ON y hay URLs)
      let contextMd = '';
      const urls = extractUrls(raw);
      // SIEMPRE analiza si hay URLs, independiente del checkbox
      if (urls.length) {
        for (const u of urls) {
          // feedback mínimo al usuario
          $gen.textContent = `Analizando: ${u}`;
          const summary = await analyzeOne(u, lang);
          contextMd += `#### ${u}\n${summary}\n\n`;
        }
      }

      // (2) Componer prompt final
      const composedPrompt = contextMd
        ? `### Contexto (resumen de URLs)\n${contextMd}---\n\n${basePrompt}`
        : basePrompt;

      // (3) Redacción (vía proxy /api/write/draft)
      $gen.textContent = 'Redactando…';
      const resp = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: composedPrompt, tone })
      });

      const text = await resp.text();
      if (!resp.ok) throw new Error(`Error ${resp.status}: ${text}`);

      let data; try { data = JSON.parse(text); } catch { data = { text }; }
      const draft = data?.text || data?.draft || data?.result || '';
      $res.textContent = draft || '[sin contenido]';
      $resBox.classList.remove('wr-hidden');
      $gen.textContent = 'Listo ✓';
    } catch (e) {
      $err.textContent = String(e.message || e);
      $err.classList.remove('wr-hidden');
    } finally {
      setTimeout(() => { $gen.textContent = 'Generar borrador'; $gen.disabled = false; }, 250);
    }
  });
}

init();
