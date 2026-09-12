# PRV-103 framework 0.9 — evidencia de pre-freeze

## Estado

**Precheck: FAIL (limitación de entorno). Pool no congelado.**

El producto objetivo sí quedó verificado en el SHA exigido, pero este entorno no pudo establecer ninguna conexión HTTPS pública: el proxy devolvió `CONNECT tunnel failed, response 403` para los 100 GET. Por tanto, no sería válido afirmar frescura, accesibilidad ni correspondencia organizacional, y el freeze se detuvo antes de ejecutar QA. Los 100 hostnames de `prv103-holdout-0.9-candidates.txt` son **propuestos, no congelados**, para repetir el precheck en un runner con acceso público.

## Producto verificado

| Campo | Valor |
|---|---|
| SHA de `main` requerido y verificado antes de crear la rama | `6fbe6f94887114f4a5459af861f1fcaa0c4b7bd7` |
| `framework_version` | `0.9` |
| `scoring_version` | `0.1` |
| PRV-103 | determinístico |
| LLM/shadow | desactivado (`false`, sample rate `0`) |
| Momento del intento (UTC) | `2026-09-12T18:06:05Z` |

## Control de independencia

Se normalizaron hostnames a minúsculas, sin `www.`, esquema, puerto, ruta ni punto final. La búsqueda cubrió todos los blobs alcanzables del historial Git local para scripts, workflows, fixtures y documentación de QA/calibración PRV-103, además de calibraciones previas relacionadas. El acceso al repositorio/PRs remotos y a Issue #223 también quedó bloqueado por el proxy; por ello la independencia remota no puede declararse completa hasta repetir ese control con acceso a GitHub.

