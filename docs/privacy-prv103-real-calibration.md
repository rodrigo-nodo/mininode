# W2.2b.3-QA - calibración real de PRV-103

## Resultado

**NEEDS FIX**

PRV-103 se calibró sobre un holdout real nuevo, separado de los sitios utilizados para diseñar W2.2b.2 y PRV-103.

La ejecución no mostró promociones falsas a `concrete`, pero sí un patrón repetido de clasificaciones demasiado adversas o demasiado conservadoras: finalidades que la revisión manual considera `concrete` o `generic` terminan como `none` o, en varios casos, como `generic` cuando eran `concrete`.

Resultado principal:

- 56 sitios nuevos intentados en cuatro lotes;
- 40 sitios con al menos una página analizada;
- 18 formularios personales HIGH revisados;
- 0 formularios MEDIUM observados;
- 1 clasificación automática `concrete`, correctamente `concrete` en revisión manual;
- `detected_precision = 100%` (1/1);
- 0 `false_concrete_promotion`;
- `exact_class_agreement = 38,9%` (7/18);
- 6 `missed_concrete`;
- 8 casos `false_adverse_none` (manual `concrete/generic`, producto `none`);
- 0 `medium_influenced_result`;
- 0 errores mecánicos de consolidación multi-form observados.

Según los criterios fijados antes de ejecutar el holdout, el patrón repetido de `none` incorrecto obliga a clasificar esta QA como **NEEDS FIX**.

## Línea base

| Campo | Valor |
|---|---|
| Fecha | 2026-09-01 |
| Main SHA evaluado | `e41c8d6324fb8e526ef4a6421f3e7030ac0fc7ea` |
| `framework_version` | `0.3` |
| `scoring_version` | `0.1` |
| `actions_version` | `2` |
| Evidence Contract interno | `v0.2` |
| Controles | 21 |
| Producción modificada durante QA | No |
| PRV-103 modificado durante QA | No |

## Ejecución

La calibración se ejecutó mediante un workflow temporal de GitHub Actions usando el Web Inspector y el pipeline productivo, sin mocks ni envío de formularios.

Runs:

1. https://github.com/rodrigo-nodo/mininode/actions/runs/33563245764
2. https://github.com/rodrigo-nodo/mininode/actions/runs/33563428165
3. https://github.com/rodrigo-nodo/mininode/actions/runs/33563615844
4. https://github.com/rodrigo-nodo/mininode/actions/runs/33563860085

Artifacts sanitizados:

| Lote | Artifact | ID |
|---|---|---:|
| 1 | `privacy-prv103-calibration` | `9822099051` |
| 2 | `privacy-prv103-calibration-batch2` | `9822172201` |
| 3 | `privacy-prv103-calibration-batch3` | `9822238686` |
| 4 | `privacy-prv103-calibration-batch4` | `9822325131` |

Todos tienen retención de siete días.

El workflow temporal se eliminó después de documentar esta calibración.

## Metodología

Por cada sitio se utilizó el fetcher real, extracción real, construcción del Evidence Contract y diagnóstico Privacy real.

No se:

- enviaron formularios;
- introdujeron datos personales;
- ejecutaron actions de formularios;
- autenticaron sesiones;
- modificaron reglas de PRV-103;
- agregaron regex o keywords;
- modificaron extractor, adapter o evaluator.

Por cada formulario personal observado se guardó únicamente evidencia sanitizada y acotada:

- URL sin query ni fragment;
- sector e idioma;
- índice;
- confianza personal HIGH/MEDIUM;
- `heading`;
- `legend`;
- `introductory_text`;
- `submit_text`;
- clase interna del producto;
- tipos/nombres/labels minimizados de campos.

## Holdout

Se partió con 12 sitios nuevos y se ampliaron lotes únicamente porque muchos sitios no exponían formularios personales en las páginas inspeccionables o bloqueaban la inspección. Ninguno de los sitios de W2.2b.2-QA se utilizó como holdout.

Resumen:

| Métrica | Resultado |
|---|---:|
| Sitios intentados | 56 |
| Sitios con páginas analizadas | 40 |
| Formularios personales HIGH | 18 |
| Formularios personales MEDIUM | 0 |
| Idiomas presentes en formularios adjudicados | Español e inglés |

