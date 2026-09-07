(() => {
  const TOKEN_KEY = 'mininode_privacy_data_token';
  const API_PREFIX = '/api/privacy/data';

  function phaseOneActivityComplete(activity) {
    const answers = activity?.answers || {};
    const requiredLists = [
      answers.people_categories,
      answers.personal_data_types,
      answers.purposes,
      answers.data_origins,
      answers.storage_locations,
    ];
    if (requiredLists.some(values => !Array.isArray(values) || values.length === 0)) return false;
    if (answers.may_include_minors == null) return false;
    if (answers.has_third_parties == null) return false;
    if (!activity.data_context || activity.data_context === 'unconfirmed') return false;
    if (answers.has_third_parties === true) {
      if (!Array.isArray(answers.third_parties) || answers.third_parties.length === 0) return false;
      if (answers.third_parties.some(third => !Array.isArray(third.relationships) || third.relationships.length === 0)) return false;
    }
    return true;
  }

  function phaseOneComplete(activities) {
    return Array.isArray(activities) && activities.length > 0 && activities.every(phaseOneActivityComplete);
  }

  function triggerWizardAction(go) {
    const root = document.querySelector('#privacy-data');
    if (!root) return false;
    const control = document.createElement('button');
    control.type = 'button';
    control.hidden = true;
    control.dataset.go = go;
    root.append(control);
    control.click();
    control.remove();
    return true;
  }

  function openCompletedMapWhenReady() {
    let attempts = 0;
    const timer = setInterval(() => {
      attempts += 1;
      const root = document.querySelector('#privacy-data');
      if (root?.querySelector('.pd-result-nav')) {
        clearInterval(timer);
        return;
      }
      if (root?.querySelector('[data-go="resume"]')) {
        clearInterval(timer);
        triggerWizardAction('retention-back');
        setTimeout(() => triggerWizardAction('result-map'), 0);
        return;
      }
      if (attempts >= 120) clearInterval(timer);
    }, 50);
  }

  async function init() {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return;
    try {
      const response = await fetch(`${API_PREFIX}/maps/${token}/activities`, {
        headers: {'Content-Type': 'application/json'},
      });
      if (!response.ok) return;
      const activities = await response.json();
      if (!phaseOneComplete(activities)) return;
      openCompletedMapWhenReady();
    } catch {
      // The wizard owns recovery/error handling. Re-entry should never block it.
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, {once: true});
  else init();
})();
