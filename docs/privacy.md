# Privacy Web y Privacy Data - Contexto de producto

Usar este documento para Issues cuyo alcance sea Privacy Web, Privacy Data o Privacy Web Inspector.

## Alcance del producto

Mininode ofrece actualmente dos productos relacionados con privacidad:

- **Privacy Web** - producto operativo actual. Revisa señales públicas visibles del sitio web.
- **Privacy Data** - próximamente. Ayuda a ordenar el manejo interno de datos personales.

Privacy Data es un producto de primer nivel, separado de Privacy Web y desacoplado
de Billing. Su backend mantiene el catálogo maestro versionado en el repositorio y
persiste sus mapas en el schema PostgreSQL `privacy_data`. Los mapas nuevos son
`draft`, expiran inicialmente a los siete días y se recuperan mediante un token de
capacidad cuyo hash, nunca el token en claro, es lo único que se persiste.
Cada mapa puede persistir actividades categóricas ordenadas en
`privacy_data.activities`; su creación, consulta, edición y eliminación siempre se
autorizan a través del token del mapa padre. Las respuestas se validan contra el
catálogo versionado, sin almacenar datos identificatorios de personas concretas.
Privacy Data construye primero un mapa de **Datos, Usos y Terceros**. Esta Fase 1
incluye personas, tipos de información, posible presencia de menores, finalidades,
origen, lugares y participación de terceros, con sugerencias contextuales y acceso al
catálogo completo bajo demanda. Al terminar entrega un primer resultado sin exigir
Accesos ni Conservación; esos campos existentes, junto con `data_channels`, se
conservan de forma compatible para la posterior Fase 2 y su enriquecimiento.
Las actividades nuevas pueden usar internamente `data_context=unconfirmed` hasta que la
persona confirme si maneja la información para su operación, para prestar un servicio
a un cliente o en ambos contextos. Ese estado no representa una respuesta confirmada.
La revisión inicial de Privacy Data se calcula al solicitarla, sin persistir el
resultado. Sus reglas determinísticas D01-D08 presentan únicamente señales objetivas
como aspectos que conviene revisar o tener presentes; no producen scoring ni una
conclusión de cumplimiento. Cada observación de `/review` incluye `topic` y `action`
como orientación simple asociada al hallazgo; no representan una obligación legal,
certificación, conclusión de cumplimiento ni evidencia de que la acción fue realizada.

Privacy Web realiza un diagnóstico inicial de señales públicas de privacidad presentes en un sitio web.

El resultado es orientativo: no constituye una certificación legal, una auditoría completa ni un porcentaje oficial de cumplimiento.

Cada diagnóstico conserva las versiones canónicas del framework y del scoring dentro
de su snapshot. `framework_version` debe cambiar cuando un cambio pueda alterar la
interpretación, el resultado observable o el conjunto de controles evaluados. Esto
incluye cambios en criterios, evaluator, extracción o adaptación de evidencia y lógica
de inspección cuando puedan alterar el resultado producido para un mismo sitio.
`scoring_version` debe cambiar cuando puedan alterarse pesos, factores, exclusiones,
rangos o la fórmula del score.
Estas versiones se mantienen en `controls.json` y `scoring.json`, respectivamente;
no se derivan del Git SHA. Solo se comparan diagnósticos con ambas versiones iguales.
La versión vigente del framework en DEV es `0.13`; el scoring continúa en `0.3`.
Framework `0.13` reconoce versiones de política declaradas en su encabezado HTML o expresamente identificadas en el contenido, canales de ejercicio de derechos con contexto específico de solicitudes o consultas de privacidad, y proveedores que declaran tratar datos aunque no usen «compartir» o «transferir». No acepta versiones de software incrustadas en el contenido, simples títulos de privacidad como evidencia de canal específico ni declaraciones negadas sobre uso o tratamiento por proveedores. Los controles conservan PRV-003 como fuente exclusiva; no cambian pesos, fórmula, rutas ni BD. Los diagnósticos `0.12/0.3` y `0.13/0.3` no son comparables.

Framework `0.12` prioriza enlaces explícitos de política legal frente a páginas
comerciales de Privacy Web, resuelve el documento seleccionado entre URLs
solicitadas/finales equivalentes y permite inspeccionar candidatos adicionales
cuando faltó el contenido de la política. Mantiene la inspección pública pasiva,
los límites del fetcher, robots y SSRF. El planificador prioriza el enlace
seleccionado por PRV-003 dentro del presupuesto disponible, y PRV-002 evalúa
accesibilidad y pertinencia **solo de ese documento**, nunca de una página
comercial alternativa. Ante una política bloqueada se conserva el resultado
prudente y no se atribuye la respuesta HTTP de un documento distinto.
La selección y la inspección comparan internamente la identidad completa de
la URL, incluidos parámetros de consulta funcionales (ej. `?view=a` frente a
`?view=z`); la identidad interna aplica la **misma normalización** de
selector y fetcher: elimina `utm_*` sin eliminar `view` u otros parámetros
funcionales. La referencia pública de evidencia permanece sanitizada, sin
query ni credenciales. La URL interna no se serializa en diagnósticos,
snapshots ni logs. Esto evita asociar la respuesta de otra variante de ruta.
Este ajuste puede alterar los resultados
observables de PRV-003 a PRV-014 para un mismo sitio; por eso `0.11/0.3` y
`0.12/0.3` no son comparables. No cambian los pesos ni la fórmula del Score.
Framework `0.11` redefine PRV-201 como observación técnica contextual de cookies
vistas mediante encabezados `Set-Cookie` en las respuestas HTTP inspeccionadas. La
ausencia de un banner o texto de cookies no produce por sí misma un resultado adverso;
PRV-201 tiene peso cero y queda fuera del Privacy Score, cobertura, prioridades y mejoras accionables de Privacy Web. `not_detected` significa únicamente que no se observaron cookies dentro
del alcance técnico inspeccionado, no que el sitio no utilice cookies. El scoring
`0.3` registra esta exclusión y los diagnósticos `0.10/0.2` y `0.11/0.3` no son
comparables.
Framework `0.10` mantiene PRV-104 como señal contextual e informativa con peso cero, fuera del Privacy Score, cobertura, prioridades y mejoras accionables de Privacy Web. El scoring `0.2` registra esta exclusión para preservar la comparabilidad de snapshots.
Framework `0.9` mantiene la captura estática de contexto asociado a formularios y el descubrimiento de páginas de acción de `0.8`, y hace que PRV-103 combine acciones explícitas con objetos o resultados acotados dentro del mismo formulario. El clasificador sigue siendo determinístico, sin LLM, y no ejecuta JavaScript del sitio.
En PRV-103, el contacto general (`Escríbenos`, `Enviar mensaje` o equivalentes) se clasifica como finalidad genérica; solo se considera concreta cuando el mismo formulario expresa un resultado o servicio específico observable.

