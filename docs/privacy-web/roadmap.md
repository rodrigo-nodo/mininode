# Privacy Web - Roadmap

**Estado:** Plan aprobado; seguimiento actualizado al 27 de octubre de 2026  
**Producto:** Mininode Privacy Web  
**Referencia oficial:** `main` (`docs/privacy-web/roadmap.md`)  
**Integración y validación:** rama `dev` y entorno `dev.mininode.io`  
**Alcance:** Preparación, piloto, comercialización y evolución del producto.

Este roadmap es la **fuente oficial del estado funcional** de Privacy Web. Distingue trabajo publicado en producción, avances exclusivos de DEV y trabajo pendiente. La rama `main` continúa siendo la fuente de verdad técnica de producción; `dev` puede contener desarrollos adicionales aún no promovidos. No se exige que sus historiales sean idénticos.

## 1. Objetivo

Preparar Privacy Web para un piloto controlado, validar su utilidad con usuarios reales y habilitar su comercialización.

Privacy Web realiza diagnósticos orientativos de señales públicas de privacidad de sitios web. No constituye una certificación legal, una auditoría completa ni una medición oficial de cumplimiento.

## 2. Situación de partida (27 de octubre de 2026)

- **MAIN / PROD:** diagnóstico gratuito con 21 controles en cinco áreas (ver [`docs/privacy.md`](../privacy.md)), Privacy Score orientativo y Plan de corrección; Access/Clerk, workspaces, guardado y revisiones; desvinculación de sitios; aliases y solicitudes de agrupación; Mininode Admin y cortesías auditadas. Incorporado mediante [PR #379](https://github.com/rodrigo-nodo/mininode/pull/379), con CI y Reviewer PASS y despliegues Cloudflare/Render confirmados. Validación visual PROD aprobada por el Product Owner.
- **MAIN y DEV:** núcleo de Billing A4 (`billing.orders` y `access.entitlements`). **Ninguna rama tiene aún el recorrido comercial completo validado**; todavía coexiste el flujo anterior `privacy.correction_plan_order`.
- **Solo DEV:** adaptador Mercado Pago, endpoints backend de checkout/webhook y herramienta interna de conciliación histórica de sitios. No están promovidos ni habilitados como flujo público E2E. La utilidad de conciliación no autoriza operaciones sobre datos reales.
- **Solo MAIN:** Content Reader V1, independiente de Privacy Web; debe preservarse al alinear ramas.
- **Pendiente:** consolidar el flujo comercial (PW-03), integrar y validar pagos de extremo a extremo (PW-04), piloto y lanzamiento comercial.

**Criterio de estado:** código presente no equivale a función comercial habilitada, despliegue confirmado ni QA completo. La diferencia de commits entre `main` y `dev` tampoco equivale a trabajo funcional pendiente: comparar archivos, contratos y entornos desplegados.

**Evidencia de publicación:** [PR #379](https://github.com/rodrigo-nodo/mininode/pull/379), [promoción funcional](../privacy-web-prod-promotion.md), [contrato Access/Admin](../access.md) y [flujo DEV → PROD](../dev-prod-release.md).

## 2.1. Estado comprobado por entorno (27 de octubre de 2026)

| Capacidad / hito | PROD (`main`) | DEV (`dev`) |
|---|---|---|
| Diagnóstico gratuito (21 controles, cinco áreas), score orientativo y consulta de resultados | **Implementado y validado** (promoción #379) | **Disponible** como base funcional |
| Access/Clerk, workspaces, sitios guardados y desvinculación | **Implementado y validado** (alcance promovido en #379) | **Implementado y validado** |
| Mininode Admin y entitlements internos auditados | **Implementado y validado** (#379; sin afirmar ejecución de operaciones reales en PROD) | **Disponible** |
| Plan autenticado y revisiones asociadas a entitlement | **No promovido en esta fase** | **Implementado y validado funcionalmente**; PW-03B, con legado aún coexistente |
| Mis sitios: acción única según activación, consulta agrupada y mensajes de error | **No promovido en esta fase** | **Validado visual y funcionalmente** (PRs #388–#393; backend Render DEV) |
| Header compartido de Privacy Web Plan | **Sin nueva promoción de esta etapa** | **PASS** (PRs #385–#387) |
| Título dinámico de prioridades del diagnóstico gratuito | **Sin nueva promoción de esta etapa** | **Mergeado** (#394, CI SUCCESS); validación visual posterior pendiente |
| Mercado Pago, checkout y webhook | **Recorrido E2E no habilitado** | **Integración backend parcial**; compra E2E sin validar |
| Rediseño integral del Plan — etapa C | **No implementado** | **UX aprobada, implementación pendiente** |

**Regla de lectura:** distinguir código presente, CI, despliegue y validación de usuario; no dar por promovido a PROD lo validado solo en DEV. El estado se basa en evidencia de PRs y validaciones documentadas; no sustituye una comprobación operativa nueva de cada entorno.

## 3. Próximo trabajo prioritario — Privacy Web Plan — Etapa C: rediseño UX aprobado (27 de octubre de 2026)

**Estado:** definición de producto y UX aprobada; implementación pendiente. **Alcance de validación:** rama `dev`, integración Clerk/Access en `https://dev.mininode.io`; PROD sin cambios. Los PRs de esta fase tendrán destino `dev`, con CI y autorización explícita antes de merge. No utilizar Branch Preview como entorno principal.

**Objetivo:** integrar diagnóstico, recomendaciones y seguimiento en una única experiencia de Privacy Web activo, clara para usuarios no técnicos y partners con múltiples sitios. El diagnóstico gratuito permanece para usuarios sin activación. Mantener evaluación pública/pasiva y evitar cualquier promesa de certificación o cumplimiento legal.

### Criterios transversales

- Una pantalla con tres secciones navegables: **Estado de mi sitio**, **Qué debo mejorar** y **Mis avances**; iniciar en Estado de mi sitio.
- Navegación adaptable: tres pestañas en notebook/tablet y navegación compacta en celular, sin perder contenido ni funciones. Referencias de revisión responsive: 1366 px, 768 px, 390 px y accesibilidad a 320 px; verificar teclado, objetivos táctiles y ausencia de desbordamiento horizontal.
- Diferenciar **inicial** (primera revisión/línea base), **anterior** (inmediatamente precedente) y **actual** (última revisión válida). Evitar diferencias de score engañosas cuando `framework_version` o `scoring_version` no sean compatibles.
- Separar vigencia del servicio de resultados del sitio. El servicio activo no significa diagnóstico positivo; las revisiones son manuales, no monitoreo continuo.
- No duplicar resultados ni instrucciones entre bloques; mensajes comprensibles, códigos PRV secundarios y evidencia observable. No usar «Cumple/No cumple» ni prometer corrección automática.
- Si una revisión falla, conservar el último resultado válido y comunicar el error sin modificar el score mostrado.

### Bloque 1 — Estado de mi sitio

Pregunta: **¿Cómo está mi sitio actualmente?**

- Mostrar como protagonista el **Privacy Score actual**, fecha y origen de la última revisión válida. Antes de la primera revisión posterior, el diagnóstico inicial también es el actual. Score inicial solo como dato secundario.
- Resumir las cinco áreas (Transparencia, Formularios, Cookies, Contacto, Seguridad) **por cantidades de estados de controles**, no mediante scores porcentuales por área; utilizar los estados reales del motor y no inventar equivalencias.
- Diagnóstico completo integrado en el Plan mediante detalle expandible por área y por control; no obligar a volver al diagnóstico gratuito.
- Cada control muestra **resultado**, **evidencia** y **alcance/limitaciones** cuando corresponda. Preferir «Detectado», «No detectado» y «No concluyente» solo cuando correspondan semánticamente al resultado real; nunca equipararlos automáticamente a cumplimiento normativo.
- Mantener acciones de corrección en el bloque 2 y el inicio de nuevas revisiones en el bloque 3.

#### C2a - Contrato de lectura de diagnóstico (backend)

La respuesta autenticada existente de `GET/POST /api/privacy/workspace-sites/{workspace_site_id}/plan` incorpora un objeto **aditivo** `diagnostic`, sin alterar `plan`, `check` ni el endpoint de revisión:

- `diagnostic.initial`: `score`, `created_at` (fecha **real del diagnóstico original**, no fecha de creación del Plan), `framework_version`, `scoring_version`.
- `diagnostic.current`: `score`, `created_at`, `source` (`initial` o `review`), `framework_version`, `scoring_version`, `scope` acotado y `controls` con `control_code`, `name`, `area`, `type`, `result`, `reason`, `confidence`, `evidence_summary` y `source_url`.
- Sin revisión posterior, **actual = inicial**. Con revisiones, el actual proviene del `diagnostic_snapshot` correspondiente al último `entitled_plan_check` válido del Plan, no de un escaneo nuevo.
- Los nombres/áreas provienen del catálogo actual, con la presentación «Seguridad» para el dominio «Seguridad visible». Los códigos antiguos desconocidos se conservan sin asignarles un área inventada. La interfaz deberá distinguir este caso.
- La evidencia se limita a textos/resúmenes ya evaluados y URL HTTP(S) pública sin credenciales, query ni fragmento. **No** se expone el arreglo crudo `evidence`, parámetros internos, HTML inspeccionado ni otros campos técnicos del snapshot. Una evidencia ausente se muestra como ausente; no se inventa una explicación.
- Se conserva la autorización de workspace/site/entitlement y el comportamiento de solo lectura tras vencimiento natural; la revocación sigue bloqueando lectura. Sin cambios de scoring, reglas, controles ni migraciones. Las diferencias de score siguen condicionadas a comparabilidad de versiones.

C2b utiliza este contrato para mostrar score actual y fecha, cinco áreas y controles expandibles. El score inicial y su fecha se muestran en **Mis avances** como referencia comparativa; el gráfico de evolución y el historial completo corresponden a C4.

#### C2b - Estado de mi sitio (frontend)

C2b consume **únicamente** el contrato autenticado `diagnostic.current` de C2a para presentar:

- Privacy Score actual y su fecha real de diagnóstico, con indicador discreto de primera o última revisión. El score inicial no aparece en esta pestaña: la comparación inicial/actual con ambas fechas pertenece a **Mis avances** (C4).
- Cinco áreas expandibles y controles anidados expandibles, con conteo textual por estados observados (sin inventar puntuaciones por área). Si un snapshot histórico contiene controles sin área reconocida, se presentan bajo «Otros controles de esta revisión».
- Resultado, explicación, resumen de evidencia pública y enlace de origen saneado cuando están disponibles. Si no existe resumen de evidencia o un resultado no es concluyente, se señala explícitamente; no se asume cumplimiento ni corrección. Se muestra el alcance limitado y el número de páginas cuando el diagnóstico los informa.
- Una revisión nueva exitosa refresca el diagnóstico actual mediante el GET autenticado del Plan. Si la lectura posterior falla, se oculta el estado potencialmente obsoleto y se invita a recargar, sin negar que la revisión fue guardada.
- Accesos legados sin `diagnostic` mantienen sus otras funciones con un mensaje explícito sobre la ausencia del detalle. No se ejecutan inspecciones adicionales por abrir el Plan.

Estilos con tokens globales Mininode, responsive, y tests de contrato visible, aislamiento lógico de pestañas y actualización posterior a revisión. Sin cambios de API, scoring, controles ni BD.

**Ajuste UX posterior a C2b:** conservar una sola tarjeta por área y presentar sus controles como filas con separadores sutiles, nombres de peso normal y detalle expandible. Los controles `not_applicable` continúan disponibles bajo «Mostrar N controles no aplicables» dentro de su área, sin perder explicación ni evidencia. Los conteos incluyen todos los controles. En **Mis avances**, la fecha original y la fecha actual se colocan discretamente debajo de sus respectivos scores; se retira la fecha duplicada del pie. En revisiones no comparables se muestra solo el score y la fecha actuales, sin atribuir una variación entre versiones. Sin cambios de scoring ni de contrato.

### Bloque 2 — Qué debo mejorar

Pregunta: **¿Qué debería corregir y cómo?**

- Mostrar los **hallazgos pendientes de la última revisión válida**, no el listado congelado del diagnóstico inicial. Los confirmados como corregidos dejan de figurar como pendientes y permanecen trazables en Mis avances.
- Orden automático por prioridad **alta → media → baja**, conservando orden estable del motor dentro de cada prioridad; inicialmente sin filtros ni ordenación manual.
- Detalle expandible de cada acción: **qué se encontró**, **cómo abordarlo**, **cómo comprobarlo**.
- **Sin checklist manual** por ahora: el usuario corrige en su sitio y una revisión posterior verifica las señales observables. Un estado no concluyente nunca equivale automáticamente a corregido.
- Si no existen mejoras pendientes detectadas, mostrar un mensaje positivo pero acotado al alcance observado; distinguir controles no concluyentes y aclarar que no es certificación legal.

#### C3a - Recomendaciones vigentes (backend)

`GET/POST /api/privacy/workspace-sites/{workspace_site_id}/plan` incorpora el campo **aditivo** `current_actions`. Los campos existentes `plan` (diagnóstico inicial inmutable), `diagnostic` y `check` se conservan:

- `current_actions.status`: `available` o `version_mismatch`; `source`: `initial` o `review`; `created_at`: fecha real del diagnóstico utilizado; `actions_version`: versión del catálogo con el que se generaron instrucciones (o `null` cuando no son seguras).
- `item_count` e `items`: solo acciones actuales y evaluables, en el orden determinista del motor, con el mismo contrato de acciones del Plan inicial. Si todavía no hay revisión, se reutilizan las acciones **guardadas** inicialmente sin regenerarlas.
- Tras una revisión, las acciones se recalculan en memoria sobre el diagnóstico persistido de la última revisión válida utilizando `build_correction_plan`, sin escanear de nuevo ni sobrescribir el `plan_snapshot`. Se incorporan hallazgos nuevos con acciones de catálogo y se retiran los detectados como corregidos.
- `verification_pending_count` y `verification_pending`: controles evaluables sin conclusión (`not_evaluable`) y controles con una acción en el Plan inicial **o en cualquier revisión anterior compatible** que posteriormente pasan a `not_applicable` o desaparecen, sin confirmación de corrección intermedia. Se reconstruyen los hallazgos no resueltos en orden cronológico desde los snapshots guardados de este mismo Plan: solo `detected` confirma su resolución; `not_evaluable`, `not_applicable` y ausencias no la confirman. Son **pendientes de verificación**, nunca acciones supuestamente corregidas ni instrucciones inventadas.
- El diagnóstico revisado debe identificar exactamente las versiones vigentes de framework/scoring. Si faltan o difieren, `status=version_mismatch`, conteos `null` e instrucciones vacías: **no** interpretar el vacío como «sin pendientes». La generación de acciones desde el diagnóstico vigente no requiere comparar el score histórico inicial con el actual. Una revisión antigua con versiones incompatibles no se reinterpreta con el catálogo vigente.
- La lectura sigue protegida por membresía, sitio no desvinculado y entitlement, incluidos los accesos de solo lectura tras vencimiento natural y el bloqueo por revocación.
- Sin cambios de BD, migraciones, motor de priorización, scoring, controles, catálogo de acciones o endpoints de revisión. C3b ya se implementó en DEV; «Qué debo mejorar» utiliza las acciones de la última revisión válida.

C3b consume **exclusivamente** `current_actions` para «Qué debo mejorar», muestra pendientes de verificación aparte y distingue `version_mismatch` de un diagnóstico sin hallazgos accionables. Después de cada revisión vuelve a leer el Plan autenticado.

#### C3b - Recomendaciones dinámicas (frontend)

«Qué debo mejorar» consume `current_actions` del Plan autenticado sin recrear hallazgos ni consultar el diagnóstico histórico por su cuenta:

- Usa solo `current_actions.items` para las tarjetas de acciones y mantiene el orden estable del backend, con prioridades Alta/Media/Baja y pasos expandibles. Se elimina la excepción local de nombre PRV-003, utilizando el nombre canónico del contrato.
- Muestra fecha/origen de la revisión que sustenta las recomendaciones. Los controles `verification_pending` aparecen separados de las acciones, con motivos «Resultado no concluyente», «No aplica en esta revisión» o «No evaluado en esta revisión», sin instrucciones inventadas, checklist ni cierre automático.
- Solo muestra «Sin mejoras pendientes en el alcance observado» si **ambos conteos valen cero**. Ese mensaje recuerda que no acredita cumplimiento legal. Si hay pendientes de verificación, no presenta una conclusión positiva.
- Si el estado es `version_mismatch`, el contrato está incompleto o tiene datos incoherentes, oculta acciones previas y explica que no puede mostrar recomendaciones vigentes, sin sustituirlas por el Plan inicial.
- Después de cada POST de revisión exitosa, invalida inmediatamente las acciones antiguas y utiliza el mismo GET autenticado existente para refrescar diagnóstico y recomendaciones. Un error de GET mantiene ocultas las recomendaciones obsoletas y solicita recargar. Sin solicitudes de escaneo adicionales.
- Solo para el recorrido legado por token, que no expone `current_actions`, conserva las instrucciones iniciales identificadas explícitamente como históricas y no actualizadas. No se considera origen válido para acciones vigentes de Access.

Se preservan las tres pestañas y el comportamiento de C2; C4 continúa a cargo del historial y evolución. Sin cambios de API, scoring, controles, persistencia ni motor de recomendaciones.

#### Validación C3 en DEV - 28-oct-2026

- En la revisión real de un sitio público sin cambios intencionales: Privacy Score inicial/actual **47/100 → 47/100**, **0** mejoras corregidas, **2** aún pendientes; «Estado de mi sitio» y «Qué debo mejorar» mostraron fecha actualizada y ambas acciones (PRV-001 y PRV-003). Esta prueba confirma el recorrido de revisión y la consistencia observable en ese escenario; **no demuestra** manualmente una corrección ni un hallazgo nuevo.
- Las pruebas automatizadas de C3a/C3b cubren cambios, pendientes no concluyentes, incompatibilidad de versiones y recuperación del Plan. No reemplazan una QA independiente con nuevos sitios cuando corresponda.
- Se encontró una diferencia de presentación en «Mis avances»: el backend de comparación emite `items[].control_id`, mientras el frontend leía `control_code` para el nombre UX. Corrección frontend en **PR #407** para usar `control_id` con compatibilidad `control_code`, sin modificar datos, scoring o contrato. Validación visual final y persistencia tras recarga todavía pendientes.
- Estado de C3: **integración real sin cambios PASS; cierre completo condicionado a validar el ajuste de «Mis avances» y persistencia tras recargar**.

#### Catálogo de presentación UX - 21 controles (independiente del motor)

Decisión de producto: conservar dos conceptos separados.

Cierre: unificación de 21 nombres y descripciones mediante **PR #405** y prioridades gratuitas mediante **PR #406**; ambos mergeados en DEV, CI verde y validación visual del nombre PRV-003 en todas las vistas comprobadas (28-oct-2026).

- **Catálogo técnico**: `backend/src/mininode_api/domain_packs/privacy/controls.json` (`v0.11`) continúa definiendo el identificador PRV, nombre de referencia técnico, dominio, aplicabilidad, criterios y evidencias. No se modifica scoring, resultados, reglas ni contratos de API.
- **Catálogo UX único**: `frontend/privacy/control-ux.js` contiene exactamente 21 códigos y para cada uno un nombre comprensible y una descripción breve. Es la única fuente para la **presentación** de controles conocidos en el diagnóstico gratuito, las tres pestañas del Plan (incluidas acciones, verificación y evolución) y la demo. Mantener códigos PRV visibles para trazabilidad.
- Las descripciones aparecen en los detalles del diagnóstico público y bajo el control expandido de «Estado de mi sitio»; se preservan hallazgos, evidencias y recomendaciones propias del diagnóstico. En «Qué debo mejorar» no se duplica la descripción donde ya existen hallazgo, corrección e instrucciones.
- Controles históricos desconocidos conservan el nombre recibido sin inventar descripciones ni asociaciones; el cambio de nombre UX no modifica snapshots persistidos ni resultados históricos. Se eliminan las excepciones locales de PRV-003.
- Los seis controles informativos (`PRV-004`, `PRV-009`, `PRV-101`, `PRV-103`, `PRV-104`, `PRV-201`) siguen sin peso en el score; ser «informativo» en Mininode no equivale a que la información sea legalmente opcional.
- **Limitaciones fuera de alcance**: PRV-004 detecta fecha **o** versión, no acredita comprobar ambas; PRV-009 observa un fundamento declarado, no verifica su suficiencia legal y no participa del score. Revisar la cobertura de ambos por separado; unificar nombres no cambia el alcance efectivo de estos controles.
- Versionar scripts compartidos y mantener tests de cobertura del catálogo UX contra los códigos del framework técnico, orden de carga y consistencia visual entre pantallas.

### Bloque 3 — Mis avances

Pregunta: **¿Estoy mejorando?**

- Gráfico de evolución del Privacy Score con valores inicial y actual; representar solo tramos comparables, nunca conectar resultados con versiones incompatibles como una serie continua.
- Historial **completo** de revisiones, más reciente primero, cada una expandible; se podrá incorporar paginación solo cuando el volumen lo justifique.
- Para la evolución general, comparar **actual frente a inicial** cuando corresponda; para cambios recientes, comparar con la revisión **inmediatamente anterior**.
- Desglosar cambios como **corregidos**, **pendientes**, **nuevos** y **no concluyentes**, sin considerar ausencias de evidencia o resultados indeterminados como correcciones.
- Ubicar aquí **Revisar nuevamente**, disponible durante la vigencia del Plan. No prometer seguimiento automático.

### Brechas técnicas conocidas y secuencia propuesta

El Plan actual prioriza score inicial y acciones originales; el endpoint autenticado devuelve solo `latest_check`, aunque las revisiones se almacenan en PostgreSQL. Antes de implementar el historial completo, detalle actual por control, prioridades dinámicas y estados por área, revisar contratos/snapshots existentes y definir los ajustes backend necesarios, evitando inferir datos inexistentes.

| Tramo | Alcance propuesto | Estado |
|---|---|---|
| C1 | Estructura visual, navegación y responsive | **Implementado en DEV; validaciones visuales realizadas** |
| C2a | Backend: contrato de lectura del diagnóstico vigente | **Mergeado en DEV (PR #400)** |
| C2b | Frontend: estado actual, cinco áreas y controles expandibles | **PASS visual en DEV (PRs #401 y #402)** |
| C3a | Backend: contrato de acciones vigentes y pendientes de verificación | **Mergeado en DEV, PR #403; Reviewer PASS y CI verde** |
| C3b | Frontend: recomendaciones dinámicas y actualización tras revisión | **Mergeado en DEV (PR #404); integración real sin cambios validada el 28-oct-2026; cierre visual y recarga pendientes** |
| C4 | Historial completo, gráfico, comparaciones y nueva revisión | **Diseño aprobado · pendiente de implementación** |

Implementar en PRs pequeños, enfocados y con tests por comportamiento. Revisar CI del último commit, validar en DEV y no mergear sin autorización. Considerar Reviewer independiente cuando se alteren contratos, autorización, BD o comparabilidad. No cambiar scoring, controles ni versiones por razones cosméticas.

**Roadmap público:** `frontend/roadmap/index.html` es un resumen editorial distinto; actualizarlo en un trabajo posterior separado, sin presentar estas capacidades UX pendientes como ya disponibles.

## 4. Etapa 1 - Preparación del producto (P1)

**Objetivo:** producto preparado para pruebas internas y piloto.

| ID | Actividad | Estado |
|---|---|---|
| PW-01 | Desasignar sitios de un workspace conservando historial y evidencia, con autorización correcta | **Cerrado · PROD** (PR #379) |
| PW-02 | Habilitar uso interno completo sin pago mediante entitlement explícito, auditable y separado de Billing | **Cerrado · PROD** (Mininode Admin; PR #379) |
| PW-03 | Consolidar Billing como recorrido único, retirar órdenes heredadas y desacoplar Plan de corrección y revisiones; preparación de activación con actualización automática | **En curso · DEV** (PW-03A validado; PW-03B integrado en DEV: planes y revisiones con entitlement y migración controlada; retirada legacy pendiente) |
| PW-04 | Conectar Mercado Pago con el recorrido de compra: checkout, retorno, webhook, confirmación, entitlement, expiración y reintentos | **Parcial · DEV** (adaptador y endpoints backend; E2E pendiente, no disponible en PROD) |
| PW-05 | Unificar tercera persona singular en UX, resultados, hallazgos, recomendaciones, botones, estados y errores | Pendiente |
| PW-06 | Incorporar observabilidad de diagnósticos, pagos, activaciones y fallos operativos, sin exponer datos sensibles | Pendiente |
| PW-07 | Definir y revisar acceso, privacidad y retención de datos de usuarios, diagnósticos, pagos y eventos | Pendiente |

**Avance confirmado:** PW-01 y PW-02 fueron implementados y validados en DEV, promovidos a PROD en PR #379 y aprobados visualmente tras el despliegue. No se afirma que se hayan ejecutado transacciones reales de concesión o revocación en PROD. PW-03A ya prepara la activación en DEV; PW-03B conecta planes/revisiones con entitlements, mientras la retirada final de rutas heredadas sigue pendiente; PW-04 permanece como integración parcial de backend en DEV, sin recorrido comercial E2E.

**Criterios de cierre restantes de la etapa:** recorrido comercial oficial único; pago confirmado por proveedor habilita prestaciones y pago no confirmado no las habilita; mensajes coherentes; fallos detectables; tratamiento de datos definido.

**Decisión comercial (PW-03 → PW-04):** `billing.orders` + `access.entitlements` serán el único recorrido comercial oficial. Mercado Pago es el proveedor inicial. El historial de órdenes y activaciones del sistema heredado **no necesita migrarse ni conservarse comercialmente**; se preservan diagnósticos, cuentas, sitios y entitlements actuales. PW-03 retirará dependencias del flujo anterior `privacy.correction_plan_order`, desacoplando Plan de corrección y revisiones. El diagnóstico guardado se conserva consultable; al iniciar activación se reutiliza si tiene menos de 24 horas o se actualiza automáticamente, sin exponer plazos al cliente. Preparar compatibilidad y rollback, verificar dependencias y probar primero en DEV. **Ninguna operación destructiva en producción sin autorización explícita.**

## 5. Etapa 2 - Piloto controlado (P1)

**Objetivo:** validar valor, comprensión y uso real antes de la apertura comercial general.

| ID | Actividad | Estado |
|---|---|---|
| PW-08 | Funnel interno de uso y conversión, visible solo para Mininode | Pendiente |
| PW-09 | Definir participantes, alcance, duración, modalidad de acceso y ejecutar piloto | Pendiente |
| PW-10 | Seguir uso, pagos, hallazgos, incidencias, feedback y revisiones posteriores | Pendiente |
| PW-11 | Evaluar resultados y decidir lanzamiento, correcciones u otra validación | Pendiente |

**Funnel mínimo:** diagnóstico iniciado → terminado → resultado consultado → activación solicitada → checkout iniciado → pago confirmado → entitlement activo → revisión posterior. Diferenciar abandono, rechazo de pago y error técnico. Minimizar los datos personales registrados.

Antes del piloto, fijar criterios de éxito, participantes, modalidad gratuita o pagada y canales de soporte. Las activaciones gratuitas controladas se harán con entitlements internos, nunca con pagos ficticios.

## 6. Etapa 3 - Comercialización (P2)

**Objetivo:** abrir y operar el servicio comercial de forma confiable.

| ID | Actividad | Estado |
|---|---|---|
| PW-12 | Validar recorrido completo: compra, activación, vigencia, expiración y reactivación | Pendiente |
| PW-13 | Definir e implementar personalización Partner: logo, colores y límites de identidad Mininode | Pendiente |
| PW-14 | Definir soporte, conciliación, reembolsos e incidencias de cobro/activación | Pendiente |
| PW-15 | QA de lanzamiento con versión/SHA congelado, criterios PASS previos y autorización de publicación | Pendiente |

**Modelo comercial vigente:** Privacy Web activo por **CLP $9.900**, durante **un mes calendario**, sin renovación automática, con revisiones manuales durante la vigencia.

La URL de retorno del proveedor no confirma el pago: la activación depende de la verificación confiable del proveedor y de Billing. Probar aprobación, rechazo, pendiente, duplicados, reintentos, expiración y conciliación. Validar en entornos correspondientes antes de abrir ventas.

## 7. Etapa 4 - Evolución del diagnóstico (P3)

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

## 8. Dependencias y secuencia

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

## 9. Estados y seguimiento

- **Pendiente:** actividad identificada sin implementación acreditada para su objetivo completo.
- **Parcial · DEV:** existe código o pruebas en `dev`, pero faltan componentes, integración E2E o validación; **no** implica publicación comercial.
- **En curso:** desarrollo o preparación activos.
- **Validación / validación de caso real pendiente:** implementación disponible, pero falta una comprobación específica para cerrar la actividad.
- **Cerrado · PROD:** funcionalidad publicada en `main` y PROD, con las validaciones aplicables aprobadas y evidencia trazable; el alcance de esas validaciones se declara.
- **Bloqueado:** falta una dependencia que impide avanzar.

Los estados se actualizarán con evidencia del repositorio, CI, QA, desplegado efectivo y validación del Product Owner; no por suposición. PW-01 y PW-02 se consideran cerrados por la promoción #379 y la aceptación visual de PROD; PW-21 conserva la validación de un caso real pendiente. No interpretar `Cerrado · PROD` como aprobación de pagos o de actividades distintas.

## 10. Fuera de alcance

Privacy Data; certificación legal; auditoría integral; modificación automática de sitios; renovación automática; controles de procesos internos no observables públicamente; ampliaciones no acordadas.

## 11. Flujo de implementación y alineación

- **Desarrollo / integración:** cambios enfocados en DEV, CI y validación funcional del Product Owner en **https://dev.mininode.io**, asegurando que el backend desplegado corresponda a la versión que se está validando. Los Branch Previews arbitrarios no sustituyen el entorno integrado de Access/Clerk.
- **Promoción selectiva:** partir de `main` actualizado, preparar un PR propio hacia `main` con **solo la funcionalidad aprobada** y dependencias necesarias. Conservar componentes exclusivos de MAIN (como Content Reader V1) y excluir trabajos experimentales de DEV. Revisar diff y CI, obtener autorización expresa de merge y confirmar despliegue y validación breve de PROD.
- **Alineación permanente:** MAIN y DEV comparten la **base funcional aprobada**, mientras DEV puede mantener avances en validación. Las diferencias intencionales de código, datos, credenciales e infraestructura se registran; **no** hacer merge masivo para igualar commits. Ver [`docs/dev-prod-release.md`](../dev-prod-release.md).
- **Gobierno del roadmap:** `main` representa el estado publicado en PROD; este cambio documental se revisa primero en `dev` por tratarse de la planificación de la etapa C. La actualización de la referencia oficial en `main` se hará mediante promoción documental selectiva y autorizada, preservando las diferencias explícitas DEV/PROD. `frontend/roadmap/index.html` es un resumen público general distinto: actualizarlo solo en un trabajo editorial/UX posterior aprobado.

**Próximo frente priorizado:** etapa C del Privacy Web Plan (C1–C4), seguida por los pendientes de PW-03 (consolidación comercial) y PW-04 (integración E2E Mercado Pago). No activar cobros ni modificar registros históricos por actualizar este roadmap. Nunca mergear sin autorización explícita.