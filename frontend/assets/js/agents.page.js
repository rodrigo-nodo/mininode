import { injectPartials } from '/assets/js/core-partials.js';
import { attachGoNavigation } from '/assets/js/core-go-nav.js';

const ENABLE_AGENT_PAGES = true; // ⬅️ cuando existan las páginas, ponlo en true


(async function init() {
  await injectPartials();
  attachGoNavigation(document); // OK si además respeta aria-disabled/disabled

  if (!ENABLE_AGENT_PAGES) {
    const btns = document.querySelectorAll('#agents-landing .ag-btn[data-go]');
    btns.forEach((btn) => {
      btn.setAttribute('aria-disabled', 'true'); // accesibilidad
      btn.disabled = true;                       // apariencia + bloqueo nativo
    });
  }
})();
