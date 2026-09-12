# PRV-103 framework 0.9 — evidencia de pre-freeze

## Estado

**Control histórico: PASS. Precheck público: PENDIENTE. Pool no congelado.**

La lista completa recuperada del Artifact B congelado de Issue #223 contiene 100 hostnames. La primera comparación confirmó 30 cruces en el pool propuesto del PR #226; una comparación posterior contra el artifact completo detectó otros cuatro reemplazos indirectos. Los 34 cruces fueron retirados antes del freeze. El pool corregido permanece en `pre-freeze` porque este runner no dispone de salida HTTPS pública.

## Producto mantenido

| Campo | Valor |
|---|---|
| SHA productivo | `6fbe6f94887114f4a5459af861f1fcaa0c4b7bd7` |
| `framework_version` | `0.9` |
| `scoring_version` | `0.1` |
| PRV-103 | determinístico; no ejecutado |
| LLM/shadow | desactivado |

No se modificaron el producto, sus reglas, el extractor, el scoring ni las versiones.

## Cruces confirmados con Issue #223 y reemplazos

Los hostnames se compararon en minúsculas y sin esquema, `www.`, ruta ni barra final. Cada reemplazo conserva razonablemente la categoría funcional del dominio retirado. La selección no utilizó formularios, predicciones ni resultados esperados.

| dominio contaminado | origen | acción | reemplazo | equivalencia funcional |
|---|---|---|---|---|
| `bill.com` | Issue #223 | `replace` | `paystack.com` | pagos y cuentas por pagar |
| `breezy.hr` | Issue #223 | `replace` | `jobvite.com` | reclutamiento |
| `bugsnag.com` | Issue #223 | `replace` | `honeybadger.io` | monitoreo de errores |
| `crisp.chat` | Issue #223 | `replace` | `livechat.com` | soporte y chat |
| `dixa.com` | Issue #223 | `replace` | `deskpro.com` | soporte al cliente |
| `factorialhr.com` | Issue #223 | `replace` | `namely.com` | gestión de RR.HH. |
| `getresponse.com` | Issue #223 | `replace` | `campaigner.com` | email marketing |
| `gladly.com` | Issue #223 | `replace` | `richpanel.com` | atención al cliente |
| `hibob.com` | Issue #223 | `replace` | `sesamehr.com` | gestión de RR.HH. |
| `justworks.com` | Issue #223 | `replace` | `patriotsoftware.com` | nómina y RR.HH. |
| `klarna.com` | Issue #223 | `replace` | `affirm.com` | pagos y financiación |
| `kustomer.com` | Issue #223 | `replace` | `reamaze.com` | atención al cliente |
| `logrocket.com` | Issue #223 | `replace` | `openreplay.com` | observabilidad frontend |
| `mollie.com` | Issue #223 | `replace` | `payplug.com` | procesamiento de pagos |
| `nordpass.com` | Issue #223 | `replace` | `roboform.com` | gestión de contraseñas |
| `paycor.com` | Issue #223 | `replace` | `isolvedhcm.com` | nómina y RR.HH. |
| `payoneer.com` | Issue #223 | `replace` | `worldremit.com` | pagos internacionales |
| `plausible.io` | Issue #223 | `replace` | `fathomanalytics.com` | analítica web |
| `raygun.com` | Issue #223 | `replace` | `appsignal.com` | monitoreo de aplicaciones |
| `recruitee.com` | Issue #223 | `replace` | `manatal.com` | reclutamiento |
| `rollbar.com` | Issue #223 | `replace` | `airbrake.io` | monitoreo de errores |
| `sophos.com` | Issue #223 | `replace` | `eset.com` | ciberseguridad |
| `spendesk.com` | Issue #223 | `replace` | `pleo.io` | gestión de gastos |
| `tawk.to` | Issue #223 | `replace` | `chatwoot.com` | soporte y chat |
| `teamwork.com` | Issue #223 | `replace` | `freedcamp.com` | gestión de proyectos |
| `todoist.com` | Issue #223 | `replace` | `ticktick.com` | gestión de tareas |
| `travis-ci.com` | Issue #223 | `replace` | `buildkite.com` | integración continua |
| `workable.com` | Issue #223 | `replace` | `jazzhr.com` | reclutamiento |
| `wufoo.com` | Issue #223 | `replace` | `formester.com` | formularios online |
| `zenefits.com` | Issue #223 | `replace` | `paycom.com` | nómina y RR.HH. |

Resultado de la primera corrección: **30/30 cruces de Issue #223 eliminados**.

### Cuatro cruces adicionales contra el Artifact B completo

| dominio histórico | origen | acción | reemplazo final | equivalencia funcional |
|---|---|---|---|---|
| `affirm.com` | Issue #223 | `replace` | `sezzle.com` | pagos y financiación |
| `buildkite.com` | Issue #223 | `replace` | `woodpecker-ci.org` | integración continua |
| `freedcamp.com` | Issue #223 | `replace` | `awork.com` | gestión de proyectos |
| `livechat.com` | Issue #223 | `replace` | `delightchat.io` | soporte y chat |

Resultado de la corrección final: **4/4 cruces adicionales eliminados**.

## Control contra el histórico restante

Los cuatro reemplazos finales se contrastaron primero contra los 100 hostnames de Issue #223, el propio pool y los blobs alcanzables del SHA base. Después, el pool completo corregido se volvió a comparar contra los blobs alcanzables del SHA base para QA1-QA8, scripts, workflows, fixtures, documentación y calibraciones/investigaciones PRV-103 con sitios reales. Las sustituciones acumuladas quedaron cubiertas por la comparación final.

