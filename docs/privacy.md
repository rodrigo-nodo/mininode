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
La versión vigente del framework es `0.11`; el scoring vigente es `0.3`.
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

## Privacy Score — suficiencia y representatividad de la evidencia

**Decisión de producto (04-11-2026, refinada el 10-11-2026; pendiente de implementación y QA):**
el Score calculado por el backend y la **suficiencia de evidencia para destacarlo en
la interfaz** son asuntos diferentes. Se mantiene íntegro el scoring `0.3`:
fórmula, pesos, resultados, contratos y snapshots existentes. Privacy Score es
orientativo respecto de señales públicas observables; **no** representa un
porcentaje de cumplimiento legal ni una auditoría integral.

### Resultados y principio de aplicabilidad

Los 21 controles actuales incluyen controles puntuables y contextuales
(informativos, sin peso). Para los puntuables:

| Resultado técnico | Significado | Tratamiento actual del Score |
| --- | --- | --- |
| `detected`, `partial`, `not_detected` | Se pudo evaluar y el resultado es positivo, intermedio o adverso | Se incluye con el factor y peso vigente |
| `not_applicable` | El control no corresponde según su condición de aplicabilidad/dependencia | **No suma ni resta; se excluye del denominador** |
| `not_evaluable` | No se pudo determinar el resultado por falta de evidencia o limitación técnica | No se penaliza directamente ni se considera aprobado; reduce la cobertura y puede limitar la presentación |

**No aplica legítimamente no es un incumplimiento ni una ventaja.** Por
ejemplo, si no se identifican formularios que soliciten datos personales
(`PRV-101=not_detected`, control contextual), el envío seguro de esos
formularios (`PRV-102`) queda `not_applicable`: no hay motivo para obligar al
sitio a incorporar un formulario. Si falta una política propia y se constata
`PRV-003=not_detected`, ese control sí expresa un hallazgo adverso; los
controles de contenido dependientes que resulten `not_applicable` no deben
descontar puntos repetidamente por la misma ausencia. **La aplicabilidad debe
estar justificada por el contrato y la evidencia; ausencia de evidencia no
equivale automáticamente a no aplicabilidad.**

La cobertura actual por cantidad es
`evaluated_controls / applicable_controls`, excluidos los controles
contextuales y `not_applicable`. La nota actual se calcula sobre los
puntuables *evaluados*, con los pesos y factores existentes. Por tanto,
`100/100` puede coexistir con muy poca evidencia. `4/4` o `14/14`
significa **100% de los controles puntuables aplicables evaluados**, no que
se revisaron todos los controles posibles, todas las páginas ni todas las
obligaciones legales. Cuando no hay controles puntuables aplicables o
evaluables, no interpretar el `coverage=100` técnico ni un `score=0`
como evidencia de cumplimiento o incumplimiento.

### Tres dimensiones distintas de calidad

1. **Suficiencia:** cuántos controles puntuables aplicables se evaluaron,
   su importancia/peso y las causas verificables de `not_evaluable`.
2. **Sensibilidad de interpretación:** cuánto podrían variar la nota y la
   etiqueta humana si se conocieran los controles pendientes.
3. **Representatividad del rastreo:** qué páginas, categorías y señales
   públicas fueron efectivamente inspeccionadas y cuáles son las
   limitaciones conocidas. `scope.limited=false` o haber examinado tres
   páginas no acredita cobertura exhaustiva del sitio. Sin un universo
   verificable, no inventar un porcentaje de URLs cubiertas.

No usar un porcentaje fijo de controles como único criterio. Diferenciar
una ausencia constatada (`not_detected`) de un dato no observado
(`not_evaluable`); no castigar este último como si fuera un fallo del sitio.

### Tres estados de presentación propuestos

| Estado visual | Condición conceptual | Presentación |
| --- | --- | --- |
| **Evaluación limitada** | Evidencia puntuable insuficiente por cantidad, peso o causas de faltantes; regla cuantitativa aún por validar | No destacar la nota; mostrar hallazgos comprobados, cobertura y explicación, sin implicar que el sitio está mal |
| **Evaluación parcial** | Evidencia suficiente para una nota orientativa, pero existen controles puntuables aplicables sin evaluar | Mostrar el Score contextualizado, cobertura y advertencias; distinguir lo confirmado de lo pendiente |
| **Evaluación completa de aplicables** | Todos los controles puntuables aplicables evaluados y al menos uno aplicable | Score destacado y leyenda «Cobertura completa de los controles aplicables» con el conteo real; no afirmar «sitio completamente evaluado» |

