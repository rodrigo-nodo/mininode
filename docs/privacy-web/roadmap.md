# Privacy Web - Roadmap

**Estado:** Plan aprobado; seguimiento actualizado al 26 de octubre de 2026  
**Producto:** Mininode Privacy Web  
**Referencia oficial:** `main` (`docs/privacy-web/roadmap.md`)  
**Integración y validación:** rama `dev` y entorno `dev.mininode.io`  
**Alcance:** Preparación, piloto, comercialización y evolución del producto.

Este roadmap es la **fuente oficial del estado funcional** de Privacy Web. Distingue trabajo publicado en producción, avances exclusivos de DEV y trabajo pendiente. La rama `main` continúa siendo la fuente de verdad técnica de producción; `dev` puede contener desarrollos adicionales aún no promovidos. No se exige que sus historiales sean idénticos.

## 1. Objetivo

Preparar Privacy Web para un piloto controlado, validar su utilidad con usuarios reales y habilitar su comercialización.

Privacy Web realiza diagnósticos orientativos de señales públicas de privacidad de sitios web. No constituye una certificación legal, una auditoría completa ni una medición oficial de cumplimiento.

## 2. Situación de partida (26 de octubre de 2026)

- **MAIN / PROD:** diagnóstico gratuito con 21 controles en cinco áreas (ver [`docs/privacy.md`](../privacy.md)), Privacy Score orientativo y Plan de corrección; Access/Clerk, workspaces, guardado y revisiones; desvinculación de sitios; aliases y solicitudes de agrupación; Mininode Admin y cortesías auditadas. Incorporado mediante [PR #379](https://github.com/rodrigo-nodo/mininode/pull/379), con CI y Reviewer PASS y despliegues Cloudflare/Render confirmados. Validación visual PROD aprobada por el Product Owner.
- **MAIN y DEV:** núcleo de Billing A4 (`billing.orders` y `access.entitlements`). **Ninguna rama tiene aún el recorrido comercial completo validado**; todavía coexiste el flujo anterior `privacy.correction_plan_order`.
- **Solo DEV:** adaptador Mercado Pago, endpoints backend de checkout/webhook y herramienta interna de conciliación histórica de sitios. No están promovidos ni habilitados como flujo público E2E. La utilidad de conciliación no autoriza operaciones sobre datos reales.
- **Solo MAIN:** Content Reader V1, independiente de Privacy Web; debe preservarse al alinear ramas.
- **Pendiente:** consolidar el flujo comercial (PW-03), integrar y validar pagos de extremo a extremo (PW-04), piloto y lanzamiento comercial.

**Criterio de estado:** código presente no equivale a función comercial habilitada, despliegue confirmado ni QA completo. La diferencia de commits entre `main` y `dev` tampoco equivale a trabajo funcional pendiente: comparar archivos, contratos y entornos desplegados.

**Evidencia de publicación:** [PR #379](https://github.com/rodrigo-nodo/mininode/pull/379), [promoción funcional](../privacy-web-prod-promotion.md), [contrato Access/Admin](../access.md) y [flujo DEV → PROD](../dev-prod-release.md).

## 3. Etapa 1 - Preparación del producto (P1)

**Objetivo:** producto preparado para pruebas internas y piloto.

| ID | Actividad | Estado |
|---|---|---|
| PW-01 | Desasignar sitios de un workspace conservando historial y evidencia, con autorización correcta | **Cerrado · PROD** (PR #379) |
| PW-02 | Habilitar uso interno completo sin pago mediante entitlement explícito, auditable y separado de Billing | **Cerrado · PROD** (Mininode Admin; PR #379) |
| PW-03 | Consolidar Billing como recorrido único, retirar órdenes heredadas y desacoplar Plan de corrección y revisiones; preparación de activación con actualización automática | **En curso · DEV** (primer PR: preparación precheckout; sin cobros) |
| PW-04 | Conectar Mercado Pago con el recorrido de compra: checkout, retorno, webhook, confirmación, entitlement, expiración y reintentos | **Parcial · DEV** (adaptador y endpoints backend; E2E pendiente, no disponible en PROD) |
| PW-05 | Unificar tercera persona singular en UX, resultados, hallazgos, recomendaciones, botones, estados y errores | Pendiente |
| PW-06 | Incorporar observabilidad de diagnósticos, pagos, activaciones y fallos operativos, sin exponer datos sensibles | Pendiente |
| PW-07 | Definir y revisar acceso, privacidad y retención de datos de usuarios, diagnósticos, pagos y eventos | Pendiente |

**Avance confirmado:** PW-01 y PW-02 fueron implementados y validados en DEV, promovidos a PROD en PR #379 y aprobados visualmente tras el despliegue. No se afirma que se hayan ejecutado transacciones reales de concesión o revocación en PROD. PW-03 no ha comenzado su retirada controlada del flujo antiguo; PW-04 permanece como integración parcial de backend en DEV, sin recorrido comercial E2E.

**Criterios de cierre restantes de la etapa:** recorrido comercial oficial único; pago confirmado por proveedor habilita prestaciones y pago no confirmado no las habilita; mensajes coherentes; fallos detectables; tratamiento de datos definido.

**Decisión comercial (PW-03 → PW-04):** `billing.orders` + `access.entitlements` serán el único recorrido comercial oficial. Mercado Pago es el proveedor inicial. El historial de órdenes y activaciones del sistema heredado **no necesita migrarse ni conservarse comercialmente**; se preservan diagnósticos, cuentas, sitios y entitlements actuales. PW-03 retirará dependencias del flujo anterior `privacy.correction_plan_order`, desacoplando Plan de corrección y revisiones. El diagnóstico guardado se conserva consultable; al iniciar activación se reutiliza si tiene menos de 24 horas o se actualiza automáticamente, sin exponer plazos al cliente. Preparar compatibilidad y rollback, verificar dependencias y probar primero en DEV. **Ninguna operación destructiva en producción sin autorización explícita.**

## 4. Etapa 2 - Piloto controlado (P1)

**Objetivo:** validar valor, comprensión y uso real antes de la apertura comercial general.

| ID | Actividad | Estado |
|---|---|---|
| PW-08 | Funnel interno de uso y conversión, visible solo para Mininode | Pendiente |
| PW-09 | Definir participantes, alcance, duración, modalidad de acceso y ejecutar piloto | Pendiente |
| PW-10 | Seguir uso, pagos, hallazgos, incidencias, feedback y revisiones posteriores | Pendiente |
| PW-11 | Evaluar resultados y decidir lanzamiento, correcciones u otra validación | Pendiente |

**Funnel mínimo:** diagnóstico iniciado → terminado → resultado consultado → activación solicitada → checkout iniciado → pago confirmado → entitlement activo → revisión posterior. Diferenciar abandono, rechazo de pago y error técnico. Minimizar los datos personales registrados.

Antes del piloto, fijar criterios de éxito, participantes, modalidad gratuita o pagada y canales de soporte. Las activaciones gratuitas controladas se harán con entitlements internos, nunca con pagos ficticios.

## 5. Etapa 3 - Comercialización (P2)

**Objetivo:** abrir y operar el servicio comercial de forma confiable.

| ID | Actividad | Estado |
|---|---|---|
| PW-12 | Validar recorrido completo: compra, activación, vigencia, expiración y reactivación | Pendiente |
| PW-13 | Definir e implementar personalización Partner: logo, colores y límites de identidad Mininode | Pendiente |
| PW-14 | Definir soporte, conciliación, reembolsos e incidencias de cobro/activación | Pendiente |
| PW-15 | QA de lanzamiento con versión/SHA congelado, criterios PASS previos y autorización de publicación | Pendiente |

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
| PW-04 → PW-08 | Medir estados reales de compra y activación |
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
- **Gobierno del roadmap:** mantener **este archivo en `main`** como referencia oficial. Tras aprobar y mergear cambios del roadmap, sincronizar su contenido hacia `dev` mediante un cambio documental enfocado, sin arrastrar código. `frontend/roadmap/index.html` es un resumen público general distinto: actualizarlo solo en un trabajo editorial/UX posterior aprobado.

**Próximo frente priorizado:** PW-03 (consolidación comercial), seguido de PW-04 (integración E2E Mercado Pago). No activar cobros ni modificar registros históricos por actualizar este roadmap. Nunca mergear sin autorización explícita.