## PW-03 - Preparación de activación (DEV; sin pagos)

El diagnóstico gratuito guardado permanece disponible para consultar su fotografía
original. La ventana técnica de 24 horas no es una fecha de caducidad del resultado:
solo decide si es necesario obtener evidencia más reciente antes de intentar
activar Privacy Web.

Cuando el usuario decide activar un resultado ya guardado, el endpoint autenticado
`POST /privacy/workspace-sites/{workspace_site_id}/prepare-activation` verifica
pertenencia al workspace y reutiliza el último snapshot si sigue reciente.
En caso contrario inspecciona nuevamente **la URL persistida y autorizada**, guarda
un snapshot nuevo y lo entrega para la continuación. No solicita otra acción al
usuario, no elimina el resultado anterior y no crea órdenes ni realiza cobros.
Si la inspección o la persistencia falla, no se ofrece un diagnóstico nuevo
como apto para compra: el resultado anterior sigue consultable y se puede reintentar.

La interfaz muestra «Estamos actualizando el diagnóstico de tu sitio antes de
continuar.» únicamente cuando anticipa una actualización. En esta primera parte
de PW-03, completar la preparación aún muestra que el pago en línea estará
disponible próximamente. La conexión con Billing y Mercado Pago es posterior.

La elegibilidad para iniciar checkout y el pago acreditado son conceptos separados:
PW-04 deberá anclar la compra a una orden iniciada oportunamente; un webhook
acreditado tardío nunca debe perder la prestación por la expiración posterior
del snapshot, ni confiar solo en la URL de retorno.

## PW-03B - Plan de corrección por entitlement (validado en DEV; no promovido a PROD)

El nuevo recorrido autenticado se basa **exclusivamente** en
`access.entitlements` (producto `privacy_web`). Es compatible con los
orígenes `payment` e `internal_grant` sin inventar órdenes de cobro.

- `privacy.entitled_plan`: un plan base por `entitlement_id`, asociado a
  `workspace_site_id` y un `original_diagnostic_id` inmutable.
- `privacy.entitled_plan_check`: revisiones repetibles de ese plan,
  con evidencias y resultados asociados a nuevos snapshots de
  `privacy.diagnostic`. No usan `privacy.correction_plan_order`.
- **Continuidad histórica entre períodos (PW-03C, correctivo posterior a C2):**
  un entitlement nuevo crea un Plan nuevo, pero «Mis avances» consulta todos
  los Planes y sus revisiones vinculados al **mismo `workspace_site_id`**.
  Un intervalo sin acceso no borra evidencias ni implica seguimiento automático.
  Si la nueva línea base reutiliza exactamente el diagnóstico de la última
  revisión anterior (`diagnostic.id`), aparece una sola vez; una línea base
  distinta se muestra como «Diagnóstico de reactivación». La evolución no
  conecta gráficamente períodos diferentes ni versiones incompatibles; las
  comparaciones entre observaciones quedan condicionadas a su comparabilidad.
  Cuando el GET se autoriza únicamente por la recuperación en lectura de
  un entitlement vencido naturalmente, el historial visible queda acotado
  hasta ese período: un entitlement anterior no autoriza datos de períodos
  posteriores revocados. Un entitlement **vigente** y autorizado mantiene
  acceso al historial acumulativo completo del sitio. Se conserva una línea
  base inmutable para cada Plan, y «Estado de mi sitio»,
  «Qué debo mejorar» y «Revisar nuevamente» permanecen limitados al período
  autorizado vigente. Sin derecho vigente no se habilitan nuevas revisiones;
  la lectura tras un vencimiento natural mantiene la regla preexistente.
  Nunca se mezclan historias de workspaces distintos aunque compartan dominio.
- `POST /privacy/workspace-sites/{id}/plan`: crea o retorna el plan de manera
  idempotente, tomando el último diagnóstico **ya guardado** al iniciar el
  período; no realiza una inspección nueva ni acepta URLs externas.
- `GET /privacy/workspace-sites/{id}/plan`: consulta el plan guardado,
  validando acceso vigente.
- `POST /privacy/workspace-sites/{id}/plan/check`: inspecciona la URL
  persistida, compara con la línea base y guarda revisión y snapshot
  **en la misma transacción**. El inspector sigue siendo público/pasivo.