La etiqueta «Bien» depende hoy de los rangos visibles existentes. Si una
evaluación **parcial** tiene una interpretación sensible a controles
pendientes, **no** convertirla automáticamente en «Limitada» solo porque
el rango teórico pueda cruzar un límite de etiqueta. Evaluar una
advertencia de «interpretación sensible a evidencia pendiente» y evitar
una etiqueta categórica injustificadamente positiva. Su texto y
comportamiento siguen pendientes de decisión y tests de UX.

Se conservan los cuatro **ejemplos ilustrativos de diseño** del
04-11-2026: `6/15, Score calculado 100` → **limitada, sin nota
destacada**; `12/15, Score 86` → presentación **parcial
ilustrativa**, su clasificación definitiva depende del peso y causa de
los faltantes; `15/15, Score 86` y `15/15, Score 100` →
**completa respecto de aplicables**. En este último caso comunicar
«Bien», nunca «Perfecto» ni «Cumplimiento legal 100%».

### Cobertura ponderada y sensibilidad: herramientas de calibración

Como análisis interno **candidato**, con aplicabilidad y pesos fijos:

- `W_a`: suma de pesos de controles puntuables aplicables;
  `W_o`: suma de pesos de los evaluados;
  `W_m = W_a - W_o`: suma de pesos de `not_evaluable`.
- `E_o`: puntos ponderados obtenidos en los evaluados
  (`detected=1`, `partial=0.5`, `not_detected=0`).
- Cobertura ponderada: `W_o / W_a`.
- Límite inferior hipotético: `S_min = 100 × E_o / W_a`.
  Límite superior: `S_max = 100 × (E_o + W_m) / W_a`.
- Amplitud sin redondear: `Δ = 100 × W_m / W_a` puntos de Score.

Solo calcular estas expresiones cuando `W_a > 0`. La banda
`[S_min, S_max]` representa **escenarios extremos condicionales**,
no un intervalo estadístico de confianza, probabilidad o predicción.
No considera cambios de aplicabilidad por dependencias, errores de
extracción, correlación entre controles ni páginas nunca descubiertas.
No mostrarla al cliente como «precisión» ni usarla para recalcular o
reescribir el Score histórico.

**20 puntos de amplitud es una hipótesis no aprobada**, a comparar con
15 y 25; el cruce de una categoría verbal (`40`/`70` en la UX)
no es por sí solo condición suficiente para «Limitada». Esos rangos son
decisiones de presentación, no límites científicos de confianza.

### Evidencia exploratoria y límites del análisis

Consultas `SELECT` a snapshots históricos de PROD, sin ejecutar nuevos
diagnósticos ni modificar datos: 37 revisiones framework `0.11` /
scoring `0.3` de 25 sitios. Diez revisiones (ocho sitios) tenían
`100/100` con cobertura de apenas 27%–40% e importantes controles
`not_evaluable`; las otras 27 tenían cobertura 100% de aplicables.
Entre estas últimas, 21 registraron `PRV-003=not_detected` y
solo cuatro o cinco controles aplicables: es cobertura completa de
**su denominador**, no ausencia de brechas. Se probaron además
**ocho simulaciones lógicas** sobre resultados existentes, sin alterar
los registros originales.

**Esto no es QA independiente ni calibración estadística:** hay
revisiones repetidas por sitio, faltan observaciones reales con
cobertura intermedia y los históricos de PROD `0.11` pueden reflejar
limitaciones del extractor corregidas después en DEV, incluida PRV-006.
No usar su distribución para escoger umbrales ni extrapolar incidencia
actual. Antes de implementar, definir criterios esperados *antes* del
QA, probar escenarios intermedios independientes, dependencias, casos
`not_applicable`, snapshots sin metadatos y cambios de versión,
y validar comprensibilidad de la interfaz.

Si versiones, pesos, controles, aplicabilidad, alcance o cobertura
cambian entre revisiones, indicar esa diferencia al comparar resultados
históricos: una variación de Score no equivale por sí sola a una mejora
o deterioro del sitio. Las ampliaciones de rastreo requieren respetar
la inspección pública pasiva y sus autorizaciones.