La muestra final supera el mínimo práctico de 15 formularios reales. No se realizó tuning entre lotes: solo se buscaron sitios frescos adicionales para completar el denominador.

## Matriz manual vs producto

La etiqueta manual responde exclusivamente si los cuatro campos estructurados asociados al mismo formulario expresan una finalidad. No se utilizó `nearby_text` para rescatar casos.

| Caso | Sitio/formulario | Evidencia estructurada resumida | Producto | Manual | Acuerdo | Error |
|---|---|---|---|---|---|---|
| H02-1 | CleverIT / home | submit: “Transforma tu futuro digital ahora” | none | none | Sí | - |
| H02-2 | CleverIT / contact | submit: “Hablemos de tu proyecto” | none | concrete | No | missed_concrete / false_adverse_none |
| H07-1 | Shopify / checkout | sin evidencia estructurada | unknown | unknown | Sí | - |
| H12-1 | Zendesk / home | “14-day free trial…” + “Try for free” | none | concrete | No | missed_concrete / false_adverse_none |
| H12-2 | Zendesk / privacy notice | submit: “Subscribe” | none | generic | No | false_adverse_none |
| H13-1 | Kibernum | submit: “Conversemos” | none | generic | No | false_adverse_none |
| H18-1 | Chipax / contact | intro: “Nombre”; submit: “Escríbenos” | none | concrete | No | missed_concrete / false_adverse_none |
| H19-1 | Fintoc / home | “Completa este formulario y nos pondremos en contacto contigo…” | generic | concrete | No | missed_concrete |
| H19-2 | Fintoc / privacidad | mismo formulario visible | generic | concrete | No | missed_concrete |
| H19-3 | Fintoc / smart checkout | mismo formulario visible | generic | concrete | No | missed_concrete |
| H25-1 | monday.com | intro: “O”; submit: “Empezar” | none | generic | No | false_adverse_none |
| H25-2 | monday.com | submit: “Empezar” | none | generic | No | false_adverse_none |
| H26-1 | Intercom / contact sales | submit: “Next” | generic | generic | Sí | - |
| H35-1 | Zoom / contact sales | heading: “Cuéntenos un poco acerca de usted”; submit incluye “Registrarse” | concrete | concrete | Sí | - |
| H47-1 | Stripe / contact sales | heading: “Te llevamos al lugar adecuado”; submit: “Continuar” | generic | generic | Sí | - |
| H48-1 | Slack / contact sales | submit: “Enviar” | generic | generic | Sí | - |
| H50-1 | GitHub Enterprise / contact | legend: “I'm interested in”; submit: “Contact” | none | generic | No | false_adverse_none |
| H52-1 | Figma / contact | heading: “Contact sales”; submit: “Submit” | generic | generic | Sí | - |

### Nota sobre Fintoc

El mismo componente de formulario apareció en tres páginas distintas y se cuenta como tres formularios observados porque esa fue la unidad fijada antes del análisis.

La conclusión no depende de esa repetición. Si se deduplican dos de las tres apariciones de Fintoc:

- el acuerdo exacto continúa muy por debajo de 90%;
- permanecen múltiples `missed_concrete`;
- permanecen múltiples `false_adverse_none`;
- la decisión continúa siendo **NEEDS FIX**.

## Métricas

| Métrica | Resultado |
|---|---:|
| Formularios HIGH revisados | 18 |
| Formularios MEDIUM revisados | 0 |
| Producto concrete | 1 |
| Producto generic | 7 |
| Producto none | 9 |
| Producto unknown | 1 |
| Manual concrete | 7 |
| Manual generic | 9 |
| Manual none | 1 |
| Manual unknown | 1 |
| Exact class agreement | 7/18 = 38,9% |
| Detected precision | 1/1 = 100% |
| False concrete promotions | 0 |
| False generic promotions | 0 |
| Missed concrete | 6 |
| False adverse none | 8 |
| False unknown | 0 |
| Medium influenced results | 0 observados |
| Multi-form consolidation errors | 0 |
| Manual uncertain | 0 |