- Las tres rutas exigen sesión Clerk/Access, pertenencia al workspace,
  relación de sitio no desvinculada y entitlement activo (fecha/estado).
  La autorización se comprueba contra BD en cada petición; una revocación
  bloquea el acceso. Al expirar naturalmente el período, el Plan y su última
  revisión siguen consultables **solo en lectura**, pero nuevas revisiones
  quedan bloqueadas. No se borra historial.
- La página `/privacy/plan/?workspace_site_id=...` usa sesión de usuario,
  no tokens de acceso por URL. Cuando un sitio tiene entitlement vigente,
  la tarjeta de Privacy Web muestra «Abrir Privacy Web» en vez del precio.

**Estrategia de BD:** migración aditiva controlada
`backend/migrations/20261026_privacy_entitled_plans.sql`,
registrada por SHA-256 en `backend/scripts/predeploy_migrations.py`.
Se ejecuta **solo** en el entorno explícitamente autorizado a través de
`MIGRATION_APPROVED_FILES`, antes de desplegar el backend. El inicio del
servicio verifica las tablas y columnas en modo lectura; si faltan, el nuevo
módulo no está disponible (sin DDL ni concesión implícita de acceso).
La migración no elimina datos ni tablas existentes; las tablas nuevas pueden
coexistir si se revierte el código. Probar primero en DEV y revisar aprobación
separada para cualquier ejecución sobre PROD.

**Vigencia durante revisión:** el servicio vuelve a comprobar el plazo
con `clock_timestamp()` después de la inspección externa y después de guardar
las evidencias dentro de la transacción. Si el plazo vence, revierte
el snapshot y su comparación, retornando acceso no vigente.

**Errores de entitlement:** la vista del diagnóstico guardado sigue visible
si falla la consulta de entitlement; muestra «Reintentar acceso» y nunca
interpreta un error HTTP, de red o de JSON como ausencia de derecho.
No se prepara pago/activación hasta que la verificación se complete.

Esta rama no habilita Mercado Pago ni cobros nuevos.

**PW-03C — retiro del modelo comercial legado en DEV (cerrado):** no se
mantiene compatibilidad funcional futura para órdenes o tokens antiguos.
En **C1** el Plan por entitlement adoptó una comparación determinista neutral
en `domain_packs/privacy/diagnostic_comparison.py` y la comparabilidad
canónica de `versioning.py`; en **C2** se retiraron endpoints, servicios,
formulario de orden, rutas por token, proxy e inicializaciones legadas.
**C3** confirmó las tres tablas legadas vacías en DEV y sus dependencias SQL
externas ausentes. Tras PR #414, Reviewer PASS, despliegue de `503f65d`
en Render DEV y autorización específica, el **29-oct-2026** se ejecutó
manualmente el retiro `DROP TABLE ... RESTRICT` exclusivamente en DEV.
La verificación posterior confirmó las tres tablas eliminadas,
`privacy.entitled_plan` = 3, `privacy.entitled_plan_check` = 3
y `privacy.diagnostic` = 67. El Product Owner confirmó que el Plan
en DEV se ve y funciona igual: **PW-03C3 PASS funcional**.

**Excepción de respaldo aceptada:** se eligió como referencia el respaldo
del 28-oct-2026, pero **su restauración no fue probada**; el riesgo fue
aceptado expresamente antes de ejecutar. Ver [registro de cierre PW-03C3](privacy-web/pw-03c3-legacy-dev-retirement.md).

**PROD permanece sin cambios:** conserva 2 Planes, 3 órdenes y 1 revisión
legadas, y `main` todavía ejecuta código heredado. La comprobación de
órdenes históricas en agrupación de sitios se mantiene condicionada a la
presencia de la tabla. No eliminar tablas en PROD ni promover la migración
DEV: requeriría decisión, migración, respaldo y autorización independientes.
Se preservan diagnósticos/snapshots, Access, Billing, entitlements,
planes y revisiones nuevos.
C1 no modifica BD, scoring, controles, API ni comportamiento público.
La UX C1–C4c está validada en DEV (C4c: PR #410); aún no está en PROD.

## Arquitectura de interpretación semántica

Privacy Web adopta como arquitectura objetivo el flujo:

**Página → evidencia textual → extractor semántico común → hechos estructurados → controles deterministas.**

La interpretación de lenguaje natural debe resolverse en una capa común y reutilizable.
Los controles no deben implementar clasificadores semánticos propios cuando el mismo
problema pueda resolverse mediante esta capa compartida.

El extractor semántico produce hechos estructurados acompañados de la evidencia textual
y su fuente. No determina directamente el resultado de un control. Los controles
consumen esos hechos y aplican reglas deterministas, trazables y versionables.

Mientras esta capa no esté disponible o suficientemente validada, los nuevos controles
que dependan de interpretación semántica deben quedar pendientes, contextuales o
limitados explícitamente. No se deben crear soluciones semánticas independientes por
control para cerrar temporalmente esa dependencia.

Esta restricción permite avanzar en paralelo con controles basados en evidencia pública
observable y determinista, dejando la interpretación semántica como una pieza
transversal que podrá reutilizarse en Transparencia, Formularios, Cookies y futuros
controles.

## Foco técnico actual

- Backend: Python/FastAPI en Render.
- Frontend: HTML/CSS/JavaScript en Cloudflare Pages.
- El trabajo actual de Web Inspector pertenece a la implementación backend existente de Privacy y sus pruebas.
- Mantener el contrato de la API pública salvo que la Issue solicite explícitamente modificarlo.

## Diseño de controles de formularios

La definición aprobada para la siguiente ampliación de la familia Formularios está en
[`privacy-forms-control-design.md`](privacy-forms-control-design.md). El diseño mantiene
PRV-101 y PRV-104 sin cambios, prioriza un control determinista de transporte del
formulario y posterga conclusiones sobre minimización, consentimiento, menores o datos
de riesgo elevado cuando la evidencia pública no permite evitar falsos positivos.

## Privacy Web: presentación de Score y cobertura en DEV — PW-QA-01

**Estado:** reglas de suficiencia integradas en DEV mediante PR #442 (CI y
Reviewer PASS). La presente revisión de jerarquía UX está acordada como
contrato de producto; requiere CI, validación visual del PO y merge autorizado
en su propio PR. No declarar todavía PASS funcional de esta revisión.
El frontend presenta los resultados del backend sin recalcular ni modificar
el Privacy Score `0.3`, sus pesos, `status`, controles, API o snapshots.
El catálogo `controls.json` framework `0.13` sigue siendo la fuente de
verdad para peso/aplicabilidad; `frontend/privacy/score-presentation.js`
contiene una proyección de sus pesos validada por test de consistencia en CI.
Los seis controles contextuales no afectan el Score.

