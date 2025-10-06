import { injectPartials } from '/assets/js/core-partials.js';
import { attachGoNavigation } from '/assets/js/core-go-nav.js';
import * as Ex from '/assets/js/util-export.js';

const LS_KEY = 'mininode_write_prefs_v1';

// antes: const API_URL = "https://api.mininode.io/redaccion/draft";
const API_URL = "/api/write/draft";  // llama a la Function, no expone la API key
// Para prod: NO hardcodear; var de entorno / Workers
// DEV/staging: window.__MININODE_API_KEY__ set en index.html
function getApiKey() {
  return window.__MININODE_API_KEY__ || '';
}

function loadPrefs() {
  try { return JSON.parse(localStorage.getItem(LS_KEY)) || {}; } catch { return {}; }
}
function savePrefs(p) {
  try { localStorage.setItem(LS_KEY, JSON.stringify(p)); } catch {}
}

async function init() {
  await injectPartials();
  attachGoNavigation(document);

  // UI elements
  const $txt  = document.getElementById('wr-texto');
  const $size = document.getElementById('wr-size');
  const $tone = document.getElementById('wr-tone');
  const $lang = document.getElementById('wr-lang'); // oculto en v1
  const $gen  = document.getElementById('wr-generate');
  const $resBox = document.getElementById('wr-result-box');
  const $res  = document.getElementById('wr-result');
  const $err  = document.getElementById('wr-error');

  const $copy = document.getElementById('wr-copy');
  const $exportBtn = document.getElementById('wr-export');
  const $exportMenu = $exportBtn?.parentElement?.querySelector('.wr-menu');

  // Defaults
  const prefs = { tamaño: 'micro', tono: 'simple', idioma: 'es', ...loadPrefs() };
  $size.value = prefs.tamaño;
  $tone.value = prefs.tono;
  $lang.value = prefs.idioma;

  $size.addEventListener('change', () => { prefs.tamaño = $size.value; savePrefs(prefs); });
  $tone.addEventListener('change', () => { prefs.tono = $tone.value; savePrefs(prefs); });
  $lang.addEventListener('change', () => { prefs.idioma = $lang.value; savePrefs(prefs); });

  // Export menu
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
    // Futuro (docx/pdf nativos) → Ex.exportDocx(...) / Ex.exportPDF(...)
  });

  $copy.addEventListener('click', async () => {
    if (!$res?.textContent) return;
    await Ex.copyToClipboard($res.textContent);
    $copy.textContent = 'Copiado ✓';
    setTimeout(() => ($copy.textContent = 'Copiar'), 1200);
  });

  // Generate
  $gen.addEventListener('click', async () => {
  $err.classList.add('wr-hidden'); $err.textContent = '';
  $resBox.classList.add('wr-hidden'); $res.textContent = '';

  const raw = ($txt.value || '').trim();
  if (!raw) {
    $err.textContent = 'Por favor escribe algo en el input.';
    $err.classList.remove('wr-hidden');
    return;
  }

  // guías por tamaño/tono
  const size = $size.value || 'micro';
  const tone = $tone.value || 'simple';

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

  const composedPrompt =
    `Escribe un borrador en español con ${sizeGuide}${toneGuide}` +
    `Transforma estas ideas en un texto coherente y útil. ` +
    `Evita saludos genéricos. ` +
    `Contenido base:\n` + raw;

  $gen.disabled = true; $gen.textContent = 'Generando…';

  try {
    const resp = await fetch('/api/write/draft', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: composedPrompt, tone }),
    });

    const text = await resp.text();               // leemos texto para mejor debug
    if (!resp.ok) throw new Error(`Error ${resp.status}: ${text}`);

    let data; try { data = JSON.parse(text); } catch { data = { text }; }
    const draft = data?.text || data?.draft || data?.result || '';
    $res.textContent = draft || '[sin contenido]';
    $resBox.classList.remove('wr-hidden');
  } catch (e) {
    console.error(e);
    $err.textContent = String(e.message || e);
    $err.classList.remove('wr-hidden');
  } finally {
    $gen.disabled = false; $gen.textContent = 'Generar borrador';
  }
});


  // bloqueo UI durante la llamada
  $gen.disabled = true; $gen.textContent = 'Generando…';

  try {
    const resp = await fetch(API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Api-Key': getApiKey(),
      },
      body: JSON.stringify({
        prompt,
        tone: $tone.value || 'simple',
        // Campos listos para futuro
        size: $size.value || 'micro',
        lang: $lang.value || 'es',
        seo: false, // v1: manual oculto
      }),
    });

    if (!resp.ok) {
      const t = await resp.text();
      throw new Error(`Error ${resp.status}: ${t}`);
    }

    // intenta detectar el campo con texto
    const data = await resp.json();
    const draft = data?.text || data?.draft || data?.result || '';
    $res.textContent = draft || '[vacío]';

    $resBox.classList.remove('wr-hidden');
  } catch (err) {
    console.error(err);
    $err.textContent = 'No se pudo generar el borrador. Revisa tu conexión o la API Key.';
    $err.classList.remove('wr-hidden');
  } finally {
    $gen.disabled = false; $gen.textContent = 'Generar borrador';
  }
};


init();