## Interpretación

### Señal positiva

La única promoción automática a `concrete` observada, Zoom, fue correcta. Por tanto, en este holdout no aparece el riesgo más grave que se quería evitar: declarar una finalidad concreta sin sustento.

### Problema principal

PRV-103 es demasiado restrictivo para expresiones reales frecuentes.

Los patrones que el producto no reconoce correctamente incluyen, entre otros:

- “Hablemos de tu proyecto”;
- “Try for free” junto a una prueba gratuita explícita;
- “Escríbenos”;
- “Completa este formulario y nos pondremos en contacto contigo…”;
- “Conversemos” y “Empezar” como contextos genéricos;
- “Contact” dentro de un formulario explícitamente orientado a contacto.

Esto genera dos efectos:

1. finalidad concreta real degradada a `generic` o `none`;
2. contexto genérico real degradado a `none`.

El segundo efecto es especialmente importante porque `none -> not_detected` afirma que existe evidencia estructurada pero no una finalidad reconocible. Esa afirmación resultó demasiado fuerte en varios formularios reales.

## Formularios MEDIUM

No apareció ningún formulario personal MEDIUM en el holdout recuperado.

Por lo tanto:

- no existe evidencia real nueva para confirmar o refutar el comportamiento MEDIUM;
- no se contabiliza como fallo;
- la protección HIGH/MEDIUM sigue respaldada por tests sintéticos, no por esta muestra real.

## Consolidación multi-form

Se observaron sitios con varios formularios HIGH, incluidos CleverIT, Zendesk, Fintoc y monday.com.

No se observó un fallo mecánico de la precedencia de consolidación: el aggregate fue consistente con las clases internas generadas por cada formulario.

Las discrepancias de sitio provienen de la clasificación semántica por formulario, no del algoritmo de precedencia multi-form.

## Asociación estructural

No se observó cross-form bleed que produjera una promoción positiva errónea.

Se registran como observaciones de extracción:

- Chipax produjo `introductory_text = "Nombre"`, que parece texto de campo más que una finalidad;
- monday.com produjo `introductory_text = "O"` en un formulario.

Ninguno produjo una falsa promoción, pero son buenos casos de regresión para una futura evolución del Evidence Contract/extractor si se decide revisarlo.

No se modifica W2.2b.2 en este PR.

## Regression reference - non-holdout

No se ejecutó.

La conclusión del holdout nuevo ya es concluyente y agregar sitios usados durante el diseño no mejoraría la independencia de la decisión.

## Decisión

Los criterios previos definían **NEEDS FIX** ante un patrón repetido de `false generic/none`.

El holdout presenta ese patrón:

- 8 `false_adverse_none`;
- 6 `missed_concrete`;
- acuerdo exacto 38,9%.

Aunque `detected_precision` fue 100% y no hubo `false_concrete_promotion`, el resultado no es suficientemente calibrado para cerrar PRV-103 como estable.

**Clasificación final: NEEDS FIX.**

## No tuning

Esta QA no modifica las reglas.

Se mantienen intactos:

- `_FORM_PURPOSE_*`;
- `_form_purpose_signal(...)`;
- `_form_purpose_evidence(...)`;
- precedencia;
- confianza;
- extractor;
- Evidence Contract;
- catálogo y scoring.

Esto evita ajustar el clasificador sobre el mismo holdout utilizado para medirlo.

## Versionado

Sin cambios:

- `framework_version = 0.3`;
- `scoring_version = 0.1`;
- `actions_version = 2`;
- Evidence Contract = `v0.2`;
- controles = 21.

## Recomendación

Mergear este PR únicamente como registro de QA con resultado **NEEDS FIX**.

El siguiente paso debe ser un PR separado:

**W2.2b.3-calibration-fix**

Ese PR puede revisar las discrepancias observadas y proponer una corrección pequeña y conservadora de la semántica `concrete / generic / none / unknown`.

Después del fix debe ejecutarse un **segundo holdout nuevo**, sin reutilizar estos formularios para medir la mejora final.

No avanzar todavía a PRV-104 adicional, destino externo (I) ni campos obligatorios (C) hasta cerrar esta recalibración de PRV-103.
