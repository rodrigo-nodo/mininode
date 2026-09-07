(() => {
  function privacyRoot() {
    return document.querySelector('#privacy-data');
  }

  function stageByTitle(title) {
    const root = privacyRoot();
    if (!root) return null;
    return [...root.querySelectorAll('.pd-next-stage')]
      .find(section => section.querySelector('h2')?.textContent.trim() === title) || null;
  }

  function activateAccessStageWhenReady() {
    const root = privacyRoot();
    if (!root?.querySelector('.pd-actions-view')) return;

    const conservation = stageByTitle('Conservación');
    const access = stageByTitle('Accesos');
    if (!conservation || !access) return;

    const conservationDetail = [...conservation.querySelectorAll(':scope > p')]
      .find(item => !item.classList.contains('eyebrow'))?.textContent.trim();
    const conservationReviewed = conservation.classList.contains('pd-next-stage--done')
      || conservationDetail === 'Revisada en todas las actividades de tu mapa.';
    if (!conservationReviewed) return;

    const accessDetail = [...access.querySelectorAll(':scope > p')]
      .find(item => !item.classList.contains('eyebrow'))?.textContent.trim();
    if (accessDetail === 'Revisada en todas las actividades de tu mapa.') return;

    let button = access.querySelector('button');
    if (!button) {
      button = document.createElement('button');
      button.className = 'btn btn--primary';
      button.type = 'button';
      access.append(button);
    }
    button.disabled = false;
    button.textContent = access.querySelector('[data-access-progress]') ? 'Continuar accesos' : 'Comenzar';
    button.dataset.phase2AccessStart = '';
  }

  function schedule() {
    setTimeout(activateAccessStageWhenReady, 0);
  }

  document.addEventListener('click', schedule, true);
  document.addEventListener('DOMContentLoaded', schedule);
  window.addEventListener('load', schedule);
})();
