const FORM_CONTROLS_V06 = [
  { code: 'PRV-101', name: 'Formularios que recopilan datos personales', informational: true },
  { code: 'PRV-102', name: 'Envío seguro del formulario' },
  { code: 'PRV-103', name: 'Finalidad visible del formulario', informational: true },
  { code: 'PRV-104', name: 'Información de privacidad asociada al formulario' },
];

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