| dominio candidato | histórico | origen histórico | acción |
|---|---|---|---|
| `zendesk.com` | sí | QA6, QA8, QA1/calibración | `replace` |
| `intercom.com` | sí | QA6, QA8, QA1/calibración | `replace` |
| `front.com` | sí | QA8, QA2 | `replace` |
| `freshworks.com` | sí | QA4, QA1/calibración | `replace` |
| `groovehq.com` | no | — | `keep` |
| `helpshift.com` | no | — | `keep` |
| `uservoice.com` | no | — | `keep` |
| `productboard.com` | sí | QA2 | `replace` |
| `canny.io` | no | — | `keep` |
| `delighted.com` | no | — | `keep` |
| `bamboohr.com` | sí | QA6 | `replace` |
| `rippling.com` | sí | QA6 | `replace` |
| `gusto.com` | sí | QA6 | `replace` |
| `deel.com` | sí | QA6 | `replace` |
| `remote.com` | sí | QA6 | `replace` |
| `lattice.com` | no | — | `keep` |
| `cultureamp.com` | no | — | `keep` |
| `greenhouse.com` | sí | QA6 | `replace` |
| `lever.co` | sí | QA6 | `replace` |
| `workable.com` | no | — | `keep` |
| `asana.com` | sí | QA4, QA1/calibración | `replace` |
| `monday.com` | sí | QA6, QA8, QA1/calibración | `replace` |
| `clickup.com` | sí | QA6, QA8, QA2 | `replace` |
| `linear.app` | sí | QA8, QA3 | `replace` |
| `jira.com` | no | — | `keep` |
| `height.app` | no | — | `keep` |
| `craft.do` | no | — | `keep` |
| `notion.so` | no | — | `keep` |
| `miro.com` | sí | QA4, QA2 | `replace` |
| `mural.co` | sí | QA2 | `replace` |
| `sentry.io` | sí | QA4, QA8, QA1/calibración | `replace` |
| `datadoghq.com` | sí | QA4, QA1/calibración | `replace` |
| `newrelic.com` | sí | QA6, QA8, QA3 | `replace` |
| `honeycomb.io` | sí | QA8 | `replace` |
| `betterstack.com` | no | — | `keep` |
| `launchdarkly.com` | sí | QA8, QA3 | `replace` |
| `circleci.com` | sí | QA6, QA3 | `replace` |
| `gitlab.com` | sí | QA6 | `replace` |
| `vercel.com` | sí | QA8, QA3 | `replace` |
| `netlify.com` | sí | QA8, QA3 | `replace` |
| `auth0.com` | sí | QA8 | `replace` |
| `workos.com` | sí | QA3 | `replace` |
| `clerk.com` | sí | QA3 | `replace` |
| `okta.com` | sí | QA6, QA8, QA1/calibración | `replace` |
| `1password.com` | sí | QA6, QA7 | `replace` |
| `bitwarden.com` | sí | QA8 | `replace` |
| `dashlane.com` | sí | QA6 | `replace` |
| `crowdstrike.com` | sí | QA8, QA3 | `replace` |
| `wiz.io` | sí | QA8, QA3 | `replace` |
| `snyk.io` | sí | QA6, QA3 | `replace` |
| `stripe.com` | sí | QA6, QA8, QA1/calibración, fixture/código histórico | `replace` |
| `adyen.com` | sí | QA6, QA1/calibración | `replace` |
| `checkout.com` | sí | QA6, QA7 | `replace` |
| `airwallex.com` | sí | QA8 | `replace` |
| `wise.com` | sí | QA6, QA2 | `replace` |
| `revolut.com` | sí | QA6, QA2 | `replace` |
| `brex.com` | sí | QA6, QA7 | `replace` |
| `ramp.com` | sí | QA6 | `replace` |
| `mercury.com` | sí | QA6, QA7 | `replace` |
| `plaid.com` | sí | QA6, QA7 | `replace` |
| `hubspot.com` | sí | QA4, QA1/calibración | `replace` |
| `mailchimp.com` | sí | QA4, QA1/calibración | `replace` |
| `klaviyo.com` | sí | QA6, QA8, QA1/calibración | `replace` |
| `customer.io` | sí | QA6, QA3 | `replace` |
| `activecampaign.com` | sí | QA8, QA3 | `replace` |
| `convertkit.com` | no | — | `keep` |
| `typeform.com` | sí | QA4, QA2 | `replace` |
| `jotform.com` | sí | QA6, QA7 | `replace` |
| `tally.so` | sí | QA8 | `replace` |
| `paperform.co` | sí | QA6 | `replace` |
| `amplitude.com` | sí | QA6, QA8, QA2 | `replace` |
| `mixpanel.com` | sí | QA6, QA8, QA2 | `replace` |
| `heap.io` | sí | QA6, QA8, QA2 | `replace` |
| `fullstory.com` | sí | QA8, QA2 | `replace` |
| `posthog.com` | sí | QA8 | `replace` |
| `segment.com` | sí | QA8 | `replace` |
| `rudderstack.com` | sí | QA8, QA3 | `replace` |
| `mparticle.com` | no | — | `keep` |
| `census.com` | no | — | `keep` |
| `hightouch.com` | sí | QA8, QA3 | `replace` |
| `snowflake.com` | sí | QA4, QA2 | `replace` |
| `fivetran.com` | sí | QA8, QA3 | `replace` |
| `dbt.com` | no | — | `keep` |
| `confluent.io` | sí | QA4, QA8, QA2 | `replace` |
| `elastic.co` | sí | QA4, QA8, QA2 | `replace` |
| `algolia.com` | sí | QA4, QA8 | `replace` |
| `contentful.com` | sí | QA4, QA8 | `replace` |
| `sanity.io` | sí | QA6 | `replace` |
| `webflow.com` | sí | QA4, QA8, QA2 | `replace` |
| `squarespace.com` | sí | QA4, QA1/calibración | `replace` |
| `calendly.com` | sí | QA6, QA8, QA2 | `replace` |
| `cal.com` | no | — | `keep` |
| `acuityscheduling.com` | no | — | `keep` |
| `docusign.com` | sí | QA4, QA1/calibración | `replace` |
| `pandadoc.com` | sí | QA6 | `replace` |
| `dropbox.com` | sí | QA4, QA1/calibración | `replace` |
| `box.com` | sí | QA4, QA2 | `replace` |
| `loom.com` | sí | QA6, QA8, QA2 | `replace` |
| `zapier.com` | sí | QA4, QA1/calibración | `replace` |
| `make.com` | sí | QA8 | `replace` |

## Sustituciones propuestas antes del precheck

Estas sustituciones mantienen de forma agregada las categorías funcionales del pool (soporte/CX, RR.HH., colaboración, observabilidad, seguridad, pagos, marketing/formularios, datos y productividad). No se inspeccionaron formularios ni se eligieron sitios por resultados o clases esperadas. Al fallar el acceso público, ninguna sustitución se considera congelada.

