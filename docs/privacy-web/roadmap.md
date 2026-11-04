# Privacy Web - Roadmap

**Estado:** Plan aprobado; seguimiento actualizado al 03 de noviembre de 2026  
**Producto:** Mininode Privacy Web  
**Referencia oficial:** `main` (`docs/privacy-web/roadmap.md`)  
**Integración y validación:** rama `dev` y entorno `dev.mininode.io`  
**Alcance:** Preparación, piloto, comercialización y evolución del producto.

Este roadmap es la **fuente oficial del estado funcional** de Privacy Web. Distingue trabajo publicado en producción, avances exclusivos de DEV y trabajo pendiente. La rama `main` continúa siendo la fuente de verdad técnica de producción; `dev` puede contener desarrollos adicionales aún no promovidos. No se exige que sus historiales sean idénticos.

## 1. Objetivo

Preparar Privacy Web para un piloto controlado, validar su utilidad con usuarios reales y habilitar su comercialización.

Privacy Web realiza diagnósticos orientativos de señales públicas de privacidad de sitios web. No constituye una certificación legal, una auditoría completa ni una medición oficial de cumplimiento.

## 2. Estado verificado y preparación de piloto (03 de noviembre de 2026)

- **MAIN / PROD:** diagnóstico gratuito con 21 controles en cinco áreas (ver [`docs/privacy.md`](../privacy.md)), Privacy Score orientativo y Plan de corrección; Access/Clerk, workspaces, guardado y revisiones; desvinculación de sitios; aliases y solicitudes de agrupación; Mininode Admin y cortesías auditadas. Incorporado mediante [PR #379](https://github.com/rodrigo-nodo/mininode/pull/379), con CI y Reviewer PASS y despliegues Cloudflare/Render confirmados. Validación visual PROD aprobada por el Product Owner.
- **MAIN y DEV:** núcleo de Billing A4 (`billing.orders` y `access.entitlements`). **Ninguna rama tiene aún el recorrido comercial completo validado**. El flujo comercial legado fue retirado del código de MAIN en PR #422. Las tres tablas antiguas `privacy.correction_plan`, `privacy.correction_plan_order` y `privacy.correction_plan_check` fueron eliminadas de PostgreSQL PROD tras autorización destructiva específica, ejecución única y comprobación independiente de ausencia, documentadas en PR #430. **No repetir ni ampliar esas operaciones.**
- **Solo DEV:** adaptador Mercado Pago, endpoints backend de checkout/webhook y herramienta interna de conciliación histórica de sitios. No están promovidos ni habilitados como flujo público E2E. La utilidad de conciliación no autoriza operaciones sobre datos reales.
- **Solo MAIN:** Content Reader V1, independiente de Privacy Web; debe preservarse al alinear ramas.
- **PW-03 cerrado:** esquema y Plan autenticado, retirada por código y retiro físico legado finalizados en PROD. **Pendiente:** QA funcional posterior al retiro, coherencia de score/cobertura y controles visibles, integración E2E Mercado Pago (PW-04, solo para venta), piloto y lanzamiento comercial.

**Criterio de estado:** código presente no equivale a función comercial habilitada, despliegue confirmado ni QA completo. La diferencia de commits entre `main` y `dev` tampoco equivale a trabajo funcional pendiente: comparar archivos, contratos y entornos desplegados.

**Evidencia de publicación:** [PR #379](https://github.com/rodrigo-nodo/mininode/pull/379), [promoción funcional](../privacy-web-prod-promotion.md), [contrato Access/Admin](../access.md) y [flujo DEV → PROD](../dev-prod-release.md).


**PW-03 completado en PROD:** PR #416–#418 incorporaron esquema, backend e interfaz del Plan por entitlement; PR #421 aportó historial vinculado; PR #422 retiró las rutas y servicios del comercio anterior. Tras los procedimientos de seguridad PR #423–#429, el 03-11-2026 se retiraron físicamente las tres tablas legado de PostgreSQL PROD **con autorización destructiva expresa**; PR #430 registra una comprobación independiente de ausencia y conservación de `privacy.diagnostic`, `privacy.entitled_plan`, `privacy.entitled_plan_check`, `access.entitlements` y `billing.orders`. El backend `66ea22f1` estaba LIVE durante esa operación; el último commit `main` `73bffc2d` es documental y **no se acredita aquí su despliegue en Render**. No ejecutar de nuevo operaciones sobre las tablas retiradas. Mercado Pago y PW-04 siguen fuera del alcance de PW-03.

## 3. Etapa 1 - Preparación del producto (P1)

**Objetivo:** producto preparado para pruebas internas y piloto.

| ID | Actividad | Estado |
|---|---|---|
| PW-01 | Desasignar sitios de un workspace conservando historial y evidencia, con autorización correcta | **Cerrado · PROD** (PR #379) |
| PW-02 | Habilitar uso interno completo sin pago mediante entitlement explícito, auditable y separado de Billing | **Cerrado · PROD** (Mininode Admin; PR #379) |
| PW-03 | Retirar el flujo comercial antiguo de órdenes/activaciones y eliminar controladamente las tres tablas históricas | **Cerrado · PROD** (PR #416–#418, #421–#430; retiro físico ejecutado y verificado) |
| PW-04 | Conectar Mercado Pago con el recorrido de compra: checkout, retorno, webhook, confirmación, entitlement, expiración y reintentos | **Parcial · DEV** (adaptador y endpoints backend; E2E pendiente, no disponible en PROD) |
| PW-05 | Unificar tercera persona singular en UX, resultados, hallazgos, recomendaciones, botones, estados y errores | Pendiente |
| PW-06 | Incorporar observabilidad de diagnósticos, pagos, activaciones y fallos operativos, sin exponer datos sensibles | Pendiente |
| PW-07 | Definir y revisar acceso, privacidad y retención de datos de usuarios, diagnósticos, pagos y eventos | Pendiente |

**Avance confirmado:** PW-01 y PW-02 fueron implementados y validados en DEV, promovidos a PROD en PR #379 y aprobados visualmente tras el despliegue; esto no acredita concesiones o revocaciones reales en PROD. PW-03 está cerrado: nuevo Plan, retirada de servicios y frontend comercial legado y eliminación física PROD ejecutada y verificada conforme al [runbook](pr5-legacy-retirement.md). La operación de retiro **no equivale** a QA E2E del Plan posterior a esa eliminación. PW-04 permanece como integración parcial en DEV, sin recorrido comercial E2E.

**Criterios de preparación del piloto gratuito:** diagnóstico y comunicación de cobertura comprensibles, contrato visible de controles consistente, acceso/guardado, concesiones internas auditables, Plan y revisiones funcionales con el esquema PROD posterior a PW-03, fallos detectables y tratamiento mínimo de datos definido. **Criterios adicionales para venta:** pago confirmado por proveedor habilita prestaciones y pago no confirmado no las habilita, E2E de Mercado Pago, expiración, reintentos y conciliación; corresponden a PW-04/PW-12 y **no bloquean un piloto gratuito**.

**Decisión comercial (PW-03 → PW-04):** `billing.orders` + `access.entitlements` constituyen el recorrido comercial oficial previsto; Mercado Pago es el proveedor inicial. PW-03 retiró las rutas/servicios legados y, posteriormente, las tres tablas históricas, previa autorización destructiva separada. Se preservaron diagnósticos, entitlements y Plan nuevo. **No volver a ejecutar operaciones sobre las tablas retiradas.** PW-04 requiere su propia implementación, validación e integración E2E antes de habilitar cobros. **Ninguna operación destructiva en producción sin autorización explícita.**

## 4. Etapa 2 - Piloto controlado (P1)

**Objetivo:** validar valor, comprensión y uso real antes de la apertura comercial general.

| ID | Actividad | Estado |
|---|---|---|
| PW-08 | Funnel interno de uso y conversión, visible solo para Mininode | Pendiente |
| PW-09 | Definir participantes, alcance, duración, modalidad de acceso y ejecutar piloto | Pendiente |
| PW-10 | Seguir uso, pagos, hallazgos, incidencias, feedback y revisiones posteriores | Pendiente |
| PW-11 | Evaluar resultados y decidir lanzamiento, correcciones u otra validación | Pendiente |

**Funnel mínimo para piloto gratuito:** diagnóstico iniciado → terminado → resultado consultado → guardado en cuenta → concesión interna de entitlement → Plan consultado → revisión posterior → feedback/incidencia. Registrar lo mínimo necesario sin pagos ficticios. **Funnel comercial futuro (PW-04/PW-12):** activación solicitada → checkout → pago confirmado por proveedor → entitlement activo → revisión posterior. Distinguir abandono, rechazo y error técnico cuando se implemente.

Antes del piloto, fijar criterios de éxito, participantes, modalidad gratuita o pagada y canales de soporte. Las activaciones gratuitas controladas se harán con entitlements internos, nunca con pagos ficticios.


### Puerta de QA para piloto gratuito controlado (pendiente de PASS)

| Control | Evidencia requerida | Estado al 03-11-2026 |
|---|---|---|
| **PW-QA-01: comunicación de score y cobertura** | No presentar un 100/100 o «Bien» como evidencia suficiente cuando numerosos controles no pudieron evaluarse; definir y comprobar la experiencia sin cambiar el algoritmo de scoring implícitamente | **Por resolver**; QA exploratorio Work del 02-11 detectó el caso |
| **PW-QA-02: contrato visible de controles** | Conciliar los 21 controles del backend con el texto «19 puntos» y la enumeración del frontend; incluir tests que eviten divergencia y verificar PROD | **Por resolver**; [issue #204](https://github.com/rodrigo-nodo/mininode/issues/204) |
| **PW-QA-03: E2E posterior a PW-03** | Congelar SHA, comprobar frontend Cloudflare y backend Render LIVE, guardar diagnóstico, autenticar, otorgar/revocar cortesía interna autorizada, leer Plan, repetir revisión, comparar historial y validar aislamiento por workspace y errores sin tablas legado | **No verificado** luego del retiro físico; no realizar diagnósticos externos no autorizados |
| **PW-QA-04: experiencia y tratamiento mínimo** | Verificar flujo OTP, móvil, textos críticos, fallos detectables, soporte básico y datos/accesos/retención aplicables a pilotos | **Parcial / pendiente de evidencia**; coordinar con PW-05–PW-07 |

**Criterio de PASS:** evidencias por prueba y versión/SHA efectivamente publicados, sin FAIL de severidad alta ni dudas de autorización/aislamiento; si corresponde, validación independiente y del Product Owner. El QA exploratorio anterior (12 PASS, 1 FAIL, 3 no verificados) **no** acredita el nuevo estado después de PW-03. La concesión de un entitlement de prueba requiere autorización operativa y no se realiza por el solo hecho de aprobar el roadmap. **No es un bloqueo de piloto gratuito** tener PW-04, pagos, checkout o reembolsos aún pendientes.

## 5. Etapa 3 - Comercialización (P2)

**Objetivo:** abrir y operar el servicio comercial de forma confiable.

| ID | Actividad | Estado |
|---|---|---|
| PW-12 | Validar recorrido completo: compra, activación, vigencia, expiración y reactivación | Pendiente |
| PW-13 | Definir e implementar personalización Partner: logo, colores y límites de identidad Mininode | Pendiente |
| PW-14 | Definir soporte, conciliación, reembolsos e incidencias de cobro/activación | Pendiente |
| PW-15 | QA de lanzamiento con versión/SHA congelado, criterios PASS previos y autorización de publicación | Pendiente |
| PW-22 | Definir precios por **superficie web efectivamente inspeccionada** (páginas únicas, profundidad, formularios, subdominios y frecuencia de revisión), con plan base y reglas de volumen multisitio; medir cobertura y costos en pilotos | **Por definir** (sin cambiar la tarifa actual) |

**Roadmap transversal:** futuro `preview.mininode.io` (MIN-01), política de visibilidad del repositorio (MIN-02) y el detalle de precios por superficie (PW-22) están en [`docs/roadmap.md`](../roadmap.md). Son iniciativas por definir, no implementación ni precios aprobados.

**Modelo comercial vigente:** Privacy Web activo por **CLP $9.900**, durante **un mes calendario**, sin renovación automática, con revisiones manuales durante la vigencia.

La URL de retorno del proveedor no confirma el pago: la activación depende de la verificación confiable del proveedor y de Billing. Probar aprobación, rechazo, pendiente, duplicados, reintentos, expiración y conciliación. Validar en entornos correspondientes antes de abrir ventas.

## 6. Etapa 4 - Evolución del diagnóstico (P3)

**Objetivo:** ampliar evidencia y valor recurrente sin alterar prematuramente los controles vigentes.

| ID | Actividad | Estado |
|---|---|---|
| PW-16 | Completar validación independiente del extractor semántico común | Pendiente |
| PW-17 | Implementar y validar PRV-202 como control inicialmente informativo | Pendiente |
| PW-18 | Priorizar brechas web-observables de cobertura legal sin equipararlas a cumplimiento | Pendiente |
| PW-19 | Evolucionar Formularios después de V1 (PRV-103/PRV-104) sobre semántica validada | Pendiente |
| PW-20 | Incorporar revisiones automáticas y alertas de cambios | Pendiente |
| PW-21 | Validar flujo manual de aprobación de agrupación de sitios cuando exista un caso real | **Validación de caso real pendiente** (código y pruebas en DEV y PROD) |

Mantener inspección pública y pasiva, límites entre Privacy Web y Privacy Data, tests de consistencia, QA independiente y versionado cuando cambien controles, scoring o comportamiento público. Esta etapa **no bloquea el piloto**.

## 7. Dependencias y secuencia

| Dependencia | Motivo |
|---|---|
| PW-03 → PW-04 | Consolidar un único recorrido comercial |
| PW-02 → PW-09 | Facilitar uso interno y accesos gratuitos controlados |
| PW-04 → PW-08 (solo funnel pagado) | Los estados reales de compra son necesarios únicamente para la medición comercial; PW-08 puede comenzar con funnel gratuito sin PW-04 |
| PW-05, PW-06, PW-07 → PW-09 | Experiencia consistente, observabilidad y tratamiento de datos |
| PW-08 → PW-10 → PW-11 | Medir y evaluar el piloto |
| PW-11 → PW-15 | Incorporar aprendizajes antes del lanzamiento |
| PW-16 → PW-17 y PW-19 | Validar semántica antes de ampliar su uso |

Los trabajos independientes podrán avanzar en paralelo mediante PRs pequeños. El pago se habilita técnicamente en la etapa 1; la etapa 3 valida su operación y autoriza el lanzamiento.

## 8. Estados y seguimiento

- **Pendiente:** actividad identificada sin implementación acreditada para su objetivo completo.
- **Parcial · DEV:** existe código o pruebas en `dev`, pero faltan componentes, integración E2E o validación; **no** implica publicación comercial.
- **En curso:** desarrollo o preparación activos.
- **Validación / validación de caso real pendiente:** implementación disponible, pero falta una comprobación específica para cerrar la actividad.
- **Cerrado · PROD:** funcionalidad publicada en `main` y PROD, con las validaciones aplicables aprobadas y evidencia trazable; el alcance de esas validaciones se declara.
- **Bloqueado:** falta una dependencia que impide avanzar.

Los estados se actualizarán con evidencia del repositorio, CI, QA, desplegado efectivo y validación del Product Owner; no por suposición. PW-01 y PW-02 se consideran cerrados por la promoción #379 y la aceptación visual de PROD; PW-21 conserva la validación de un caso real pendiente. No interpretar `Cerrado · PROD` como aprobación de pagos o de actividades distintas.

## 9. Fuera de alcance

Privacy Data; certificación legal; auditoría integral; modificación automática de sitios; renovación automática; controles de procesos internos no observables públicamente; ampliaciones no acordadas.

## 10. Flujo de implementación y alineación

- **Desarrollo / integración:** cambios enfocados en DEV, CI y validación funcional del Product Owner en **https://dev.mininode.io**, asegurando que el backend desplegado corresponda a la versión que se está validando. Los Branch Previews arbitrarios no sustituyen el entorno integrado de Access/Clerk.
- **Promoción selectiva:** partir de `main` actualizado, preparar un PR propio hacia `main` con **solo la funcionalidad aprobada** y dependencias necesarias. Conservar componentes exclusivos de MAIN (como Content Reader V1) y excluir trabajos experimentales de DEV. Revisar diff y CI, obtener autorización expresa de merge y confirmar despliegue y validación breve de PROD.
- **Alineación permanente:** MAIN y DEV comparten la **base funcional aprobada**, mientras DEV puede mantener avances en validación. Las diferencias intencionales de código, datos, credenciales e infraestructura se registran; **no** hacer merge masivo para igualar commits. Ver [`docs/dev-prod-release.md`](../dev-prod-release.md).
- **Gobierno del roadmap:** mantener **este archivo en `main`** como referencia oficial del estado del producto en producción. DEV conserva su documentación propia de ejecución, pero consulta las decisiones estratégicas directamente en el roadmap transversal de MAIN. No copiar roadmaps completos entre ramas. `frontend/roadmap/index.html` sigue siendo un resumen público general distinto.

**Próximo frente priorizado:** conciliación funcional DEV/MAIN/PROD, comunicación de score/cobertura y matriz de controles, y QA funcional posterior al retiro PW-03 para un piloto gratuito controlado. PW-04 se promueve únicamente al preparar venta real. No activar cobros ni modificar registros históricos por actualizar este roadmap. Nunca mergear sin autorización explícita.

### PW-03 PROD — PR 3: interfaz de Plan por entitlement (30-10-2026)

El backend de PR #417 fue integrado a `main` en SHA `cf51c8d3` y publicado en Render PROD (estado LIVE, sin nuevas migraciones). Este PR 3 propone la interfaz de **Estado de mi sitio / Qué debo mejorar / Mis avances**, con lectura del Plan, acciones actuales, evolución y revisiones repetibles.

**Compatibilidad durante la transición:** la página nueva usa `/privacy/mi-plan/?workspace_site_id=<uuid>`, en lugar de reemplazar `/privacy/plan/` que todavía recibe tokens de los planes antiguos mediante la regla `/privacy/plan/:token /privacy/plan/ 200`. El frontend y proxy comerciales antiguos se retiran en PR 4. Al retirar el flujo legado se revisará la URL canónica sin romper enlaces anteriores.

La navegación desde `/access/` consulta `GET /billing/workspaces/{workspace_id}/entitlements` y muestra **Abrir Privacy Web** solamente cuando el sitio pertenece al workspace mostrado y su entitlement está vigente. Si falla la consulta, conserva la navegación de diagnóstico gratuito sin afirmar ausencia de entitlement. El proxy incorpora solo las rutas nuevas autenticadas y **mantiene** las reglas para el flujo viejo hasta PR 4.

Esta etapa no habilita pagos, no crea entitlements, no cambia PostgreSQL ni controles/scoring. La preparación de activación ya existe en backend, pero la UX comercial definitiva seguirá el retiro del legado en PR 4 y la integración de cobro en PW-04. Se requieren CI y validación visual con Clerk en Branch Preview antes de autorizar merge.
