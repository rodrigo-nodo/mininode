# Privacy Web — Conciliación funcional DEV / MAIN / PROD

**Fecha de corte:** 03-11-2026  
**Repositorio:** `rodrigo-nodo/mininode`  
**Fuente de verdad técnica:** `main`  
**MAIN examinado:** `73bffc2d24a974943b084a1bff9eefd34eacace5`  
**DEV examinado:** `e3af7e48ac8458f4cfa8bc8a586ec30ec1aaedac`  
**Tipo de revisión:** estática, de solo lectura; sin modificar datos, despliegues ni servicios.

## Objetivo y alcance

Distinguir funcionalidades **ya promovidas a MAIN**, **pendientes reales** y **exclusivas de DEV por decisión o etapa**, sin inferir pendientes a partir de la divergencia histórica de commits. La verificación de despliegue y el QA funcional de PROD son controles separados.

La comparación recursiva de los árboles Git de las dos ramas arrojó: **382 archivos idénticos**, **44 rutas presentes en ambas con contenido diferente**, **27 rutas exclusivas de DEV** y **23 exclusivas de MAIN** (449 archivos en MAIN y 453 en DEV). Estos recuentos **no** equivalen a una lista de funcionalidades por promover.

## Matriz funcional de conciliación

| Funcionalidad / evidencia | Estado de MAIN vs DEV | Clasificación | Acción |
|---|---|---|---|
| Diagnóstico público: API `api/privacy.py`, matriz `controls.json`, evaluador/scoring y contratos de Access | Archivos de motor y contratos clave idénticos en ambas ramas | **Ya promovida a MAIN (código)** | Solo QA y cotejo de backend desplegado; no copiar DEV a MAIN |
| Guardado, Access, workspaces, aliases y operador/Admin | Promoción selectiva a MAIN mediante [#379](https://github.com/rodrigo-nodo/mininode/pull/379); `api/access.py` y `services/site_aliases.py` idénticos; las vistas Access pueden tener adaptaciones posteriores en MAIN | **Ya promovida a MAIN (con adaptaciones)** | QA de flujo autenticado y permisos, sin tratar diferencias de interfaz como features por promover |
| Plan vinculado al entitlement, historial y comparaciones | Promovido selectivamente a MAIN por [#416](https://github.com/rodrigo-nodo/mininode/pull/416), [#417](https://github.com/rodrigo-nodo/mininode/pull/417), [#418](https://github.com/rodrigo-nodo/mininode/pull/418) y [#421](https://github.com/rodrigo-nodo/mininode/pull/421). MAIN usa `/privacy/mi-plan/`; DEV conserva `/privacy/plan/` y `plan-assets`. Servicios `privacy_entitled_plan` difieren | **Ya promovida a MAIN, con implementación propia** | Verificar equivalencia **funcional**, no de archivo/ruta; revisar continuidad entre períodos, historial, revisiones y comparación en PROD antes de PASS |
| PW-03, retiro del comercio anterior | DEV retiró código/tablas legado mediante PRs propios; MAIN retiró código y concluyó retiro físico autorizado en PROD, documentado en [#422](https://github.com/rodrigo-nodo/mininode/pull/422) y [#430](https://github.com/rodrigo-nodo/mininode/pull/430) | **Ya promovida / cerrada** | Ninguna operación adicional sobre tablas retiradas; QA funcional posterior |
| PW-04 Mercado Pago | `services/mercadopago.py` y tests del adaptador solo en DEV; `api/billing.py` DEV tiene checkout y webhook no presentes en MAIN | **Pendiente real de promoción e integración** | No incluir en piloto gratuito controlado; para venta requiere alcance aprobado, seguridad, CI, proveedor, despliegue y QA E2E. No copiar solo adaptador sin dependencias |
| Herramienta `services/site_reconciliation.py` | Exclusiva de DEV; operación interna de reconciliación histórica de sitios | **Exclusiva de DEV en esta etapa** | No promover sin caso real, evaluación de permisos e impacto en datos |
| `frontend/privacy/plan-demo/`, `plan-assets/` y `plan/` | Presentes en DEV; MAIN usa la nueva implementación `mi-plan` | **Exclusiva de DEV / legado de desarrollo** | No reintroducir estas rutas como sustituto del Plan de MAIN |
| Migración `20261029_pw03c3_retire_legacy_dev.sql` | Exclusiva de DEV por su ámbito; MAIN tiene procedimientos/runbook separados para PROD | **Exclusiva de DEV por entorno** | No copiar SQL DEV a PROD; retiro PROD ya terminó |
| Content Reader V1 y `frontend/privacy/mi-plan/` | Archivos propios de MAIN, sin equivalente exacto en DEV | **Ya incorporados a MAIN / evolución de MAIN** | Preservarlos en futuras promociones selectivas; no sobrescribirlos con versiones DEV |
| `render.yaml` y automatización asociada a entornos | `render.yaml` solo en DEV; workflows y scripts también difieren | **Diferencia de entorno; decisión pendiente si se quisiera alinear** | Revisar configuración antes de cualquier promoción; no asumir equivalencia de infraestructura |

### Brechas compartidas: no confundir con pendientes DEV → MAIN

| Brecha | Evidencia | Tratamiento |
|---|---|---|
| **21 controles backend vs 19 declarados por la interfaz** | `controls.json` es idéntico en ambas ramas, mientras `frontend/privacy/index.html` de ambas dice «19 puntos». El frontend estático omite PRV-102/PRV-103 en su enumeración. Ver [issue #204](https://github.com/rodrigo-nodo/mininode/issues/204) | Confirmar contrato real y visualización publicada; definir ajuste UX/tests como cambio propio y enfocado, no como promoción DEV |
| **Privacy Score y cobertura de evidencia** | QA exploratorio Work del 02-11-2026 observó 100/100 con numerosos controles «No pudimos revisarlo». Backend expone métricas de score y cobertura separadas | Definir presentación comprensible de cobertura/confianza antes del piloto; **no** modificar scoring sin decisión |
| **QA posterior a PW-03** | El retiro físico PROD está documentado en #430, pero no consta aquí una ejecución E2E posterior que pruebe Plan, historial y autorizaciones con esquema retirado | Bloqueante para PASS de piloto; acceso controlado y sin pagos reales |
| **OTP, móvil y versión publicada** | La revisión Work anterior dejó OTP y móvil sin verificar; los SHAs de Cloudflare y Render live deben cotejarse por servicio | Cerrar con evidencia de despliegue y QA; la igualdad de código Git no prueba configuración ni servicio publicado |
| **Documentación de estado** | `docs/privacy-web/roadmap.md` de MAIN todavía indica PW-03 «En curso»; `docs/privacy.md` aún dice que tablas legadas esperan retiro. El roadmap de DEV contiene estados históricos distintos | Actualizar mediante PR documental separado, sin sincronizar copias completas entre ramas |

## Criterio de publicación y límites de esta revisión

1. **Código en MAIN ≠ despliegue confirmado.** La verificación anterior de backend PROD LIVE correspondía a `66ea22f1`; el último MAIN examinado es `73bffc2d`. El último commit de MAIN documenta retiro: no se afirma aquí que Render sirva ese SHA. Comprobar SHA/live por servicio antes del PASS.
2. La aplicación pública y DEV no se probaron E2E en esta conciliación; las revisiones publicadas anteriores no sustituyen un QA posterior al retiro.
3. El piloto **gratuito controlado** puede usar Clerk/Access y entitlements internos; **no requiere** PW-04, pero sí QA de concesión, Plan, revisiones y aislamiento.
4. **No hacer merge global de `dev` en `main`.** Promover solo el alcance explícitamente aprobado con un PR focalizado, tests y documentación.
5. No ejecutar diagnósticos nuevos, escrituras en BD, SQL de retiro, compras, activaciones ni cambios de configuración como parte de esta conciliación.

## Decisiones y siguiente paso

- **Cerrado en código:** motor, Access/guardado, Plan autenticado (con implementación MAIN), PW-03.
- **Pendiente para lanzamiento de pago:** PW-04 y validaciones comerciales.
- **No promover por ahora:** conciliación operativa histórica y páginas demo/legado DEV.
- **Antes de piloto gratuito:** resolver comunicación del score/cobertura, coherencia de matriz de controles y QA funcional posterior al retiro, con evidencia del despliegue.
- **Documentación:** actualizar estados de `docs/privacy-web/roadmap.md` y `docs/privacy.md` en un PR independiente; distinguir «Cerrado en PROD» de «QA de cierre pendiente».

### Fuentes de revisión

- Código y árboles Git: [MAIN](https://github.com/rodrigo-nodo/mininode/tree/73bffc2d24a974943b084a1bff9eefd34eacace5) y [DEV](https://github.com/rodrigo-nodo/mininode/tree/e3af7e48ac8458f4cfa8bc8a586ec30ec1aaedac).
- [Flujo DEV → PROD](../dev-prod-release.md), [roadmap Privacy Web](roadmap.md), [roadmap estratégico](../roadmap.md).
- PRs de promoción y retiro: #379, #416–#418, #421–#423, #428–#430.
- Evidencia previa del usuario: reporte exploratorio Work **QA-Privacy-Web-Work-001.md** (02-11-2026), no un QA posterior al retiro.
