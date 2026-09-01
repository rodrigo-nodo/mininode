# W2.2b.3-QA - calibración real de PRV-103

## Resultado

**CALIBRATION BLOCKED**

No fue posible ejecutar la calibración real. El entorno local resolvió DNS, pero
rechazó todas las conexiones salientes del `WebFetcher` con
`ConnectError: network_unreachable`. El entorno tampoco dispone de autenticación
GitHub (`gh auth status` informa que no existe una sesión), por lo que no fue
posible publicar ni ejecutar el workflow temporal alternativo.

No se usaron fixtures, mocks ni resultados inventados. En consecuencia, esta
ejecución no permite clasificar PRV-103 como PASS, PASS WITH OBSERVATIONS o NEEDS
FIX.

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
| Producción modificada | No |
| PRV-103 modificado | No |

## Metodología intentada

Se preparó fuera del repositorio un runner efímero que invocaba
`diagnose_privacy_url(...)` sin mocks. El runner conservaba en memoria el Evidence
Contract final y proyectaba exclusivamente URL sin query string, hostname, índice,
confianza personal, evidencia estructurada, clase interna y campos minimizados. No
introducía datos, enviaba formularios, ejecutaba POST, autenticaba ni probaba
endpoints.

Los doce intentos fallaron durante el fetch inicial. Al no existir autenticación
GitHub, no se creó el workflow alternativo: hacerlo sin poder publicarlo o ejecutarlo
no habría producido evidencia real y habría dejado un cambio temporal innecesario.

## Holdout principal intentado

Todos los sitios eran nuevos respecto de W2.2b.2-QA.

| Sitio | Idioma | Sector | Resultado |
|---|---|---|---|
| `bsale.cl` | Español | SaaS/e-commerce, Chile | `network_unreachable` |
| `cleveritgroup.com` | Español | Tecnología, Chile | `network_unreachable` |
| `uc.cl` | Español | Educación, Chile | `network_unreachable` |
| `clinicaalemana.cl` | Español | Salud, Chile | `network_unreachable` |
| `achs.cl` | Español | Salud, Chile | `network_unreachable` |
| `laborum.cl` | Español | Servicios, Chile | `network_unreachable` |
| `shopify.com` | Inglés | E-commerce/SaaS | `network_unreachable` |
| `hubspot.com` | Inglés | SaaS/tecnología | `network_unreachable` |
| `salesforce.com` | Inglés | SaaS/tecnología | `network_unreachable` |
| `wordpress.com` | Inglés | Tecnología | `network_unreachable` |
| `squarespace.com` | Inglés | SaaS/tecnología | `network_unreachable` |
| `zendesk.com` | Inglés | Soporte/SaaS | `network_unreachable` |

Sitios diagnosticados: **0 de 12**. No se forzó ninguno ni se relajaron las
protecciones del inspector.

## Formularios y matriz manual/producto

No hubo páginas recuperadas ni formularios observables. Por tanto, no existe una
matriz manual/producto válida. Una tabla con clases o acuerdos en estas condiciones
sería evidencia inventada.

| Case | Site | Lang | Form | Personal conf | Heading | Legend | Intro | Submit | Product purpose | PRV-103 | Manual purpose | Agreement | Error type |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — | — | — | — | — | — | — | `calibration_blocked` |

## Métricas

Las métricas quedan **no calculables**, no en cero: no existe denominador real.

| Métrica | Resultado |
|---|---|
| Formularios HIGH revisados | No calculable |
| Formularios MEDIUM revisados | No calculable |
| Producto `concrete` | No calculable |
| Producto `generic` | No calculable |
| Producto `none` | No calculable |
| Producto `unknown` | No calculable |
| `exact_class_agreement` | No calculable |
| `detected_precision` | No calculable |
| `false_concrete_promotions` | No calculable |
| `false_generic_promotions` | No calculable |
| `missed_concrete` | No calculable |
| `medium_influenced_results` | No calculable |
| `multi_form_consolidation_errors` | No calculable |
| `manual_uncertain` | No calculable |

## Errores

El único error adjudicable es operacional: conectividad saliente no disponible y
ausencia de credenciales para la alternativa GitHub Actions. No se observó evidencia
suficiente para adjudicar errores A-I de PRV-103.

## Análisis MEDIUM

Bloqueado: no se recuperaron formularios MEDIUM. No se puede afirmar que hayan
influido o no en resultados agregados reales.

## Consolidación multi-form

Bloqueada: no se recuperaron páginas con múltiples formularios. No se evaluó la
precedencia agregada en evidencia real.

## Regression reference - non-holdout

No ejecutada. Se priorizó el holdout principal y, una vez confirmada la limitación
global de red, ejecutar referencias habría fallado por la misma causa. No se mezcló
ninguna referencia anterior con el holdout.

## Limpieza y no tuning

No se creó ningún workflow ni runner dentro del repositorio. El runner local
efímero quedó fuera del árbol Git y no forma parte del cambio. No se modificaron
extractor, adapter, evaluator, WebFetcher, catálogos, versiones, API, frontend ni
base de datos; tampoco se ajustaron regex, palabras clave, precedencia o confianza.

## Conclusión

**CALIBRATION BLOCKED** por `network_unreachable` en los doce sitios y falta de
autenticación GitHub para ejecutar el fallback. Esta ejecución no responde si la
clasificación automática coincide con una revisión humana independiente.

## Recomendación

Repetir W2.2b.3-QA sin cambiar reglas en un runner con conectividad pública y acceso
al repositorio. Usar este mismo holdout o reemplazos no observados por quienes
diseñaron PRV-103, generar la matriz sanitizada y aplicar los umbrales de decisión
solo después de revisar aproximadamente 15-25 formularios reales. No comenzar otro
control ni realizar tuning antes de completar esa calibración.
