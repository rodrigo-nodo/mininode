export async function injectPartials() {
  const includes = document.querySelectorAll('[data-include]');
  await Promise.all([...includes].map(async (node) => {
    const url = node.getAttribute('data-include');
    if (!url) return;
    try {
      const res = await fetch(url, { credentials: 'include' });
      if (res.ok) node.innerHTML = await res.text();
    } catch(e){ console.warn('No se pudo cargar', url, e); }
  }));
}