**Clasificación de suficiencia** (solo presentación):
- `Wa` = suma de pesos puntuables aplicables (excluir `not_applicable`).
  `Wm` = suma de pesos de los aplicables `not_evaluable`.
- **Completa de controles aplicables:** `Wa > 0`, hay evaluables y
  `Wm = 0`. «Cobertura completa» **no** significa cumplimiento legal ni
  que todas las páginas del sitio se hayan inspeccionado.
- **Parcial:** hay evaluables, `Wm > 0`, `5 * Wm <= Wa`, y
  `PRV-001` y `PRV-003` no son `not_evaluable`. El Score se muestra
  como orientativo, junto con evaluados/aplicables.
- **Limitada:** si faltan todos los evaluables, no hay puntuables
  aplicables, `5 * Wm > Wa` o `PRV-001`/`PRV-003` no son
  evaluables. **No se destaca** el Score técnico aunque sea 100.
- `not_applicable` legítimo **no suma ni resta**; los problemas
  comprobados (`not_detected`) no deben convertirse en `not_evaluable`.

La incertidumbre matemática `[100 * Eo/Wa, 100 * (Eo+Wm)/Wa]`
solo se usa internamente como escenario extremo condicional, **no** como
confianza estadística. Si una evaluación parcial podría cruzar un
límite de texto visible (`40/70/85`), se informa que la interpretación
podría cambiar, sin forzar por eso «Limitada».

**Escala de presentación pública** (sin cambiar los rangos del backend):
0–39 «Preparación inicial»; 40–69 «Preparación en desarrollo»;
70–84 «Preparación avanzada»; 85–100 «Preparación destacada».
Con evidencia **completa**, cualquier control puntuable de impacto muy alto
con `not_detected` sustituye un mensaje de preparación potencialmente
positivo por «Hay aspectos importantes por corregir» y se identifica el
hallazgo. Con evidencia parcial, «Evaluación parcial» sigue siendo el
encabezado y los hallazgos confirmados se muestran por separado.
El resultado `partial` de impacto muy alto conserva su recomendación,
pero no activa la sustitución del encabezado.

Las revisiones con versiones incompatibles, detalle ausente o conteos
inconsistentes conservan su Score almacenado y muestran **«Cobertura no
verificable»** como estado principal, no «Diagnóstico anterior» (esa etiqueta
confundía antigüedad con verificabilidad). La puntuación aparece como
**«Puntuación registrada»**, de protagonismo visual secundario; en resultados
guardados se indica **«Referencia histórica»**. No se asigna nivel de
preparación y no se altera el registro. `scope.limited` se muestra como
advertencia del rastreo **independiente** de la suficiencia de controles.

### Matriz UX aprobada — preparación × evaluación (11-nov-2026)

**Dimensiones distintas:**

- **Nivel de preparación:** Inicial (0–39), En desarrollo (40–69),
  Avanzada (70–84), Destacada (85–100). Describe el rango de un Score
  calculado. Solo se muestra como conclusión visible con evidencia **Completa**
  y sin hallazgos de impacto muy alto `not_detected` que deban reemplazarla.
- **Estado de evaluación:** Completa, Parcial y Limitada son estados de
  suficiencia. **Cobertura no verificable** es una condición especial de
  compatibilidad/datos, **no** un quinto nivel de preparación ni un cuarto
  estado metodológico comparable.

| Estado de evaluación | 0–39 · Inicial | 40–69 · En desarrollo | 70–84 · Avanzada | 85–100 · Destacada |
| --- | --- | --- | --- | --- |
| **Completa** | Preparación inicial | Preparación en desarrollo | Preparación avanzada | Preparación destacada |
| **Parcial** | Evaluación parcial + Score orientativo | Evaluación parcial + Score orientativo | Evaluación parcial + Score orientativo | Evaluación parcial + Score orientativo |
| **Limitada** | Sin nivel ni Score destacado | Sin nivel ni Score destacado | Sin nivel ni Score destacado | Sin nivel ni Score destacado |
| **Cobertura no verificable** | Sin nivel; Score guardado secundario | Sin nivel; Score guardado secundario | Sin nivel; Score guardado secundario | Sin nivel; Score guardado secundario |

