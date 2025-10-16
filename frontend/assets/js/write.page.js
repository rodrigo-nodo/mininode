import { injectPartials } from '/assets/js/core-partials.js';
import { attachGoNavigation } from '/assets/js/core-go-nav.js';
import * as Ex from '/assets/js/util-export.js';

const LS_KEY = 'mininode_write_prefs_v1';
const API_URL = '/api/write/draft';
const ANALYZE_PROXY = '/api/analyze/summary';
const ANALYZE_URL = 'https://api.mininode.io/analyze/summary';

function extractUrls(text) {
  const re = /\bhttps?:\/\/[^\s)]+/gi;
  const found = (text || '').match(re) || [];
  const cleaned = found.map(u => u.trim().replace(/[),.;]+$/, ''));
  return Array.from(new Set(cleaned)).slice(0, 3);
}

function loadPrefs() {
  try { return JSON.parse(localStorage.getItem(LS_KEY)) || {}; } catch { return {}; }
}
function savePrefs(p) {
  try { localStorage.setItem(LS_KEY, JSON.stringify(p)); } catch {}
}

// Simple local fallback generator when API is unavailable
function localDraft(text, { tone = 'simple', size = 'micro', contextMd = '' } = {}) {
  const normalize = (s) => (s || '')
    .replace(/\r\n|\r|\n/g, '\n')
    .split('\n')
    .map(line => line.trim().replace(/^[-*•]\s+/, ''))
    .filter(Boolean)
    .join(' ')
    .replace(/\s+/g, ' ')
    .trim();

  let body = normalize(text);
  if (!body) return '';

  const toneLead = tone === 'formal' ? 'En términos precisos, ' : tone === 'inspirador' ? 'Enfaticemos el impacto: ' : '';
  const caps = { micro: 180, medio: 450, largo: 750 };
  const cap = caps[size] || 180;
  const words = body.split(' ');
  if (words.length > cap) body = words.slice(0, cap).join(' ') + '…';

  let out = toneLead + body;
  if (contextMd) {
    const ctx = normalize(contextMd).replace(/#+\s*/g, '');
    out = `${ctx ? ctx + '\n\n' : ''}${out}`;
  }
  return out;
}

async function analyzeOne(url, lang = 'es') {
  const body = { urls: [url], scope: 'page', lang };
  // Try same-origin proxy first
  try {
    const r = await fetch(ANALYZE_PROXY, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    if (r.ok) {
      const d = await r.json();
      return d.text || d.result || d.output || d.summary || d.resumen || '';
    }
  } catch (_) { /* fall through */ }

  // Fallback: direct endpoint with API key if available
  let key = '';
  try {
    key = (localStorage.getItem('MININODE_API_KEY') || window.__MININODE_API_KEY__ || '').trim();
  } catch {}
  if (!key) return '';

  try {
    const rr = await fetch(ANALYZE_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Api-Key': key },
      body: JSON.stringify(body)
    });
    if (!rr.ok) return '';
    const dd = await rr.json();
    return dd.text || dd.result || dd.output || dd.summary || dd.resumen || '';
  } catch (_) {
    return '';
  }
}

async function init() {
  await injectPartials();
  attachGoNavigation(document);

  const analyzeToggle = document.getElementById('analyzeToggle');
  const urlInfo = document.getElementById('urlInfo');

  const $txt    = document.getElementById('wr-texto');
  const $size   = document.getElementById('wr-size');
  const $tone   = document.getElementById('wr-tone');
  const $lang   = document.getElementById('wr-lang'); // hidden in v1
  const $gen    = document.getElementById('wr-generate');
  const $resBox = document.getElementById('wr-result-box');
  const $res    = document.getElementById('wr-result');
  const $err    = document.getElementById('wr-error');
  const $copy   = document.getElementById('wr-copy');
  const $exportBtn  = document.getElementById('wr-export');
  const $exportMenu = $exportBtn?.parentElement?.querySelector('.wr-menu');

  // Defaults
  const prefs = { tamano: 'micro', tono: 'simple', idioma: 'es', ...loadPrefs() };
  if ($size) $size.value = prefs.tamano;
  if ($tone) $tone.value = prefs.tono;
  if ($lang) $lang.value = prefs.idioma;

  // Clean UI
  if ($err)   { $err.textContent = ''; $err.classList.add('wr-hidden'); }
  if ($resBox){ $resBox.classList.add('wr-hidden'); }
  if ($res)   { $res.textContent = ''; }
  if (urlInfo) { urlInfo.textContent = ''; urlInfo.classList.add('wr-hidden'); }

  // Persist basic prefs
  $size?.addEventListener('change', () => { prefs.tamano = $size.value; savePrefs(prefs); });
  $tone?.addEventListener('change', () => { prefs.tono   = $tone.value; savePrefs(prefs); });
  $lang?.addEventListener('change', () => { prefs.idioma = $lang.value; savePrefs(prefs); });

  // URL detection feedback
  $txt?.addEventListener('input', () => {
    const urls = extractUrls($txt.value);
    if (urls.length > 0) {
      if (urlInfo) {
        urlInfo.textContent = `URLs detectadas: ${urls.length}`;
        urlInfo.classList.remove('wr-hidden');
      }
      if (analyzeToggle) analyzeToggle.checked = true; // keep in sync (even if hidden)
    } else {
      if (urlInfo) {
        urlInfo.textContent = '';
        urlInfo.classList.add('wr-hidden');
      }
      if (analyzeToggle) analyzeToggle.checked = false;
    }
  });

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

  // Copy
  $copy?.addEventListener('click', async () => {
    if (!$res?.textContent) return;
    await Ex.copyToClipboard($res.textContent);
    $copy.textContent = 'Copiado';
    setTimeout(() => ($copy.textContent = 'Copiar'), 1200);
  });

  // Generate
  $gen?.addEventListener('click', async () => {
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
      micro: '120-180 palabras, 1-2 parrafos. ',
      medio: '300-500 palabras, secciones cortas (H2). ',
      largo: '600-800 palabras, estructura clara con H2/H3. ',
    }[size];

    const toneGuide = {
      simple: 'tono claro y directo, sin jergas. ',
      formal: 'tono formal y preciso. ',
      inspirador: 'tono motivador con lenguaje positivo. ',
      tecnico: 'tono tecnico y especifico cuando corresponda. ',
    }[tone] || '';

    const basePrompt =
      `Escribe un borrador en español con ${sizeGuide}${toneGuide}` +
      `Transforma estas ideas en un texto coherente y util. ` +
      `Evita saludos genericos.\n` +
      `Contenido base:\n` + raw;

    $gen.disabled = true;
    $gen.textContent = 'Generando...';

    try {
      // Analyze URLs first if any (never blocks on failure)
      let contextMd = '';
      const urls = extractUrls(raw);
      if (urls.length) {
        for (const u of urls) {
          $gen.textContent = `Analizando: ${u}`;
          const summary = await analyzeOne(u, lang);
          if (summary && summary.trim()) contextMd += `#### ${u}\n${summary}\n\n`;
        }
      }

      const composedPrompt = contextMd
        ? `### Contexto (resumen de URLs)\n${contextMd}---\n\n${basePrompt}`
        : basePrompt;

      // Draft generation with graceful fallback
      let draft = '';
      try {
        $gen.textContent = 'Redactando...';
        const resp = await fetch(API_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: composedPrompt, tone })
        });

        const text = await resp.text();
        if (!resp.ok) throw new Error(`Error ${resp.status}: ${text}`);

        let data; try { data = JSON.parse(text); } catch { data = { text }; }
        draft = data?.text || data?.draft || data?.result || '';
      } catch (_) {
        draft = localDraft(raw, { tone, size, contextMd });
      }

      $res.textContent = draft || '[sin contenido]';
      $resBox.classList.remove('wr-hidden');
      $gen.textContent = 'Listo';
    } catch (e) {
      $err.textContent = String(e.message || e);
      $err.classList.remove('wr-hidden');
    } finally {
      setTimeout(() => { $gen.textContent = 'Generar borrador'; $gen.disabled = false; }, 250);
    }
  });
}

init();
