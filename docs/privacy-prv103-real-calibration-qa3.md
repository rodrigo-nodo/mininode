# W2.2b.3-QA3 - holdout final de PRV-103

## Resultado

**NEEDS FIX**

PRV-103 v0.5 se validó sobre un tercer holdout real e independiente.

El control mantuvo las propiedades de seguridad que más importan:

- 0 `false_concrete_promotions`;
- `detected_precision = 100%`;
- 0 `false_adverse_none`;
- 0 errores de consolidación multi-form;
- 0 problemas críticos de asociación estructural;
- no se observaron formularios MEDIUM influyendo en el resultado.

Sin embargo, el acuerdo global y el recall de `concrete` quedaron por debajo de los umbrales de cierre definidos para QA3:

- `exact_class_agreement = 54,8%`;
- `concrete_recall = 25,0%`;
- 13 `false_unknown`;
- 3 `missed_concrete`.

El patrón residual sigue siendo conservador, no peligroso: la mayor parte de los errores degrada finalidades reconocibles a `unknown`. Pero el patrón es sistemático y aparece incluso en expresiones genéricas frecuentes como `Send message`, `Connect with us`, `Contáctanos`, `Enviar Formulario` o `Confirmar`, además de tres finalidades concretas omitidas.

De acuerdo con los criterios predefinidos de QA3, PRV-103 todavía **no se cierra**.

## Línea base

| Campo | Valor |
|---|---|
| Fecha | 2026-09-02 |
| Main SHA evaluado | `c72312186dc6fa458af1c2692a1976576801abe7` |
| `framework_version` | `0.5` |
| `scoring_version` | `0.1` |
| `actions_version` | `2` |
| Evidence Contract interno | `v0.2` |
| Controles | 21 |
| Producción modificada durante QA3 | No |
| PRV-103 modificado durante QA3 | No |

El SHA base incluye cambios posteriores de Privacy Data sobre `main`, pero la versión de Privacy Web evaluada para PRV-103 permanece en framework `0.5`.

## Independencia del holdout

No se reutilizó ninguna organización usada en:

- W2.2b.2-QA;
- W2.2b.3-QA / QA1;
- W2.2b.3-QA2;
- los regression/tuning sets derivados de QA1 y QA2.

Se intentaron 85 organizaciones nuevas en tres lotes.

La selección se amplió hasta superar el mínimo de 15 formularios HIGH deduplicados y llegar a un tamaño suficiente para la decisión final, sin hacer tuning entre lotes.

## Ejecución

Se utilizó un workflow temporal de GitHub Actions con el pipeline productivo real:

- `WebFetcher`;
- extracción productiva;
- `build_evidence`;
- `run_privacy_diagnostic`;
- `_personal_form`;
- `_form_purpose_signal`.

Solo se realizaron inspecciones públicas GET.

No se:

- enviaron formularios;
- introdujeron datos;
- ejecutaron POST;
- autenticaron sesiones;
- crearon cuentas;
- eludieron protecciones.

### Runs usados para métricas

| Lote | Run | Artifact | Artifact ID |
|---|---|---|---:|
| 1 | https://github.com/rodrigo-nodo/mininode/actions/runs/33589892835 | `privacy-prv103-qa3` | `9831376438` |
| 2 | https://github.com/rodrigo-nodo/mininode/actions/runs/33590097338 | `privacy-prv103-qa3-batch2` | `9831436089` |
| 3 | https://github.com/rodrigo-nodo/mininode/actions/runs/33590252305 | `privacy-prv103-qa3-batch3` | `9831502361` |

Todos los artifacts fueron sanitizados y configurados con retención de siete días.

También se produjo un run técnico duplicado al crear inicialmente el workflow y luego el documento:

- run `33589888755`;
- artifact `9831380552`.

Ese run contiene el mismo lote inicial y **se excluyó completamente de las métricas** para evitar doble conteo.

## Cobertura

| Métrica | Resultado |
|---|---:|
| Sitios intentados | 85 |
| Sitios con al menos una página analizada | 48 |
| Formularios personales raw | 40 |
| Formularios HIGH raw | 40 |
| Formularios MEDIUM raw | 0 |
| Formularios personales deduplicados | 31 |
| Formularios HIGH deduplicados | 31 |
| Formularios MEDIUM deduplicados | 0 |

## Deduplicación

Las métricas principales usan 31 formularios HIGH deduplicados.

Se colapsaron únicamente componentes claramente repetidos dentro de la misma organización:

- Netlify: el mismo footer `Subscribe` observado en tres páginas se contó una vez;
- PagerDuty: dos formularios idénticos con `Submit` se contaron una vez;
- ActiveCampaign: tres componentes lógicos repetidos entre contacto y privacidad se deduplicaron por pares:
  - `Request your demo`;
  - `Submit`;
  - `Free 14-day trial with email sign-up / Get started`;
- Hites: los componentes repetidos `Iniciar sesión`, `SUBSCRIBIRME` y `CONFIRMAR` entre contacto y privacidad se contaron una vez cada uno.

No se deduplicaron los tres formularios USM con `Enviar Formulario`, porque aparecen en páginas/audiencias distintas y no existe evidencia suficiente para afirmar que sean el mismo componente lógico.

