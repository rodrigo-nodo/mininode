# W2.2b.3-QA2 - segundo holdout real de PRV-103

## Resultado

**NEEDS FIX**

PRV-103 v0.4 se validó sobre un segundo holdout real, separado tanto de W2.2b.2-QA como del holdout utilizado para diseñar y calibrar v0.3/v0.4.

El cambio de semántica `none -> unknown` corrigió el problema adverso más importante observado en QA1: en QA2 no apareció ningún `false_adverse_none`. También se mantuvo la precisión de las promociones a `concrete`: el único `product_concrete` fue correcto.

Sin embargo, la discriminación entre `concrete`, `generic` y `unknown` sigue siendo insuficiente para cerrar PRV-103 como calibrado:

- 17 formularios HIGH deduplicados;
- 1 formulario MEDIUM;
- `exact_class_agreement = 47,1%` (8/17);
- `detected_precision = 100%` (1/1);
- `concrete_recall = 14,3%` (1/7);
- 0 `false_concrete_promotions`;
- 0 `false_adverse_none`;
- 6 `missed_concrete`;
- 5 `false_unknown`.

El patrón residual es conservador, no peligroso: el producto evita afirmar una finalidad concreta sin sustento, pero todavía degrada demasiadas finalidades humanas concretas a `generic` o `unknown`. Dado el bajo acuerdo exacto y el patrón repetido de `missed_concrete`, la recomendación es un ajuste adicional antes de continuar con el siguiente control.

## Línea base

| Campo | Valor |
|---|---|
| Fecha | 2026-09-01 |
| Main SHA evaluado | `bcbf2c6272e260e14abac9ed27e3dfcfff45d021` |
| `framework_version` | `0.4` |
| `scoring_version` | `0.1` |
| `actions_version` | `2` |
| Evidence Contract interno | `v0.2` |
| Controles | 21 |
| Producción modificada durante QA2 | No |
| PRV-103 modificado durante QA2 | No |

## Independencia del holdout

No se reutilizó ninguna organización empleada en:

- W2.2b.2-QA;
- W2.2b.3-QA holdout #1;
- el regression/tuning set del PR #173.

La búsqueda se amplió por lotes únicamente para obtener el mínimo de formularios HIGH deduplicados. No se modificaron reglas, regex, keywords, precedencia ni confianza entre lotes.

## Ejecución

Se utilizó un workflow temporal de GitHub Actions con el pipeline real:

- `WebFetcher`;
- extracción productiva;
- `build_evidence`;
- `run_privacy_diagnostic`;
- `_personal_form`;
- `_form_purpose_signal`.

No se enviaron formularios, no se introdujeron datos personales, no se ejecutaron POST y no se autenticaron sesiones.

Runs:

| Lote | Run | Artifact | Artifact ID |
|---|---|---|---:|
| 1 | https://github.com/rodrigo-nodo/mininode/actions/runs/33570742759 | `privacy-prv103-qa2` | `9824843219` |
| 2 | https://github.com/rodrigo-nodo/mininode/actions/runs/33570912543 | `privacy-prv103-qa2-batch2` | `9824907405` |
| 3 | https://github.com/rodrigo-nodo/mininode/actions/runs/33571123478 | `privacy-prv103-qa2-batch3` | `9824979689` |
| 4 | https://github.com/rodrigo-nodo/mininode/actions/runs/33571299173 | `privacy-prv103-qa2-batch4` | `9825041764` |

Todos los artifacts fueron sanitizados y configurados con retención de siete días.

## Cobertura

| Métrica | Resultado |
|---|---:|
| Sitios intentados | 95 |
| Sitios con al menos una página analizada | 44 |
| Formularios personales raw | 25 |
| Formularios HIGH raw | 24 |
| Formularios MEDIUM raw | 1 |
| Formularios personales deduplicados | 18 |
| Formularios HIGH deduplicados | 17 |
| Formularios MEDIUM deduplicados | 1 |

La deduplicación colapsó únicamente componentes claramente repetidos con la misma evidencia estructurada dentro de la misma organización. Entre otros:

- Tenpo: dos observaciones idénticas con `submit_text = Enviar`;
- Qualtrics: tres observaciones idénticas con `submit_text = Submit`;
- Wrike: dos observaciones idénticas con `submit_text = Try Wrike for free`;
- UANDES: tres componentes repetidos entre contacto y política de privacidad.

Las dos variantes de Aircall se conservaron por separado porque la evidencia estructurada era diferente por idioma.

## Etiquetado manual

La adjudicación humana utilizó exclusivamente:

- `heading`;
- `legend`;
- `introductory_text`;
- `submit_text`.

No se utilizaron fields, URL de action, page title, nearby_text ni conocimiento externo de la organización para mejorar la clase manual.

## Matriz producto/manual - HIGH deduplicados

| Caso | Evidencia estructurada resumida | Producto | Manual | Acuerdo | Error |
|---|---|---|---|---|---|
| Q27 Qualtrics | Submit | generic | generic | Sí | - |
| Q45 Aircall EN | Talk to our Sales team / Steps 1/2 | unknown | generic | No | false_unknown |
| Q45 Aircall DE | Mit Sales sprechen / Schritt 1/2 | unknown | generic | No | false_unknown |
| Q65 UC Christus | Newsletter + recibir noticias/promociones + Enviar | concrete | concrete | Sí | - |
| Q01 Tenpo | Enviar | generic | generic | Sí | - |
| Q07 Calendly | Create a ticket via email + team will follow up via email + Submit | generic | concrete | No | missed_concrete |
| Q08 Basecamp | Subscribe | generic | generic | Sí | - |
| Q12 Grammarly | Submit | generic | generic | Sí | - |
| Q15 Smartsheet | Contact our team | unknown | generic | No | false_unknown |
| Q17 Wrike trial | Try Wrike for free | unknown | concrete | No | missed_concrete / false_unknown |
| Q17 Wrike contact | Get in touch | generic | generic | Sí | - |
| Q85 KNIME | Submit | generic | generic | Sí | - |
| Q91 Mundo contacto | sin heading/legend/intro/submit | unknown | unknown | Sí | - |
| Q91 Mundo galerías | Para ver las galerías completas... completa el siguiente formulario | unknown | concrete | No | missed_concrete / false_unknown |
| Q93 UANDES temas | Conoce más + selecciona temas que te interesaría recibir + Enviar | generic | concrete | No | missed_concrete |
| Q93 UANDES experiencia | Evalúa tu experiencia en nuestro sitio + Enviar | generic | concrete | No | missed_concrete |
| Q93 UANDES búsqueda | ¿Encontraste lo que estabas buscando? + Submit | generic | concrete | No | missed_concrete |

## Formulario MEDIUM

Se observó un formulario MEDIUM en Domo con `submit_text = Send message`.

El adapter mantuvo la protección aprobada:

- no produjo `detected`;
- no produjo `partial`;
- no produjo `not_detected`;
- quedó `unknown -> not_evaluable`.

No se observó influencia de MEDIUM sobre un agregado HIGH.

## Distribución de clases - HIGH deduplicados

### Producto

| Clase | Cantidad |
|---|---:|
| concrete | 1 |
| generic | 10 |
| none | 0 |
| unknown | 6 |

### Manual

| Clase | Cantidad |
|---|---:|
| concrete | 7 |
| generic | 9 |
| none | 0 |
| unknown | 1 |

## Métricas

| Métrica | Resultado |
|---|---:|
| `exact_class_agreement` | 8/17 = **47,1%** |
| `detected_precision` | 1/1 = **100%** |
| `concrete_recall` | 1/7 = **14,3%** |
| `none_precision` | N/A - 0 product_none |
| `unknown_rate` | 6/17 = **35,3%** |
| `false_concrete_promotions` | **0** |
| `false_generic_promotions` | **0** |
| `false_adverse_none` | **0** |
| `false_unknown` | **5** |
| `missed_concrete` | **6** |
| `medium_influenced_results` | **0** |
| `multi_form_consolidation_errors` | **0** |
| `critical_evidence_association_problems` | **0** |
| `manual_uncertain` | **0** |

## Qué mejoró respecto de QA1

La mejora más clara está exactamente donde apuntaba el PR #173.

