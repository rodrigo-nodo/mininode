export function attachGoNavigation(root = document) {
  root.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-go]');
    if (!btn) return;
    if (btn.disabled || btn.getAttribute('aria-disabled') === 'true') {   // ⬅️ respeta deshabilitado
      e.preventDefault();
      return;
    }
    const to = btn.getAttribute('data-go');
    if (to) window.location.href = to;
  });
}