La columna representa el rango **numérico calculado o almacenado**, no
necesariamente un nivel de preparación que se deba comunicar. Son **16
combinaciones teóricas**, no 16 encabezados distintos.

**Prioridad visual y copy:**

- **Completa:** nivel aprobado como encabezado y Score destacado; comunicar
  controles puntuables aplicables evaluados. Un `not_detected` confirmado
  de impacto muy alto sustituye el encabezado por
  **«Hay aspectos importantes por corregir»** y muestra el hallazgo.
- **Parcial:** encabezado **«Evaluación parcial»**; Score visible marcado
  **«Orientativo»**, **sin** mostrar «Preparación destacada» u otro nivel
  como conclusión. Explicar cobertura y sensibilidad si corresponde.
- **Limitada:** encabezado **«Evaluación limitada»**; número técnico no
  destacado (se muestra «—» y «Sin nota»), manteniendo resultados útiles.
- **Cobertura no verificable:** encabezado del mismo nombre, sin nivel;
  puntuación original secundaria («Puntuación registrada» y, para una revisión
  guardada, «Referencia histórica»). No inventar cobertura ni recalcular.
- **Sin prioridades, Completa:** «No identificamos acciones prioritarias
  dentro del alcance de esta revisión.»
- **Sin prioridades, Parcial o Limitada con evaluables:** «No identificamos
  acciones prioritarias entre los puntos comprobados. Hay otros puntos que
  no pudimos verificar.»
- **Sin evaluables:** «No pudimos comprobar controles puntuables para
  identificar acciones prioritarias.»
- **Sin prioridades, Cobertura no verificable:** «Esta revisión no contiene
  acciones prioritarias identificadas. Su cobertura no puede verificarse
  con los datos disponibles.»
- La cabecera del listado se mantiene neutral **«Acciones prioritarias»**
  cuando está vacío: no se afirma que no hay problemas. El subtítulo de
  alcance dice **«Consideramos 21 puntos de privacidad en 5 áreas»**, porque
  considerar un punto no equivale a haberlo evaluado.
- Todas las pantallas mantienen la estructura diagnóstico → resultado →
  evidencia → acciones → detalle. En móvil la puntuación histórica no
  recupera protagonismo. Los hallazgos confirmados siguen visibles aun con
  evidencia Parcial o Limitada.

**Frontera del cambio UX:** no se modifica `scoring.json` 0.3, la
clasificación técnica `status`, contratos, controles, `priorities` ni
snapshots existentes. Las reglas de 20% y los límites 40/70/85 se mantienen;
la UX de cuatro niveles es una hipótesis de comunicación que se evaluará en
pilotos, no una escala de cumplimiento legal validada científicamente.

QA y gobierno: casos predefinidos PW-QA-01 / UX, comprobación de bordes y
consistencia frontend/backend en CI, y **QA independiente posterior con
SHA congelado y casos nuevos no usados para desarrollo**. Solo tras PASS
y validación del PO corresponde evaluar promoción selectiva. El
trabajo acotado a DEV no modifica MAIN, Plan autenticado, Billing,
persistencia, controles, pesos ni contratos.

## Privacy Web activo: frontera comercial

El diagnóstico Privacy Web es gratuito. En modo autenticado, un sitio ya guardado usa `workspace_site_id`: Access autoriza al miembro del workspace y el backend obtiene desde allí la URL a inspeccionar. Para una URL nueva, Privacy Web recibe el workspace autorizado, ejecuta primero el diagnóstico y, solo si éste resulta exitoso, crea o reutiliza automáticamente el `workspace_site` y vincula el snapshot. Los usuarios no crean sitios manualmente desde la cuenta. El endpoint público existente continúa disponible para diagnósticos anónimos. Privacy Web activo cuesta CLP $9.900 por un
mes, sin renovación automática por ahora. La vigencia se calcula como **un mes
calendario desde `paid_at`**, no como una cantidad fija de 30 días.

Mientras Privacy Web esté activo para un sitio, la persona puede iniciar nuevas
revisiones manuales del mismo sitio para comprobar sus cambios. Cada revisión vuelve a
inspeccionar exclusivamente la URL persistida en el diagnóstico original, crea un nuevo
snapshot y compara el resultado con el diagnóstico original cuando
`framework_version` y `scoring_version` siguen siendo comparables. Todas las
revisiones se conservan; la API expone la última revisión para la experiencia actual.
No existe un estado de "comprobación utilizada" ni una regla especial de vigencia por
monto histórico.

La solicitud pública crea solamente una orden `pending_payment` con el identificador
del snapshot y un email normalizado. El precio, la moneda, el producto y el estado son
definidos por el backend. El snapshot permite solicitar la activación durante las 24
horas posteriores al diagnóstico. Una vez vencida esa ventana, el snapshot y su
resultado permanecen disponibles; la interfaz deja de ofrecer la activación sobre esa
revisión y pide realizar una revisión reciente antes de continuar. Durante el Design
Partner, la activación puede autorizarse manualmente mediante un endpoint interno protegido: usa el
`diagnostic_snapshot` asociado, genera la estructura de mejoras, la vincula a la orden
y registra `paid_at`. En esta etapa `paid` significa autorización manual; representará
un pago confirmado cuando se integre posteriormente un proveedor de pagos.

El enlace de acceso se entrega manualmente y su token no se almacena en texto plano en
la orden. Las revisiones se serializan por activación mediante un advisory lock para
evitar ejecuciones concurrentes sobre el mismo sitio. El diagnóstico gratuito no queda
limitado por la compra y puede volver a ejecutarse independientemente de Privacy Web
activo.