### Referencias metodológicas (analogías; no reglas adoptadas)

- [OECD/JRC — Handbook on Constructing Composite Indicators](https://www.oecd.org/en/publications/handbook-on-constructing-composite-indicators-methodology-and-user-guide_9789264043466-en.html):
  datos faltantes, pesos, robustez y análisis de sensibilidad.
- [Environmental Performance Index 2026 — Methodology](https://epi.yale.edu/2026/methodology):
  considera importancia, causas y posible sesgo de indicadores faltantes,
  además de advertir cambios de comparabilidad entre versiones.
- [Google Lighthouse — puntuación de accesibilidad](https://developer.chrome.com/docs/lighthouse/accessibility/scoring):
  delimita qué cubre una nota calculada con auditorías automáticas.
- [W3C — Website Accessibility Conformance Evaluation Methodology](https://www.w3.org/WAI/test-evaluate/conformance/wcag-em/):
  alcance definido y selección representativa de páginas.

Estas referencias **no** prescriben ni validan los tres estados de
Privacy Web ni sus umbrales: la regla es una propuesta propia.

**Pendiente de aprobación antes de implementar:** criterios operativos
para «Limitada»/«Parcial», tratamiento exacto de etiquetas sensibles,
excepciones por fallos de rastreo y validación con casos intermedios
independientes. Solo después realizar un PR enfocado en DEV, tests de
presentación y QA; cualquier promoción a MAIN/PROD exige autorización.
Este cambio es **únicamente documental**: no modifica frontend,
backend, scoring `0.3`, API, BD, snapshots, versiones ni
entitlements.

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

La activación comercial anterior por orden, correo y enlace de token fue retirada en PW-03 PR 4. El Plan autenticado se accede desde `/privacy/mi-plan/` usando membresía y entitlement por `workspace_site_id`. El historial de diagnósticos previos vinculados permanece separado del historial de revisiones del Plan. Los pagos no están habilitados: la integración comercial pertenece a PW-04. Las tres tablas históricas `privacy.correction_plan`, `privacy.correction_plan_order` y `privacy.correction_plan_check` fueron eliminadas de PostgreSQL PROD el 03-11-2026 tras autorización destructiva expresa y verificación independiente (PR #430). No repetir operaciones sobre estas tablas. La preparación de activación y la ventana de 24 horas para un diagnóstico reciente siguen siendo parte del futuro recorrido Billing; no crean órdenes ni habilitan pagos por sí solas.


PRV-003 distingue de forma determinística una política propia del responsable de
referencias a políticas generales de terceros. Un dominio externo no implica por sí
solo que la política sea de un tercero: la atribución puede confirmarse mediante el
documento ya inspeccionado. Las políticas canónicas de proveedores conocidos se
consideran de tercero y el texto del enlace no puede sobreescribir esa señal.

PRV-004 detecta de forma determinística una fecha contextualizada de actualización,
publicación o vigencia, o un identificador de versión, únicamente en la política
seleccionada por PRV-003. Es un control contextual con peso cero: reutiliza contenido
ya inspeccionado, no amplía el crawling y no modifica el Privacy Score.

PRV-005 evalúa la identificación observable del responsable únicamente en el
documento seleccionado por PRV-003 y reutiliza su contenido ya inspeccionado, sin
realizar solicitudes adicionales ni usar referencias de políticas de terceros.

PRV-006 evalúa el canal para ejercer derechos únicamente en el documento
seleccionado por PRV-003. Reutiliza contenido ya inspeccionado y mantiene este
canal separado del contacto general visible evaluado por PRV-301.

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
únicamente en el documento seleccionado por PRV-003. Usa señales textuales
determinísticas en contexto de comunicación de datos, incluidas declaraciones
explícitas de que no se comparten datos con terceros, sin ampliar la inspección ni
evaluar jurídicamente esa comunicación.

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


### PW-03 — Backend de Plan por entitlement (promoción selectiva)

El contrato nuevo (en PR 2 hasta su merge) conserva el diagnóstico original por entitlement en `privacy.entitled_plan` y guarda revisiones sucesivas en `privacy.entitled_plan_check` sin depender de órdenes antiguas ni tokens de Plan. Reutiliza `access.workspace_sites`, `access.entitlements` y `privacy.diagnostic`, así como las versiones canónicas existentes del framework/scoring; este PR no cambia controles ni scoring y no requiere nueva versión de esos catálogos.

- `POST /privacy/workspace-sites/{id}/plan`: prepara Plan una vez por entitlement activo usando el último diagnóstico guardado del mismo sitio; no reinspecciona.
- `GET /privacy/workspace-sites/{id}/plan`: lee Plan e historial autorizado, incluyendo períodos anteriores del mismo `workspace_site`; un período expirado naturalmente admite recuperación de solo lectura, nunca uno revocado.
- `POST /privacy/workspace-sites/{id}/plan/check`: inspección pública pasiva, nueva evidencia y comparación atómica. Una revocación, expiración, desvinculación o membresía ajena debe denegar acceso; al fallar se revierte la transacción.
- `POST /privacy/workspace-sites/{id}/prepare-activation`: reutiliza diagnóstico reciente o inspecciona de nuevo un sitio propio cuando venció su ventana de compra; no crea orden, entitlement ni pago.
- `GET /billing/workspaces/{id}/entitlements`: lista identificadores de sitios con derecho vigente para usuarios miembros.

**Aislamiento O1:** las lecturas del Plan verifican que el entitlement y el diagnóstico de origen pertenezcan al mismo `workspace_site_id`; la creación y las revisiones derivan los identificadores del sitio autorizado y almacenado. Tests negativos cubren referencias cruzadas, junto con aislamiento entre workspaces y revocaciones. Las FK individuales por sí solas no garantizan esta igualdad.

La promoción conserva temporalmente los endpoints y tablas comerciales antiguos hasta los PR 4/5 para no romper la UI pública actual. El proxy Cloudflare y el frontend renovado corresponden al PR 3. No se habilitan Mercado Pago, checkout ni webhooks. El backend exige el esquema migrado y lo inspecciona al iniciar **sin DDL**.

### Frontend Privacy Web PW-03 — acceso al Plan renovado

La interfaz privada del Plan se presenta temporalmente en `/privacy/mi-plan/?workspace_site_id=<uuid>`, con pestañas **Estado de mi sitio**, **Qué debo mejorar** y **Mis avances**. Consulta exclusivamente las rutas autenticadas `/privacy/workspace-sites/{id}/plan` (GET/POST) y `/plan/check` (POST), con JWT de Clerk obtenido mediante la API compartida de Mininode. El backend mantiene la decisión final de autorización por workspace y entitlement.

`/access/` muestra el enlace al Plan solo tras recibir `active_site_ids` desde `/billing/workspaces/{id}/entitlements`. Un error de consulta no debe tratarse como derecho inactivo. Las revisiones usan los snapshots ya almacenados y la comparación versionada del backend; no almacenan el JWT, snapshots ni resultados sensibles en el navegador.

**Transición:** esta nueva página no reemplaza `/privacy/plan/:token` ni sus servicios o proxy hasta la retirada comercial de PR 4; por ello usa una ruta distinta. No cambia el diagnóstico público, Content Reader V1, Mercado Pago, controles ni scoring.

### Privacy Web — diagnósticos anteriores vinculados (lectura)

`GET /privacy/workspace-sites/{id}/diagnostics/previous` devuelve **solo metadatos** (fecha, score y versiones), mediante Clerk/Access y la misma autorización de Plan por `workspace_site_id` y entitlement vigente o naturalmente expirado. Requiere un Plan ya existente; una revocación o desvinculación impide la consulta. El resultado, como máximo 100 filas con indicador de truncamiento, incluye exclusivamente diagnósticos vinculados directamente a ese `workspace_site_id` **anteriores a la primera línea base del Plan**; excluye todas las líneas base y revisiones vinculadas al Plan, y no une URL/hostname, ni reclama diagnósticos anónimos. La sección UI es desplegable y consulta los datos solo al abrirla; una falla de consulta no bloquea «Mis avances».

Los diagnósticos anteriores son antecedentes, **no revisiones del Plan**: no participan del gráfico, comparaciones ni conteos de corrección. Si el Plan aún no tiene revisiones, la tarjeta indica **«Sin revisiones»** en lugar de repetir el score inicial bajo «Última revisión». No modifica tablas, entitlements, scoring ni registros históricos.
