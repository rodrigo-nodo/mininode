
document.addEventListener('DOMContentLoaded', async () => {
  const nodes = Array.from(document.querySelectorAll('[data-include]'));
  const includeSrcs = nodes.map(n => n.getAttribute('data-include') || '');

  await Promise.all(nodes.map(async el => {
    const src = el.getAttribute('data-include');
    try {
      const res = await fetch(src, { credentials:'same-origin' });
      if (!res.ok) throw new Error('HTTP '+res.status);
      el.outerHTML = await res.text();
    } catch (e) {
      console.error('Include failed', src, e);
    }
  }));

  // After all includes, normalize relative links/assets in header/footer
  try {
    // Prefer deriving prefix from this script tag's src (robust for file://)
    let pre = '';
    try {
      const self = document.currentScript || Array.from(document.scripts).find(s => (s.getAttribute && /(^|\/)include\.js$/.test(s.getAttribute('src')||'')));
      const srcAttr = self && self.getAttribute && self.getAttribute('src');
      if (srcAttr && /(^|\/)include\.js$/.test(srcAttr)) {
        pre = srcAttr.replace(/include\.js$/, '');
      }
    } catch {}

    // Fallback: infer from include path (e.g., ../partials/header-nav.html)
    if (!pre) {
      const p = includeSrcs.find(s => s.includes('partials/')) || '';
      if (p) pre = p.slice(0, p.indexOf('partials/'));
    }

    // Last fallback: location-based heuristic
    if (!pre) {
      const path = (location.pathname||'/').replace(/\\/g,'/');
      const mark = '/frontend/';
      const i = path.toLowerCase().lastIndexOf(mark);
      if (i >= 0) {
        const within = path.substring(i + mark.length);
        const segs = within.split('/').filter(Boolean);
        const depth = Math.max(0, segs.length - 1);
        pre = depth===0? '' : '../'.repeat(depth);
      }
    }

    // data-rel on anchors/imgs
    document.querySelectorAll('[data-rel]').forEach(el => {
      const rel = el.getAttribute('data-rel');
      if (!rel) return;
      if (el.tagName === 'IMG') el.setAttribute('src', pre + rel);
      else el.setAttribute('href', pre + rel);
    });

    // footer year
    const y = document.getElementById('year');
    if (y) y.textContent = new Date().getFullYear();

    // script[data-src] loader (footer)
    document.querySelectorAll('script[data-src]').forEach(s => {
      const src = s.getAttribute('data-src');
      if (src && !s.src) s.src = pre + src;
    });
  } catch (e) {
    console.warn('Relative normalization failed', e);
  }
});