Internamente se conservan temporalmente nombres técnicos anteriores como
`PRIVACY_CORRECTION_PLAN`, `correction_plan` y la ruta `/privacy/plan/`; son detalles
de implementación y no forman parte del lenguaje público del producto. Renombrarlos
queda fuera de este cambio para no mezclar un refactor estructural con el ajuste de
comportamiento.

La creación de la estructura de mejoras y la actualización de la orden usan actualmente
conexiones separadas; por ello, un fallo de base de datos exactamente entre ambas
operaciones podría dejar un registro huérfano sin exponer su token. La nueva inspección
y su snapshot también usan conexiones separadas de la inserción final de la revisión;
un fallo posterior puede dejar ese snapshot huérfano, pero la revisión no se considera
registrada hasta guardar el resultado final.

PRV-003 distingue de forma determinística una política propia del responsable de
referencias a políticas generales de terceros. Un dominio externo no implica por sí
solo que la política sea de un tercero: la atribución puede confirmarse mediante el
documento ya inspeccionado. Las políticas canónicas de proveedores conocidos se
consideran de tercero y el texto del enlace no puede sobreescribir esa señal.

PRV-004 detecta de forma determinística una fecha contextualizada de actualización,
publicación o vigencia, o un identificador de versión, únicamente en la política
seleccionada por PRV-003. Cuando el extractor excluye el encabezado, usa solo
metadatos explícitos dentro de un elemento `header` del documento principal,
con un título propio de política. Ignora versiones de plataforma aunque aparezcan
próximas a la palabra «privacidad» o en el texto documental; en el contenido,
una referencia de versión debe aparecer como declaración propia o asociada
directamente al nombre de la política, no a otro producto.
El metadato no se incluye en el contrato de evidencia publicado; es un control
contextual de peso cero, sin solicitudes adicionales ni efecto directo sobre
el Privacy Score.

PRV-005 evalúa la identificación observable del responsable únicamente en el
documento seleccionado por PRV-003 y reutiliza su contenido ya inspeccionado, sin
realizar solicitudes adicionales ni usar referencias de políticas de terceros.

PRV-006 evalúa el canal para ejercer derechos únicamente en el documento
seleccionado por PRV-003. Requiere asociación explícita entre el canal y el
ejercicio de derechos en el mismo segmento o la frase inmediatamente
anterior del texto documental limpio, siempre que esa frase mencione
concretamente el ejercicio o la solicitud de derechos (incluida la
formulación «ejercer los derechos»). En el mismo segmento también se exige
referencia contextual específica a derechos,
solicitudes o consultas de privacidad: el mero título «Política de privacidad»
no asocia un correo general con ese canal. No se recorre una ventana
retrospectiva que pueda unir secciones diferentes. No usa cabeceras, pies de
página ni contactos generales de otras páginas, y sigue separado de PRV-301.
Cuando Cloudflare Email Address Obfuscation sustituye un correo por HTML
codificado (`data-cfemail` o `/cdn-cgi/l/email-protection#...`), el extractor
conserva **solo una señal estructurada, interna, de presencia de correo**
vinculada a su bloque HTML y sección. No introduce identificadores artificiales
en el texto extraído: el contenido de una página no puede suplantar esa señal.
No decodifica ni almacena la dirección protegida ni ejecuta JavaScript.
Los enlaces `mailto:` válidos, los enlaces Cloudflare y los canales en
celdas de tabla o elementos independientes se conservan como evidencia
estructurada del bloque correspondiente, incluso sin párrafo envolvente.
PRV-006 mantiene asociación local y explícita con el ejercicio de derechos
dentro de una misma sección. Los encabezados de secciones hermanas no se
concatenan como una frase única, y un contacto general o comercial no hereda
contexto de derechos de un encabezado anterior. Instrucciones verbales
como «escriba» o «contáctenos» no constituyen un canal observable sin un
medio concreto. Para contratos de evidencia
legados sin bloques estructurados se conserva la evaluación textual tradicional,
sin aceptar marcadores de origen no verificable. La estructura interna queda
excluida de la serialización pública del Evidence Contract.
Este comportamiento se cubre con pruebas offline positivas y negativas
(incluidos ambos hallazgos del Reviewer) y con la política HTML de Mininode
en su forma original y transformada.

PRV-007 evalúa las categorías o tipos de datos tratados únicamente en el
documento seleccionado por PRV-003, reutilizando su contenido ya inspeccionado.

PRV-008 evalúa las finalidades del tratamiento únicamente en el documento
seleccionado por PRV-003, reutilizando su contenido ya inspeccionado.

PRV-009 detecta de forma determinística y conservadora las bases o fundamentos
que la política seleccionada por PRV-003 declara en contexto de tratamiento de
datos. Es una señal contextual con peso cero: no evalúa la corrección jurídica ni
la aplicabilidad de la base declarada, no amplía el crawling y no modifica el
Privacy Score ni las prioridades sustantivas.

