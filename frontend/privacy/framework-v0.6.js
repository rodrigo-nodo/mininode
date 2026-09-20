const FORM_CONTROLS_V06 = [
  { code: 'PRV-101', name: 'Formularios que recopilan datos personales', informational: true },
  { code: 'PRV-102', name: 'Envío seguro del formulario' },
  { code: 'PRV-103', name: 'Finalidad visible del formulario', informational: true },
  { code: 'PRV-104', name: 'Información de privacidad asociada al formulario', informational: true },
];

const cookiesAreaV06 = privacyAreas.find((area) => area.name === 'Cookies');
if (cookiesAreaV06) {
  cookiesAreaV06.controls = [
    { code: 'PRV-201', name: 'Cookies observadas', informational: true },
  ];
}

const formsAreaV06 = privacyAreas.find((area) => area.name === 'Formularios');
if (formsAreaV06) {
  formsAreaV06.controls = FORM_CONTROLS_V06;
}

const reviewedScopeV06 = document.querySelector('.privacy-result__reviewed');
if (reviewedScopeV06) {
  reviewedScopeV06.textContent = 'Revisamos 21 puntos de tu sitio en 5 áreas.';
}

const detailScopeV06 = document.querySelector('.privacy-controls-detail summary small');
if (detailScopeV06) {
  detailScopeV06.textContent = '21 puntos en 5 áreas';
}

const INFORMATIONAL_LABELS_V06 = new Map([
  ['Bien', 'Detectado'],
  ['Puede mejorar', 'Parcialmente detectado'],
  ['Necesita atención', 'No detectado'],
  ['No pudimos revisarlo', 'No pudimos revisarlo'],
  ['No aplica', 'No aplica'],
]);

const relabelInformationalControlsV06 = () => {
  const areaSections = diagnosticControls.querySelectorAll('.privacy-control-area');
  const areaSummaries = diagnosticAreas.querySelectorAll('.privacy-area');

  privacyAreas.forEach((area, areaIndex) => {
    const section = areaSections[areaIndex];
    if (!section) {
      return;
    }

    const items = section.querySelectorAll('.privacy-control');
    area.controls.forEach((control, controlIndex) => {
      if (!control.informational) {
        return;
      }

      const state = items[controlIndex]?.querySelector('.privacy-state');
      if (!state) {
        return;
      }

      // PRV-201 used to return not_applicable. Preserve compatibility with
      // diagnostics produced by framework 0.10 while presenting the 0.11
      // observational semantics.
      if (control.code === 'PRV-201' && state.textContent === 'No aplica') {
        state.textContent = 'No detectado';
      }

      const informationalLabel = INFORMATIONAL_LABELS_V06.get(state.textContent);
      if (informationalLabel && state.textContent !== informationalLabel) {
        state.textContent = informationalLabel;
      }

      state.classList.remove(
        'privacy-state--good',
        'privacy-state--improve',
        'privacy-state--attention',
      );
      state.classList.add('privacy-state--neutral');
    });

    if (area.controls.length > 0 && area.controls.every((control) => control.informational)) {
      const areaState = areaSummaries[areaIndex]?.querySelector('.privacy-state');
      if (areaState) {
        areaState.textContent = 'Informativo';
        areaState.classList.remove(
          'privacy-state--good',
          'privacy-state--improve',
          'privacy-state--attention',
        );
        areaState.classList.add('privacy-state--neutral');
      }
    }
  });
};

const informationalObserverV06 = new MutationObserver(relabelInformationalControlsV06);
informationalObserverV06.observe(diagnosticControls, { childList: true, subtree: true });
