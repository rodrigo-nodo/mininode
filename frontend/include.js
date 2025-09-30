
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-include]').forEach(async el => {
    const src = el.getAttribute('data-include');
    try {
      const res = await fetch(src, { credentials:'same-origin' });
      if (!res.ok) throw new Error('HTTP '+res.status);
      el.outerHTML = await res.text();
    } catch (e) {
      console.error('Include failed', src, e);
    }
  });
});
