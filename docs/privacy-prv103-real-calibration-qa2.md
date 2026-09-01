# W2.2b.3-QA2 - segundo holdout real de PRV-103

## Resultado

**NEEDS FIX (QA no ejecutable; sin conclusión sobre PRV-103).**

No fue posible completar el segundo holdout en este entorno. El pipeline productivo
se ejecutó localmente contra 15 organizaciones nuevas, pero las 15 solicitudes HOME
terminaron antes de analizar una página (`http_error`, sin estado HTTP). El entorno no
permite conexiones directas a las IP públicas validadas y fijadas por `WebFetcher`.
Tampoco había credenciales ni remote GitHub disponibles para publicar y ejecutar el
workflow temporal previsto como alternativa.

Por tanto, este documento **no responde** si v0.4 redujo los falsos `none` sin
introducir falsos `concrete`. No se adjudicaron formularios, no se calcularon métricas
semánticas con denominadores vacíos y no se reutilizó el holdout de QA1. La etiqueta
`NEEDS FIX` describe exclusivamente que la QA requerida no satisface su muestra
mínima; no constituye evidencia de un defecto nuevo de PRV-103.

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
| Producción modificada durante QA | No |
| PRV-103 modificado durante QA | No |

## Metodología y límites de ejecución

Se preparó un runner local temporal basado en `WebFetcher`, `build_evidence`,
`run_privacy_diagnostic`, `_personal_form` y `_form_purpose_signal`, sin mocks, sin
interacción con formularios y con salida sanitizada. Se intentó primero el transporte
productivo fijado a IP. Como comprobación de la limitación ambiental se intentó luego
un cliente HTTP inyectado orientado al proxy del entorno; el proxy rechazó las
conexiones con `403` antes de llegar a los sitios. Esa comprobación no produjo
evidencia y no se consideró una ejecución productiva ni entró en métricas.

No se enviaron formularios, introdujeron datos, ejecutaron `POST`, autenticaron
sesiones, aceptaron términos, cambiaron preferencias ni eludieron protecciones. No se
guardaron HTML, cookies, headers, tokens, query strings, credenciales o request bodies.

No se creó un workflow porque este checkout carecía de remote y de autenticación de
GitHub (`gh auth status` informó que no había sesión), por lo que no existía una vía
real para publicarlo o ejecutarlo. El runner local se eliminó y no forma parte del PR.

## Exclusiones e independencia

Se excluyeron todas las organizaciones enumeradas en la Issue, incluidos los ocho
sitios de W2.2b.2-QA y los sitios del holdout #1. No se ejecutó ningún sitio antiguo
antes ni después de estos intentos. Los 15 candidatos son organizaciones distintas y
no son subdominios de organizaciones excluidas.

## Sitios intentados

| Caso | Organización | Sector | Idioma | URL sanitizada | Páginas analizadas | Resultado de fetch |
|---|---|---|---|---|---:|---|
| Q01 | Tenpo | Fintech | es | `https://www.tenpo.cl/` | 0 | `http_error` |
| Q02 | Clínica Indisa | Salud | es | `https://www.clinicaindisa.cl/` | 0 | `http_error` |
| Q03 | Duoc UC | Educación | es | `https://www.duoc.cl/` | 0 | `http_error` |
| Q04 | Tiendanube | SaaS/e-commerce | es | `https://www.tiendanube.com/` | 0 | `http_error` |
| Q05 | Entel | Servicios | es | `https://www.entel.cl/` | 0 | `http_error` |
| Q06 | Universidad del Desarrollo | Educación | es | `https://www.udd.cl/` | 0 | `http_error` |
| Q07 | Typeform | SaaS | en | `https://www.typeform.com/` | 0 | `http_error` |
| Q08 | Miro | SaaS | en | `https://miro.com/` | 0 | `http_error` |
| Q09 | Calendly | SaaS | en | `https://calendly.com/` | 0 | `http_error` |
| Q10 | Basecamp | SaaS | en | `https://basecamp.com/` | 0 | `http_error` |
| Q11 | Patagonia | E-commerce | en | `https://www.patagonia.com/` | 0 | `http_error` |
| Q12 | Mayo Clinic | Salud | en | `https://www.mayoclinic.org/` | 0 | `http_error` |
| Q13 | Stanford University | Educación | en | `https://www.stanford.edu/` | 0 | `http_error` |
| Q14 | Grammarly | SaaS | en | `https://www.grammarly.com/` | 0 | `http_error` |
| Q15 | Blue Bottle Coffee | Microempresa/e-commerce | en | `https://www.bluebottlecoffee.com/` | 0 | `http_error` |

