# Privacy Web - PRV-103 QA7

## Objetivo

Revisar ciegamente la calidad del clasificador semántico PRV-103 después de la muestra shadow de producción del 10-sep-2026.

La muestra shadow terminó con 30 sitios distintos que realizaron una llamada LLM. QA7 intenta reconstruir esos casos sin volver a llamar al LLM y producir un paquete para adjudicación independiente.

## Regla de reconstrucción

La telemetría shadow no retuvo el texto de los formularios por diseño de privacidad. Por eso QA7 no puede afirmar que una nueva captura sea byte a byte idéntica a la observada durante shadow.

Para reducir ese riesgo:

- se congelan los mismos 30 sitios antes de la recaptura;
- se usa el inspector actual de Mininode mediante navegación pública y pasiva;
- solo se consideran formularios personales con confianza `high`;
- se deduplica usando exclusivamente `heading`, `legend`, `introductory_text` y `submit_text`;
- un sitio entra al paquete ciego solo si la recaptura obtiene exactamente un HIGH deduplicado, igual que en el evento shadow original de ese sitio;
- si obtiene cero o más de uno, el sitio queda marcado como no reconstruible para comparación uno a uno.

## Paquete ciego

El Reviewer recibe únicamente:

- `blind_id`;
- `heading`;
- `legend`;
- `introductory_text`;
- `submit_text`.

No recibe URL, hostname, sector, campos del formulario, action URL, baseline ni salida shadow/LLM.

Clases permitidas: `concrete`, `generic`, `none`, `unknown`.

## Criterios congelados antes de la adjudicación

Se mantienen los gates de QA6 para evaluar al LLM contra la referencia independiente:

### PASS

- false concrete promotions = 0;
- false adverse `none` = 0;
- invalid outputs = 0;
- emitted precision >= 90%;
- coverage >= 70%;
- accuracy >= 80%;
- concrete recall >= 75%.

### PASS WITH OBSERVATIONS

- false concrete promotions = 0;
- false adverse `none` = 0;
- invalid outputs = 0;
- emitted precision >= 90%;
- coverage >= 60%;
- accuracy >= 70%;
- concrete recall >= 65%.

### NEEDS FIX

Cualquiera de estos casos:

- alguna falsa promoción a `concrete`;
- algún falso `none` adverso;
- salida inválida;
- métricas inferiores a PASS WITH OBSERVATIONS;
- patrón sistemático generalizable de error.

## Resultado

La adjudicación independiente se completó después de congelar el paquete ciego. Resultado formal: **NEEDS FIX** por un falso `concrete` (`QA7-019`).

La comparación completa y reproducible queda en `docs/privacy-prv103-qa7-result.md` y `backend/tests/domain_packs/privacy/prv103_semantic_benchmark/qa7_reference.json`.

Hallazgo principal: los 10 casos donde shadow discrepó del baseline fueron 10 mejoras confirmadas por la referencia independiente; el único error del shadow fue compartido con el baseline.

## Alcance

QA7 no cambia producción, scoring, framework, Evidence Contract, extractor ni reglas PRV-103. Solo genera evidencia de QA.

La salida se publica como artifact temporal de GitHub Actions. El paquete ciego fue adjudicado antes de comparar con las clases baseline/shadow observadas en producción.