| Métrica | QA1 v0.3 | QA2 v0.4 |
|---|---:|---:|
| Exact agreement | 38,9% | 47,1% |
| Detected precision | 100% | 100% |
| False concrete promotions | 0 | 0 |
| False adverse none | 8 | **0** |
| Missed concrete | 6 | 6 |

Esta comparación es solo direccional porque los holdouts son distintos.

El cambio `unrecognized semantic text -> unknown` funcionó: no apareció ningún `product_none` incorrecto y se eliminó el patrón de falsas conclusiones adversas observado en QA1.

## Problema residual

La limitación principal ya no es `none`.

La limitación pasa a ser la capacidad de distinguir una finalidad concreta de un contexto genérico o no comprendido.

Ejemplos del segundo holdout:

- `Create a ticket via email` junto con `our team will follow up via email` es una finalidad concreta, pero quedó `generic`;
- `Try Wrike for free` expresa una acción/resultado concreto, pero quedó `unknown`;
- `Para ver las galerías completas..., completa el siguiente formulario` explica un resultado concreto, pero quedó `unknown`;
- `Selecciona los temas que te interesaría recibir` expresa claramente qué recibirá la persona, pero quedó `generic`;
- `Evalúa tu experiencia en nuestro sitio` es una finalidad específica de feedback, pero quedó `generic`;
- `¿Encontraste lo que estabas buscando?` define una finalidad específica de feedback, pero quedó `generic`.

También aparecieron contextos genéricos no reconocidos, por ejemplo:

- `Talk to our Sales team`;
- `Contact our team`.

Estos quedan en `unknown`, lo que es conservador y preferible a un falso `concrete`, pero reduce el acuerdo de clase.

## Precisión vs recall

El diseño sigue cumpliendo el principio de seguridad:

**PRECISIÓN > RECALL**

La única promoción a `concrete` fue correcta y no apareció ninguna promoción falsa.

Sin embargo, `concrete_recall = 14,3%` muestra que la política actual es demasiado conservadora para que PRV-103 entregue contexto suficientemente útil. Seis de siete finalidades concretas adjudicadas no fueron reconocidas como tales.

La corrección debe continuar siendo acotada y determinista; este resultado no justifica introducir un clasificador amplio ni IA.

## Multi-form y asociación estructural

No se observaron errores mecánicos de consolidación multi-form.

Tampoco se observó evidencia estructurada asociada al formulario equivocado que provocara una clasificación incorrecta.

La discrepancia observada corresponde a la semántica de PRV-103 por formulario, no a W2.2b.2.

## Decisión

Los criterios de QA2 exigían:

- 0 false concrete;
- detected precision 100%;
- 0 false adverse none;
- ausencia de errores MEDIUM, multi-form y asociación crítica;
- y, para PASS, acuerdo exacto >= 90% sin patrón sistemático de error.

Las condiciones de seguridad se cumplen.

Sin embargo:

- acuerdo exacto = 47,1%;
- concrete recall = 14,3%;
- 6 missed concrete;
- 5 false unknown.

El error residual es repetido y justifica otro ajuste inmediato de la semántica antes de cerrar PRV-103.

**Clasificación final: NEEDS FIX.**

## No tuning

Durante QA2 no se modificaron:

- `_FORM_PURPOSE_*`;
- `_form_purpose_signal(...)`;
- `_form_purpose_evidence(...)`;
- `_without_form_purpose_noise(...)`;
- regex;
- listas generic/noise;
- precedencia;
- confianza;
- extractor;
- evaluator;
- catálogo;
- scoring;
- actions.

## Versionado

Sin cambios:

- `framework_version = 0.4`;
- `scoring_version = 0.1`;
- `actions_version = 2`;
- Evidence Contract = `v0.2`;
- controles = 21.

## Recomendación

Mergear este PR como evidencia formal de QA2 con resultado **NEEDS FIX**.

El siguiente paso debe ser un PR separado y pequeño de calibración semántica de PRV-103, enfocado exclusivamente en las seis omisiones concretas y los contextos genéricos observados, sin reglas específicas por sitio.

Después de ese ajuste, ejecutar un tercer holdout nuevo antes de cerrar definitivamente PRV-103.

No avanzar todavía al siguiente control de formularios.