La selección incluye seis sitios en español, cuatro organizaciones chilenas, nueve
sitios en inglés y variedad de fintech, salud, educación, servicios, SaaS y
e-commerce. La disponibilidad e inspeccionabilidad no pudo confirmarse porque ningún
HOME atravesó la frontera de red del entorno.

## Formularios y deduplicación

| Métrica de cobertura | Resultado |
|---|---:|
| Sitios intentados | 15 |
| Sitios con páginas analizadas | 0 |
| `raw_personal_forms` | 0 |
| `deduplicated_personal_forms` | 0 |
| HIGH | 0 |
| MEDIUM | 0 |

No hubo formularios observables que registrar o deduplicar. En particular, el cero
no significa ausencia de formularios en los sitios: significa ausencia de páginas
recuperadas.

## Matriz producto/manual

No se construye una matriz producto/manual vacía. Las clases de producto y manuales
son `N/A`, no cero observado, porque no hubo formularios adjudicables.

## Métricas

| Métrica | Resultado |
|---|---:|
| Producto `concrete` / `generic` / `none` / `unknown` | N/A |
| Manual `concrete` / `generic` / `none` / `unknown` | N/A |
| `exact_class_agreement` | N/A (0 adjudicables) |
| `detected_precision` | N/A (0 `product_concrete`) |
| `concrete_recall` | N/A (0 `manual_concrete`) |
| `none_precision` | N/A (0 `product_none`) |
| `unknown_rate` | N/A (0 adjudicables) |
| `false_concrete_promotions` | N/A |
| `false_generic_promotions` | N/A |
| `false_adverse_none` | N/A |
| `false_unknown` | N/A |
| `missed_concrete` | N/A |
| `medium_influenced_results` | N/A |
| `multi_form_consolidation_errors` | N/A |
| `evidence_association_problems` | N/A |
| `manual_uncertain` | N/A |

Asignar `0` a errores o `100%` a precisiones con esta ejecución sería una conclusión
engañosa. Ningún valor semántico entra en una decisión sobre v0.4.

## Errores, MEDIUM, multi-form y asociación estructural

El único patrón observado fue el bloqueo ambiental previo a extracción: 15 de 15
HOME con `http_error`. No es un error de clasificación PRV-103.

- **MEDIUM:** sin formularios observados; influencia no evaluable.
- **Multi-form:** sin sitios con formularios analizados; consolidación no evaluable.
- **Asociación estructural:** sin evidencia extraída; asociación no evaluable.
- **Etiquetado manual:** no se etiquetó ningún caso y no se utilizó información
  externa para inferir una etiqueta.

## Comparación direccional QA1/QA2

| Métrica | QA1 v0.3 | QA2 v0.4 |
|---|---:|---:|
| Exact agreement | 38,9% | N/A |
| Detected precision | 100% | N/A |
| False concrete promotions | 0 | N/A |
| Missed concrete | 6 | N/A |
| False adverse none | 8 | N/A |

Los holdouts son distintos y, aun si QA2 hubiera finalizado, esta tabla sería solo una
señal direccional, no un experimento A/B. En esta ejecución no admite comparación.

## Conclusión

No hay base para afirmar una mejora, regresión, precisión o recall de PRV-103 v0.4.
No se cumplen el mínimo de 15 HIGH ni las condiciones necesarias para `PASS` o `PASS
WITH OBSERVATIONS`. La clasificación operativa de esta entrega es **NEEDS FIX** porque
la validación está incompleta, no porque se haya detectado una regla defectuosa.

## No tuning y versionado

No se modificaron reglas, regex, conjuntos, ruido, precedencia, confianza, extractor,
modelos, adapter, evaluator, catálogo, scoring ni acciones. Se mantienen:

- `framework_version = 0.4`;
- `scoring_version = 0.1`;
- `actions_version = 2`;
- Evidence Contract = `v0.2`;
- controles = 21.

## Recomendación

No usar este documento para cerrar la calibración ni comenzar el siguiente control.
Repetir W2.2b.3-QA2 en un checkout con capacidad de ejecutar el workflow temporal de
GitHub Actions, manteniendo todas las exclusiones y reemplazando este registro por un
holdout con al menos 15 formularios HIGH deduplicados. Congelar etiquetas, métricas y
decisión antes de cualquier referencia a casos antiguos y eliminar luego el workflow.
