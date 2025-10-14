import { injectPartials } from '/assets/js/core-partials.js';
import { attachGoNavigation } from '/assets/js/core-go-nav.js';
import * as Ex from '/assets/js/util-export.js';

const LS_KEY = 'mininode_write_prefs_v1';
const API_URL = '/api/write/draft'; // proxy en Cloudflare Pages
const ANALYZE_URL = 'https://api.mininode.io/analisis/summary';
const analyzeToggle = document.getElementById('analyzeToggle');
const urlInfo = document.getElementById('urlInfo');

let userTouchedToggle = false;
analyzeToggle.addEventListener('change', () => { userTouchedToggle = true; });

function extractUrls(text) {
  const re = /\bhttps?:\/\/[^\s)]+/gi;
  const found = text.match(re) || [];
  return Array.from(new Set(found.map(u => u.trim()))).slice(0, 3);
}

// AUTO-ON cuando se escribe el prompt
promptInput.addEventListener('input', () => {
  const urls = extractUrls(promptInput.value);
  urlInfo.textContent = `URLs detectadas: ${urls.length}`;
  if (!userTouchedToggle) analyzeToggle.checked = urls.length > 0;
});

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
  const $txt     = document.getElementById('wr-texto');
  const $size    = document.getElementById('wr-size');
  const $tone    = document.getElementById('wr-tone');
  const $lang    = document.getElementById('wr-lang'); // oculto en v1
  const $gen     = document.getElementById('wr-generate');
  const $resBox  = document.getElementById('wr-result-box');
  const $res     = document.getElementById('wr-result');
  const $err     = document.getElementById('wr-error');
  const $copy    = document.getElementById('wr-copy');
  const $exportBtn  = document.getElementById('wr-export');
  const $exportMenu = $exportBtn?.parentElement?.querySelector('.wr-menu');

  // Defaults
  const prefs = { tamaño: 'micro', tono: 'simple', idioma: 'es', ...loadPrefs() };
  if ($size) $size.value = prefs.tamaño;
  if ($tone) $tone.value = prefs.tono;
  if ($lang) $lang.value = prefs.idioma;

  // UI limpia al cargar (NO mostrar error ni resultado)
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
      `Evita saludos genéricos.\n` +
      `Contenido base:\n` + raw;

    $gen.disabled = true; 
    $gen.textContent = 'Generando…';

    try {
      const resp = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: composedPrompt, tone }), // ← SIEMPRE enviar prompt + tone
      });

      const text = await resp.text();
      if (!resp.ok) throw new Error(`Error ${resp.status}: ${text}`);

      let data; try { data = JSON.parse(text); } catch { data = { text }; }
      const draft = data?.text || data?.draft || data?.result || '';
      $res.textContent = draft || '[sin contenido]';
      $resBox.classList.remove('wr-hidden');
    } catch (e) {
      $err.textContent = String(e.message || e);
      $err.classList.remove('wr-hidden');
    } finally {
      $gen.disabled = false; 
      $gen.textContent = 'Generar borrador';
    }
  });

}

init();