PRV-010 evalúa menciones observables de destinatarios o categorías de terceros
únicamente en el documento seleccionado por PRV-003. Separa oraciones y
cláusulas contrastivas («pero», «sin embargo», «but», etc.) y también cláusulas
aditivas («y», «and») cuando comienza una declaración independiente:
un predicado explícito («y utilizamos proveedores») o un nuevo sujeto seguido
de tratamiento de datos («y nuestros proveedores de autenticación procesan
datos»), incluyendo «y además/también nuestros proveedores…» con y sin
acentos, si existe un predicado independiente antes de la conjunción.
No divide enumeraciones nominales como «proveedores de pago y hosting»,
«publicidad y marketing» ni sujetos coordinados sin predicado previo.
Así, «no usamos proveedores publicitarios y utilizamos proveedores de
autenticación que procesan datos» contiene dos declaraciones independientes,
mientras «operamos sin proveedores que procesan datos» no es evidencia positiva. La negación de uso o tratamiento
debe vincularse a la expresión relativa a proveedores dentro de su cláusula.
Admite categorías explícitas en hasta dos frases anteriores a una declaración
afirmativa de tratamiento, sin aprobar simples menciones comerciales.
Conserva «no compartimos datos con terceros» como declaración explícita de
ausencia de destinatarios (`explicit_none`), distinta de negar únicamente
el uso de cierta clase de proveedores. No amplía la inspección ni evalúa
jurídicamente la comunicación. La matriz T01–T09 y las pruebas de invariantes
protegen la separación entre cláusulas, junto con el HTML real de Mininode.

PRV-011 evalúa los derechos del titular únicamente en el documento seleccionado
por PRV-003, reutilizando su contenido ya inspeccionado.

PRV-012 evalúa de forma observacional los plazos, eventos o criterios de
conservación únicamente en el documento seleccionado por PRV-003. Usa señales
textuales determinísticas y contextuales sobre datos, conservación y duración,
sin ampliar la inspección ni valorar si el criterio es jurídicamente adecuado.

## Seguridad - invariantes

- Las protecciones SSRF son obligatorias.
- Nunca permitir destinos privados, loopback, link-local, reservados, mezclas público/privado u otros destinos prohibidos solo para aumentar cobertura.
- Validar redirects antes de seguirlos.
- Los redirects solo pueden permanecer en el hostname inicial o su variante apex/`www`; otros dominios se rechazan aunque resuelvan a IP públicas.
- Cada request usa un perfil HTTP compatible con navegadores sin cookies, autenticación, `Referer` ni estado de sesión.
- Cuando DNS entrega varias IP públicas ya validadas, se intentan de forma determinista con IPv4 antes de IPv6; un fallo de conexión puede continuar con otra dirección dentro de límites por intento y del presupuesto total.
- Preferir un fallback seguro o un error preciso antes que debilitar SSRF.
- Mantener privada la telemetría técnica/diagnóstica; no exponer detalles internos de red en la respuesta pública de Privacy.

## Reglas de implementación

- Partir por los archivos nombrados o implícitos en la Issue; no inventariar todo el repositorio por defecto.
- Ampliar la búsqueda solo cuando imports, flujo de llamadas, pruebas o errores lo requieran.
- Reutilizar las abstracciones existentes de Web Inspector/fetcher en vez de crear un stack paralelo.
- Mantener cambios mínimos y reversibles.
- Agregar o actualizar pruebas focalizadas de regresión para cada comportamiento modificado.
- No modificar `.github/workflows/*` salvo que la Issue solicite explícitamente cambios de workflow.
- No modificar frontend, base de datos, autenticación, pagos o infraestructura no relacionados.

## Línea base actual de investigación del Web Inspector

La muestra validada de sitios educacionales dejó estos casos distintos:

- `insucap.cl`: el redirect llega a `insucapchile.cl` y queda bloqueado durante la validación SSRF. Investigar la causa exacta; no relajar SSRF globalmente.
- `cyfcapacitacion.cl`: llega al servidor después del redirect a `www` y recibe HTTP 500. Tratarlo como fallo del servidor/sitio de origen salvo nueva evidencia.
- `colegioelalbademacul.com`: responde HTTP 403 rápidamente. Es candidato a compatibilidad HTTP conservadora mediante headers/fallback tipo navegador, manteniendo seguridad.
- `colegiosochides.cl`: la conexión termina en `ConnectTimeout` cerca del timeout configurado. Diagnosticar o aplicar fallback conservador; no ocultarlo simplemente con un timeout sin límite.

Sitios conocidos como correctos en la misma muestra:

- `delucchicapacita.cl`
- `academiaelcentro.cl`
- `colegio-forjadores.cl`
- `charlesdarwin.cl`

Al modificar el fetcher, preservar el comportamiento exitoso de estos casos mediante pruebas automatizadas focalizadas cuando sea razonable. Los sitios externos en vivo no deben convertirse en dependencia obligatoria de los unit tests.

## Definición de terminado para cambios del fetcher Privacy

1. Implementación mínima y segura para la Issue.
2. Invariantes SSRF preservadas.
3. Pruebas focalizadas aprobadas.
4. Pruebas existentes relevantes aprobadas.
5. Sin archivos no relacionados modificados.
6. El resumen final indica archivos cambiados, pruebas ejecutadas y cualquier caso pendiente.

PRV-013 evalúa únicamente en la política seleccionada por PRV-003 si se informa
la posibilidad de reclamar o recurrir ante una autoridad de protección de datos.
Se mantiene separado de PRV-011: este último describe los derechos del titular,
mientras PRV-013 observa la vía de reclamación ante la autoridad.

PRV-014 evalúa el retiro o revocación del consentimiento únicamente cuando la
política seleccionada por PRV-003 declara claramente un tratamiento basado en
consentimiento. Las menciones aisladas, formularios y señales de cookies no activan
su aplicabilidad; cuando esa base no se declara, el control es `not_applicable` y no
participa en el puntaje.