| original | motivo | reemplazo propuesto |
|---|---|---|
| `zendesk.com` | hostname consumido en QA6, QA8, QA1/calibración | `kustomer.com` |
| `intercom.com` | hostname consumido en QA6, QA8, QA1/calibración | `gladly.com` |
| `front.com` | hostname consumido en QA8, QA2 | `dixa.com` |
| `freshworks.com` | hostname consumido en QA4, QA1/calibración | `podium.com` |
| `productboard.com` | hostname consumido en QA2 | `qualaroo.com` |
| `bamboohr.com` | hostname consumido en QA6 | `nicereply.com` |
| `rippling.com` | hostname consumido en QA6 | `hibob.com` |
| `gusto.com` | hostname consumido en QA6 | `factorialhr.com` |
| `deel.com` | hostname consumido en QA6 | `payfit.com` |
| `remote.com` | hostname consumido en QA6 | `oysterhr.com` |
| `greenhouse.com` | hostname consumido en QA6 | `workday.com` |
| `lever.co` | hostname consumido en QA6 | `smartrecruiters.com` |
| `asana.com` | hostname consumido en QA4, QA1/calibración | `recruitee.com` |
| `monday.com` | hostname consumido en QA6, QA8, QA1/calibración | `breezy.hr` |
| `clickup.com` | hostname consumido en QA6, QA8, QA2 | `talentlms.com` |
| `linear.app` | hostname consumido en QA8, QA3 | `trello.com` |
| `miro.com` | hostname consumido en QA4, QA2 | `teamwork.com` |
| `mural.co` | hostname consumido en QA2 | `whimsical.com` |
| `sentry.io` | hostname consumido en QA4, QA8, QA1/calibración | `framery.com` |
| `datadoghq.com` | hostname consumido en QA4, QA1/calibración | `rollbar.com` |
| `newrelic.com` | hostname consumido en QA6, QA8, QA3 | `bugsnag.com` |
| `honeycomb.io` | hostname consumido en QA8 | `logrocket.com` |
| `launchdarkly.com` | hostname consumido en QA8, QA3 | `travis-ci.com` |
| `circleci.com` | hostname consumido en QA6, QA3 | `pingidentity.com` |
| `gitlab.com` | hostname consumido en QA6 | `onelogin.com` |
| `vercel.com` | hostname consumido en QA8, QA3 | `nordpass.com` |
| `netlify.com` | hostname consumido en QA8, QA3 | `paloaltonetworks.com` |
| `auth0.com` | hostname consumido en QA8 | `braintreepayments.com` |
| `workos.com` | hostname consumido en QA3 | `mollie.com` |
| `clerk.com` | hostname consumido en QA3 | `klarna.com` |
| `okta.com` | hostname consumido en QA6, QA8, QA1/calibración | `payoneer.com` |
| `1password.com` | hostname consumido en QA6, QA7 | `n26.com` |
| `bitwarden.com` | hostname consumido en QA8 | `spendesk.com` |
| `dashlane.com` | hostname consumido en QA6 | `bill.com` |
| `crowdstrike.com` | hostname consumido en QA8, QA3 | `truelayer.com` |
| `wiz.io` | hostname consumido en QA8, QA3 | `getresponse.com` |
| `snyk.io` | hostname consumido en QA6, QA3 | `aweber.com` |
| `stripe.com` | hostname consumido en QA6, QA8, QA1/calibración, fixture/código histórico | `wufoo.com` |
| `adyen.com` | hostname consumido en QA6, QA1/calibración | `forms.app` |
| `checkout.com` | hostname consumido en QA6, QA7 | `matomo.org` |
| `airwallex.com` | hostname consumido en QA8 | `plausible.io` |
| `wise.com` | hostname consumido en QA6, QA2 | `snowplow.io` |
| `revolut.com` | hostname consumido en QA6, QA2 | `pinecone.io` |
| `brex.com` | hostname consumido en QA6, QA7 | `buffer.com` |
| `ramp.com` | hostname consumido en QA6 | `kayako.com` |
| `mercury.com` | hostname consumido en QA6, QA7 | `liveagent.com` |
| `plaid.com` | hostname consumido en QA6, QA7 | `crisp.chat` |
| `hubspot.com` | hostname consumido en QA4, QA1/calibración | `tawk.to` |
| `mailchimp.com` | hostname consumido en QA4, QA1/calibración | `missiveapp.com` |
| `klaviyo.com` | hostname consumido en QA6, QA8, QA1/calibración | `hiverhq.com` |
| `customer.io` | hostname consumido en QA6, QA3 | `salesflare.com` |
| `activecampaign.com` | hostname consumido en QA8, QA3 | `zenefits.com` |
| `typeform.com` | hostname consumido en QA4, QA2 | `justworks.com` |
| `jotform.com` | hostname consumido en QA6, QA7 | `trinet.com` |
| `tally.so` | hostname consumido en QA8 | `paycor.com` |
| `paperform.co` | hostname consumido en QA6 | `paylocity.com` |
| `amplitude.com` | hostname consumido en QA6, QA8, QA2 | `ukg.com` |
| `mixpanel.com` | hostname consumido en QA6, QA8, QA2 | `ceipal.com` |
| `heap.io` | hostname consumido en QA6, QA8, QA2 | `meistertask.com` |
| `fullstory.com` | hostname consumido en QA8, QA2 | `niftypm.com` |
| `posthog.com` | hostname consumido en QA8 | `proofhub.com` |
| `segment.com` | hostname consumido en QA8 | `flowlu.com` |
| `rudderstack.com` | hostname consumido en QA8, QA3 | `todoist.com` |
| `hightouch.com` | hostname consumido en QA8, QA3 | `sunsama.com` |
| `snowflake.com` | hostname consumido en QA4, QA2 | `akiflow.com` |
| `fivetran.com` | hostname consumido en QA8, QA3 | `xmind.app` |
| `confluent.io` | hostname consumido en QA4, QA8, QA2 | `creately.com` |
| `elastic.co` | hostname consumido en QA4, QA8, QA2 | `raygun.com` |
| `algolia.com` | hostname consumido en QA4, QA8 | `sematext.com` |
| `contentful.com` | hostname consumido en QA4, QA8 | `lumigo.io` |
| `sanity.io` | hostname consumido en QA6 | `groundcover.com` |
| `webflow.com` | hostname consumido en QA4, QA8, QA2 | `chronosphere.io` |
| `squarespace.com` | hostname consumido en QA4, QA1/calibración | `coralogix.com` |
| `calendly.com` | hostname consumido en QA6, QA8, QA2 | `mezmo.com` |
| `docusign.com` | hostname consumido en QA4, QA1/calibración | `opslevel.com` |
| `pandadoc.com` | hostname consumido en QA6 | `strongdm.com` |
| `dropbox.com` | hostname consumido en QA4, QA1/calibración | `goteleport.com` |
| `box.com` | hostname consumido en QA4, QA2 | `tailscale.com` |
| `loom.com` | hostname consumido en QA6, QA8, QA2 | `arcticwolf.com` |
| `zapier.com` | hostname consumido en QA4, QA1/calibración | `sophos.com` |
| `make.com` | hostname consumido en QA8 | `payu.com` |

## Pool propuesto de 100

El orden exacto está en `docs/evidence/prv103-holdout-0.9-candidates.txt`. Contiene 100 hostnames normalizados y distintos: 19 candidatos originales sin solapamiento local y 81 sustituciones propuestas. No es un pool congelado mientras el precheck y la revisión remota permanezcan en FAIL.

## Precheck público pasivo

- Método intentado: GET público a `https://<hostname>/`, redirecciones normales, user-agent identificable, timeout acotado.
- Resultado: **FAIL**; 0/100 conexiones pudieron salir del proxy del entorno.
- No se realizaron POST, login, creación de cuentas, entrada de datos, acciones de negocio ni bypass de protecciones.
- No se inspeccionaron `heading`, `legend`, `introductory_text` ni `submit_text`.
- No se ejecutó PRV-103, el clasificador ni ningún QA; no se generaron predicciones, Artifact A, gold ni Artifact B.

## Condición para congelar

Ejecutar el precheck desde un runner con acceso público, reemplazar solo fallos reales antes del freeze, completar la consulta de PRs/Issue #223, y exigir PASS de los 100 sitios. Solo entonces debe cambiarse explícitamente este estado a congelado, preservando el orden.