| Control | Resultado |
|---|---|
| Lista de exclusión de Issue #223 | 100 hostnames únicos |
| Comparación final contra Issue #223 | 0/100 solapamientos después de eliminar 34 cruces acumulados |
| Histórico local QA1-QA8 y calibraciones PRV-103 | 0 solapamientos adicionales |
| Hostnames vacíos o duplicados tras normalización | 0 |
| Total del pool corregido | 100 |

No aparecieron cruces adicionales contra QA1-QA8 o las calibraciones/investigaciones locales. Los únicos cruces nuevos fueron los cuatro identificados al completar la lista de exclusión de Issue #223.

## Pool final propuesto (orden pre-freeze)

Este es el orden exacto preservado también en `prv103-holdout-0.9-candidates.txt`:

| # | hostname |
|---:|---|
| 1 | `reamaze.com` |
| 2 | `richpanel.com` |
| 3 | `deskpro.com` |
| 4 | `podium.com` |
| 5 | `qualaroo.com` |
| 6 | `nicereply.com` |
| 7 | `sesamehr.com` |
| 8 | `namely.com` |
| 9 | `payfit.com` |
| 10 | `oysterhr.com` |
| 11 | `workday.com` |
| 12 | `smartrecruiters.com` |
| 13 | `manatal.com` |
| 14 | `jobvite.com` |
| 15 | `talentlms.com` |
| 16 | `trello.com` |
| 17 | `awork.com` |
| 18 | `whimsical.com` |
| 19 | `framery.com` |
| 20 | `airbrake.io` |
| 21 | `honeybadger.io` |
| 22 | `openreplay.com` |
| 23 | `woodpecker-ci.org` |
| 24 | `pingidentity.com` |
| 25 | `onelogin.com` |
| 26 | `roboform.com` |
| 27 | `paloaltonetworks.com` |
| 28 | `braintreepayments.com` |
| 29 | `payplug.com` |
| 30 | `sezzle.com` |
| 31 | `worldremit.com` |
| 32 | `n26.com` |
| 33 | `pleo.io` |
| 34 | `paystack.com` |
| 35 | `truelayer.com` |
| 36 | `campaigner.com` |
| 37 | `aweber.com` |
| 38 | `formester.com` |
| 39 | `forms.app` |
| 40 | `matomo.org` |
| 41 | `fathomanalytics.com` |
| 42 | `snowplow.io` |
| 43 | `pinecone.io` |
| 44 | `buffer.com` |
| 45 | `kayako.com` |
| 46 | `liveagent.com` |
| 47 | `delightchat.io` |
| 48 | `chatwoot.com` |
| 49 | `missiveapp.com` |
| 50 | `hiverhq.com` |
| 51 | `salesflare.com` |
| 52 | `paycom.com` |
| 53 | `patriotsoftware.com` |
| 54 | `trinet.com` |
| 55 | `isolvedhcm.com` |
| 56 | `paylocity.com` |
| 57 | `ukg.com` |
| 58 | `ceipal.com` |
| 59 | `meistertask.com` |
| 60 | `niftypm.com` |
| 61 | `proofhub.com` |
| 62 | `flowlu.com` |
| 63 | `ticktick.com` |
| 64 | `sunsama.com` |
| 65 | `akiflow.com` |
| 66 | `xmind.app` |
| 67 | `creately.com` |
| 68 | `appsignal.com` |
| 69 | `sematext.com` |
| 70 | `lumigo.io` |
| 71 | `groundcover.com` |
| 72 | `chronosphere.io` |
| 73 | `coralogix.com` |
| 74 | `mezmo.com` |
| 75 | `opslevel.com` |
| 76 | `strongdm.com` |
| 77 | `goteleport.com` |
| 78 | `tailscale.com` |
| 79 | `arcticwolf.com` |
| 80 | `eset.com` |
| 81 | `payu.com` |
| 82 | `groovehq.com` |
| 83 | `helpshift.com` |
| 84 | `uservoice.com` |
| 85 | `canny.io` |
| 86 | `delighted.com` |
| 87 | `lattice.com` |
| 88 | `cultureamp.com` |
| 89 | `jazzhr.com` |
| 90 | `jira.com` |
| 91 | `height.app` |
| 92 | `craft.do` |
| 93 | `notion.so` |
| 94 | `betterstack.com` |
| 95 | `convertkit.com` |
| 96 | `mparticle.com` |
| 97 | `census.com` |
| 98 | `dbt.com` |
| 99 | `cal.com` |
| 100 | `acuityscheduling.com` |

## Precheck público

- Estado: **PENDIENTE de verificación pública externa**; no se declara PASS.
- Ya se comprobó que el proxy de este entorno devuelve `CONNECT tunnel failed, response 403` para conexiones HTTPS públicas. Ese bloqueo es una limitación del runner y no se interpreta como caída de ningún sitio.
- No se repitieron 100 solicitudes que no aportarían evidencia nueva.
- Ningún candidato fue alterado por el error del proxy.

El pool queda listo para que un runner externo ejecute una única pasada del precheck público pasivo. Solo después de comprobar accesibilidad y correspondencia organizacional de los 100 dominios podrá declararse congelado.

## Declaración de no ejecución

No se inspeccionaron `heading`, `legend`, `introductory_text` ni `submit_text`; no se enviaron formularios ni POST; no se inició sesión ni se crearon cuentas. No se ejecutaron PRV-103, el clasificador ni el QA, y no se generaron Artifact A, Gold, Artifact B nuevo ni predicciones.