Los controles documentales PRV-004 a PRV-014 prefieren una muestra interna y
efímera de contenido principal de hasta 12.000 caracteres. El extractor selecciona
un `main` único sustantivo, después un `article` sustantivo y, por último, una copia
limpia del cuerpo; en esa copia excluye `script`, `style`, `template`, `header`,
`nav`, `footer`, `aside` y `form`. La muestra histórica `visible_text` conserva su
límite y semántica, continúa siendo la evidencia usada por PRV-003 y actúa como
fallback para construcciones anteriores. La muestra principal no se serializa en el
Evidence Contract ni forma parte de respuestas o snapshots.

## Cuenta y última revisión

Cuando un diagnóstico autenticado queda vinculado a un `workspace_site`, su snapshot persistido puede reutilizarse como la última revisión visible en la cuenta Mininode.

La cuenta muestra únicamente el snapshot más reciente por sitio: score, estado y fecha. **Ver resultado** abre ese snapshot ya almacenado; no ejecuta una nueva inspección. Una nueva revisión solo ocurre cuando el usuario inicia explícitamente otro diagnóstico.

Esto no habilita historial completo ni modifica entitlement, vigencia o Billing.

## Guardar un diagnóstico anónimo en una cuenta gratuita
Al terminar el diagnóstico anónimo, Privacy Web muestra las mismas tres
prioridades gratuitas y ofrece **Guardar mi diagnóstico**, sin obligar al
visitante a registrarse o contratar. El navegador conserva temporalmente
`diagnostic_id` y `claim_token` en `sessionStorage`, sin incluir la prueba
en la URL. Tras autenticarse con Access/Clerk, el sistema guarda automáticamente
en el único workspace disponible; si hay varios, el usuario elige el destino
y el guardado comienza sin una segunda confirmación. Si no tiene workspace,
Access crea uno mediante el onboarding existente. El frontend llama a
`POST /privacy/diagnostic-claims` con solo `diagnostic_id`, `claim_token`
y `workspace_id` (la intención `save`/`activate` permanece exclusivamente
en el navegador). Tras un guardado gratuito exitoso, elimina el pendiente, permanece en **Mi espacio**, actualiza **Mis sitios** y muestra «Diagnóstico guardado correctamente» con enlace al resultado. Si falla la actualización de la lista, la confirmación y el enlace siguen disponibles; no se informa un falso error de guardado. Cuando el usuario eligió **Activar Privacy Web**, se conserva el recorrido de activación tras guardar el snapshot.

Cada diagnóstico queda asociado a un solo workspace; varios workspaces pueden
mantener revisiones independientes del mismo hostname. Guardar no habilita
funcionalidades de pago ni amplía el contenido gratuito. El token pendiente
no se persiste entre sesiones de navegador; si falla el guardado, puede
reintentarse en la misma pestaña. **Guardar gratis no vence a las 24 horas**:
la asociación está permitida mientras el snapshot y la prueba de un solo uso
sean válidos y el usuario esté autorizado en el workspace elegido. En cambio,
`purchase_expires_at` sigue limitando a 24 horas la elegibilidad de la
**activación comercial** y no cambia el plazo de un mes del producto activado.
No se incorpora una migración ni un nuevo plazo de guardado.
La UX de resultado reúne ambas opciones bajo **Continúa con Privacy Web**: una tarjeta compacta de activación (acción principal), una fila de guardado gratis con botón del mismo tamaño, y apoyo técnico terciario. Las prestaciones y condiciones quedan plegadas en **Ver qué incluye y condiciones**; se informa que el pago en línea aún no está disponible. Si no hay oferta de pago, guardar gratis sigue disponible cuando existe token de asociación. El guardado no cambia las tres prioridades gratuitas.
La elección de continuación del diagnóstico ofrece **Activar Privacy Web** y **Guardar diagnóstico gratis** con acciones equivalentes. Ambas pasan por Access y guardan el snapshot en el workspace elegido; la intención (`save`/`activate`) se mantiene junto con el token temporal solo en `sessionStorage`. La solicitud comercial autenticada y la reactivación de una revisión guardada son trabajo posterior: mientras tanto, la interfaz informa que aún no están disponibles y no afirma que se haya comprado ni activado el producto.

En Access, si hay un diagnóstico pendiente, el guardado continúa automáticamente al autenticar cuando la cuenta posee un solo workspace. Con varios workspaces, primero se elige explícitamente el destino y entonces se guarda, sin un segundo botón de confirmación. El token temporal solo se elimina después de un guardado exitoso; un error muestra reintento. La nota sobre ausencia de renovación automática y pago en línea pendiente aparece bajo las condiciones desplegables de Privacy Web.

Al mostrar un resultado, Privacy Web diferencia entre un diagnóstico **anónimo asociable** (contiene `claim_token`: ofrece activar o guardar gratis vía Access) y un diagnóstico **ya guardado en un workspace** (contiene `diagnostic_id` y `workspace_site_id`, o se abrió desde un sitio autenticado: confirma «Diagnóstico guardado» y no ofrece volver a guardarlo). La opción **Activar Privacy Web** se conserva en ambos recorridos cuando el diagnóstico puede activar; desde un resultado guardado abre el aviso del siguiente paso comercial pendiente, sin afirmar que hubo compra ni activar prestaciones. El flujo completo de solicitud autenticada sigue siendo trabajo posterior.

La opción gratuita y la confirmación «Diagnóstico guardado» utilizan una fila responsive equivalente. En el estado guardado, la acción «Mis sitios» es un botón de navegación a la lista de sitios en Access (no vuelve a guardar el diagnóstico).
