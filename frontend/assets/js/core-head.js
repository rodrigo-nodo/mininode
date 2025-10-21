// Inject common head assets/meta with proper relative paths
(function(){
  function relPrefix(){
    try{
      const self = document.currentScript || Array.from(document.scripts).find(s => (s.getAttribute && /assets\/js\/core-head\.js$/.test(s.getAttribute('src')||'')));
      const srcAttr = self && self.getAttribute && self.getAttribute('src');
      if (srcAttr && /assets\/js\/core-head\.js$/.test(srcAttr)) {
        return srcAttr.replace(/assets\/js\/core-head\.js$/, ''); // e.g., '../../'
      }
    }catch{}
    try{
      const path = (location.pathname || '/').replace(/\\/g,'/');
      const mark = '/frontend/';
      const i = path.toLowerCase().lastIndexOf(mark);
      if (i >= 0) {
        const within = path.substring(i + mark.length);
        const segs = within.split('/').filter(Boolean);
        const depth = Math.max(0, segs.length - 1);
        return depth === 0 ? '' : '../'.repeat(depth);
      }
    }catch{}
    return '';
  }
  async function inject(){
    const prefix = relPrefix();
    const url = `${prefix}partials/head-common.html`;
    try{
      const res = await fetch(url, { credentials:'same-origin' });
      if(!res.ok) return;
      const html = await res.text();
      const tmp = document.createElement('div');
      tmp.innerHTML = html;
      // Rewrite data-href and data-content-root
      tmp.querySelectorAll('[data-href]').forEach(el => {
        const p = el.getAttribute('data-href');
        if (p) el.setAttribute('href', prefix + p);
        el.removeAttribute('data-href');
      });
      tmp.querySelectorAll('[data-content-root]').forEach(el => {
        const p = el.getAttribute('data-content-root');
        if (p) el.setAttribute('content', prefix + p);
        el.removeAttribute('data-content-root');
      });
      // Append to head
      while(tmp.firstChild){ document.head.appendChild(tmp.firstChild); }
    }catch(e){ /* silent */ }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inject);
  } else {
    inject();
  }
})();
