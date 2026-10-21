# Privacy Web - Roadmap

**Estado:** Plan aprobado; ejecución pendiente por actividad  
**Producto:** Mininode Privacy Web  
**Rama de integración:** `dev`  
**Alcance:** Preparación, piloto, comercialización y evolución del producto.

## 1. Objetivo

Preparar Privacy Web para un piloto controlado, validar su utilidad con usuarios reales y habilitar su comercialización.

Privacy Web realiza diagnósticos orientativos de señales públicas de privacidad de sitios web. No constituye una certificación legal, una auditoría completa ni una medición oficial de cumplimiento.

## 2. Situación de partida

- Diagnóstico público gratuito; 21 controles en cinco áreas (ver `docs/privacy.md`).
- Privacy Score, resultados orientativos, Plan de corrección y revisiones.
- Mininode Access, workspaces y diagnósticos vinculados a sitios.
- Backend inicial de Billing A4 y adaptador Mercado Pago.
- **Pendiente:** habilitar y validar el recorrido comercial completo para clientes.

Este documento identifica trabajo futuro; la existencia de código parcial no equivale a una funcionalidad comercial validada. Los estados se confirmarán contra el código, tests y entornos vigentes al iniciar cada trabajo.

## 3. Etapa 1 - Preparación del producto (P1)

**Objetivo:** producto preparado para pruebas internas y piloto.

| ID | Actividad | Estado |
|---|---|---|
| PW-01 | Desasignar sitios de un workspace conservando historial y evidencia, con autorización correcta | Validación |
| PW-02 | Habilitar uso interno completo sin pago mediante entitlement explícito, auditable y separado de Billing | Pendiente |
| PW-03 | Retirar el flujo comercial antiguo de órdenes/activaciones, sus endpoints, servicios, tests y documentación; preparar migración controlada | Pendiente |
| PW-04 | Conectar Mercado Pago con el recorrido de compra: checkout, retorno, webhook, confirmación, entitlement, expiración y reintentos | Pendiente |
| PW-05 | Unificar tercera persona singular en UX, resultados, hallazgos, recomendaciones, botones, estados y errores | Pendiente |
| PW-06 | Incorporar observabilidad de diagnósticos, pagos, activaciones y fallos operativos, sin exponer datos sensibles | Pendiente |
| PW-07 | Definir y revisar acceso, privacidad y retención de datos de usuarios, diagnósticos, pagos y eventos | Pendiente |

**Criterios de cierre:** desasignación sin pérdida indebida de evidencia; acceso interno sin simular pagos; recorrido comercial oficial único; pago confirmado por proveedor habilita prestaciones y pago no confirmado no las habilita; mensajes coherentes; fallos detectables; tratamiento de datos definido.

**Decisión comercial:** `billing.orders` + `access.entitlements` constituyen el único recorrido comercial oficial. Mercado Pago es el proveedor inicial. Se retira el flujo anterior `privacy.correction_plan_order`, sin eliminar las funcionalidades de diagnóstico y Plan de corrección. Antes de eliminar tablas, verificar dependencias y realizar migración en DEV; **ninguna operación destructiva en producción sin aprobación explícita**.

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
| PW-21 | Validar flujo manual de aprobación de agrupación de sitios cuando exista un caso real | Validación pendiente |

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

- **Pendiente:** trabajo identificado, no iniciado.
- **En curso:** preparación o implementación activa.
- **Validación:** cambio implementado, pendiente de comprobación.
- **Cerrado:** criterios cumplidos y cambio integrado cuando corresponda.
- **Bloqueado:** existe una dependencia impeditiva.

Los estados se actualizarán con evidencia del repositorio, CI, preview, QA y validación del Product Owner; no por suposición.

## 9. Fuera de alcance

Privacy Data; certificación legal; auditoría integral; modificación automática de sitios; renovación automática; controles de procesos internos no observables públicamente; ampliaciones no acordadas.

## 10. Flujo de implementación

`dev` → rama enfocada → PR hacia `dev` → CI del último commit → **Cloudflare Branch Preview estable de esa rama** → validación del Product Owner → merge autorizado a `dev`.

Cuando corresponda publicar: `dev` → PR hacia `main` → CI y validación → merge autorizado.

El Branch Preview debe corresponder al último commit del PR; no se usará como referencia principal una URL puntual de despliegue por commit. La fuente de verdad para producción es `main`. No mergear sin autorización explícita.