## Etiquetado manual

La adjudicación manual usó exclusivamente:

- `heading`;
- `legend`;
- `introductory_text`;
- `submit_text`;

del mismo formulario.

No se utilizaron:

- fields para inferir finalidad;
- action URL;
- page title;
- nearby_text;
- conocimiento externo del negocio.

## Matriz producto/manual - HIGH deduplicados

| Caso | Evidencia estructurada resumida | Producto | Manual | Acuerdo | Observación |
|---|---|---|---|---|---|
| R01 Linear | `Send message` | unknown | generic | No | false_unknown |
| R02 Vercel | `Talk to Vercel` | unknown | generic | No | false_unknown |
| R03 Netlify newsletter | `Subscribe` | generic | generic | Sí | - |
| R03 Netlify sales | `Talk to Netlify` | unknown | generic | No | false_unknown |
| R06 PagerDuty | `Submit` | generic | generic | Sí | - |
| R07 Splunk | `Find expert and technical advisor support` + `Send My Question` | unknown | concrete | No | missed_concrete / false_unknown |
| R09 Grafana submit | `Submit` | generic | generic | Sí | - |
| R09 Grafana subscribe | `Subscribe` | generic | generic | Sí | - |
| R13 BrowserStack | `Submit` | generic | generic | Sí | - |
| R16 Airbyte | `Connect with us` | unknown | generic | No | false_unknown |
| R18 Alation | `Submit` | generic | generic | Sí | - |
| R20 Informatica | `Submit` | generic | generic | Sí | - |
| R29 UDP | `Contáctanos` + `NOMBRE COMPLETO *` | unknown | generic | No | false_unknown |
| R39 RudderStack | `Submit` | generic | generic | Sí | - |
| R46 Dynatrace | `Contact us` + `Get In Touch With` + `Submit` | generic | generic | Sí | - |
| R60 ActiveCampaign demo | `Request your demo` | concrete | concrete | Sí | - |
| R60 ActiveCampaign submit | `Submit` | generic | generic | Sí | - |
| R60 ActiveCampaign trial | `Free 14-day trial with email sign-up` + `Get started` | generic | concrete | No | missed_concrete |
| R63 Gorgias demo | `Tell us a bit more !` + `Step 1 of 5` | unknown | generic | No | false_unknown |
| R63 Gorgias privacy | sin structured purpose evidence | unknown | unknown | Sí | - |
| R69 Neon | `Submit` | generic | generic | Sí | - |
| R72 WorkOS | `Submit` | generic | generic | Sí | - |
| R74 Wiz | `Contact Sales` | generic | generic | Sí | - |
| R79 Hites login | `Iniciar sesión` | unknown | concrete | No | missed_concrete / false_unknown |
| R79 Hites send | `Enviar` | generic | generic | Sí | - |
| R79 Hites subscribe | `SUBSCRIBIRME` | unknown | generic | No | false_unknown |
| R79 Hites confirm | `CONFIRMAR` | unknown | generic | No | false_unknown |
| R80 USM home | `Enviar Formulario` | unknown | generic | No | false_unknown |
| R80 USM alumnos | `Enviar Formulario` | unknown | generic | No | false_unknown |
| R80 USM profesores/funcionarios | `Enviar Formulario` | unknown | generic | No | false_unknown |
| R81 UdeC | `Formulario de contacto` + `También se puede comunicar con nosotros mediante el siguiente formulario` + `Enviar` | generic | generic | Sí | - |

## Distribución de clases - HIGH deduplicados

### Producto

| Clase | Cantidad |
|---|---:|
| concrete | 1 |
| generic | 16 |
| none | 0 |
| unknown | 14 |

### Manual

| Clase | Cantidad |
|---|---:|
| concrete | 4 |
| generic | 26 |
| none | 0 |
| unknown | 1 |

## Métricas

| Métrica | Resultado |
|---|---:|
| `exact_class_agreement` | 17/31 = **54,8%** |
| `detected_precision` | 1/1 = **100%** |
| `concrete_recall` | 1/4 = **25,0%** |
| `generic_precision` | 15/16 = **93,8%** |
| `none_precision` | N/A - 0 product_none |
| `unknown_rate` | 14/31 = **45,2%** |
| `false_concrete_promotions` | **0** |
| `false_generic_promotions` | **0** |
| `false_adverse_none` | **0** |
| `false_unknown` | **13** |
| `missed_concrete` | **3** |
| `medium_influenced_results` | **0** |
| `multi_form_consolidation_errors` | **0** |
| `evidence_association_problems` | **0 críticos** |
| `manual_uncertain` | **0** |

## MEDIUM

No se observaron formularios MEDIUM en el holdout QA3.

Por lo tanto no apareció ningún `medium_influenced_result`.

La protección MEDIUM sigue cubierta por pruebas sintéticas/regresiones existentes, pero QA3 no agregó una observación real nueva para ese estado.

## Multi-form

La consolidación observada fue consistente con la precedencia vigente.

Ejemplos:

- Netlify: `generic + unknown` consolidó a `not_evaluable`;
- ActiveCampaign: `concrete + generic` consolidó a `partial`;
- Hites: `unknown + generic` consolidó a `not_evaluable`;
- USM: `unknown` consolidó a `not_evaluable`.

No se observaron errores de consolidación multi-form.

## Asociación estructural

No se observó contaminación cross-form que alterara una clasificación.

En UDP apareció `NOMBRE COMPLETO *` como `introductory_text` junto al heading `Contáctanos`. Se documenta como ruido estructural conservador del mismo formulario, pero no corresponde a evidencia de otro formulario ni produjo una promoción incorrecta.

No se clasifica como problema crítico de asociación.

## Qué funcionó

Las dos propiedades más riesgosas permanecen controladas:

1. PRV-103 no inventó finalidades concretas:
   - 0 false concrete;
   - detected precision 100%.

2. El fix previo de `none -> unknown` sigue funcionando:
   - 0 product_none;
   - 0 false adverse none.

Eso confirma que el control es conservador.

## Problema residual

El fallo sistemático está concentrado en `unknown`.

Trece de catorce `product_unknown` tenían una finalidad manual reconocible.

Omisiones genéricas frecuentes:

- `Send message`;
- `Talk to <organización>`;
- `Connect with us`;
- `Contáctanos`;
- `Tell us a bit more`;
- `SUBSCRIBIRME`;
- `CONFIRMAR`;
- `Enviar Formulario`.

Omisiones concretas:

- soporte experto + envío de pregunta;
- free trial + get started;
- iniciar sesión.

El patrón es suficientemente generalizable y repetido para no tratarlo como una colección de frases raras aisladas.

## Comparación direccional QA1 / QA2 / QA3

| Métrica | QA1 v0.3 | QA2 v0.4 | QA3 v0.5 |
|---|---:|---:|---:|
| Exact agreement | 38,9% | 47,1% | **54,8%** |
| Detected precision | 100% | 100% | **100%** |
| Concrete recall | N/D | 14,3% | **25,0%** |
| False concrete promotions | 0 | 0 | **0** |
| False adverse none | 8 | 0 | **0** |
| Missed concrete | 6 | 6 | **3** |

La comparación es solo direccional: cada QA utiliza un holdout distinto.

La evolución muestra mejora sostenida en acuerdo y recall, y eliminación total del patrón adverso de `none`. Sin embargo, QA3 no alcanza todavía los criterios de cierre fijados antes de observar este holdout.

## Aplicación de los criterios de QA3

### PASS

Requería, entre otros:

- exact agreement >= 80%;
- concrete recall >= 60%.

No se cumple.

### PASS WITH OBSERVATIONS

Requería:

- exact agreement >= 65%;
- concrete recall >= 45%;
- y solo omisiones conservadoras restantes.

Las condiciones de seguridad sí se cumplen, pero:

- exact agreement = 54,8%;
- concrete recall = 25,0%.

No se cumple.

### NEEDS FIX

Los criterios permitían NEEDS FIX cuando existiera:

- exact agreement < 65% junto con patrón sistemático;
- concrete recall < 45% junto con omisiones claramente generalizables.

Ambas condiciones ocurren.

**Clasificación final: NEEDS FIX.**

## Stop rule

QA3 era el último ciclo planificado si terminaba:

- PASS;
- PASS WITH OBSERVATIONS.

No ocurrió.

El resultado NEEDS FIX se debe a un patrón sistemático y generalizable, no a una o dos frases atípicas. Por lo tanto cumple la excepción definida previamente para justificar un cambio adicional inmediato.

Esto **no autoriza tuning dentro de este PR**.

## No tuning

Durante QA3 no se modificaron:

- `_FORM_PURPOSE_*`;
- `_form_purpose_signal(...)`;
- `_form_purpose_evidence(...)`;
- `_without_form_purpose_noise(...)`;
- regex;
- listas generic/noise;
- precedencia;
- confidence;
- extractor;
- evaluator;
- catálogo;
- scoring;
- actions.

## Versionado

Sin cambios:

- `framework_version = 0.5`;
- `scoring_version = 0.1`;
- `actions_version = 2`;
- Evidence Contract = `v0.2`;
- controles = 21.

No se creó framework v0.6.

## Decisión de producto

PRV-103 **no queda cerrado** con QA3.

La razón no es riesgo de falsas afirmaciones positivas: esa parte se comportó bien.

La razón es utilidad contextual insuficiente frente a frases muy comunes. Casi la mitad de los formularios evaluados termina `unknown`, y buena parte de ellos tiene una finalidad genérica comprensible para una persona.

El siguiente paso, si se continúa con PRV-103, debe ser un ajuste pequeño y separado centrado en patrones genéricos frecuentes y en las tres omisiones concretas generalizables observadas aquí, manteniendo precisión > recall.

No se debe modificar este documento histórico ni hacer tuning sobre este mismo holdout.

## Estado final

- resultado: **NEEDS FIX**;
- PRV-103 cerrado: **No**;
- workflow temporal: **eliminado**;
- producción modificada: **No**;
- framework: **0.5**;
- scoring: **0.1**;
- actions: **2**.
