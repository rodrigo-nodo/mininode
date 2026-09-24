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
Framework `0.10` mantiene PRV-104 como señal contextual e informativa con peso cero, fuera del Privacy Score, cobertura, prioridades y Plan de corrección. El scoring `0.2` registra esta exclusión para preservar la comparabilidad de snapshots.
Framework `0.9` mantiene la captura estática de contexto asociado a formularios y el descubrimiento de páginas de acción de `0.8`, y hace que PRV-103 combine acciones explícitas con objetos o resultados acotados dentro del mismo formulario. El clasificador sigue siendo determinístico, sin LLM, y no ejecuta JavaScript del sitio.
En PRV-103, el contacto general (`Escríbenos`, `Enviar mensaje` o equivalentes) se clasifica como finalidad genérica; solo se considera concreta cuando el mismo formulario expresa un resultado o servicio específico observable.

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

El diagnóstico Privacy Web es gratuito. Privacy Web activo cuesta CLP $9.900 por un
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
horas posteriores al diagnóstico. Durante el Design Partner, la activación puede
autorizarse manualmente mediante un endpoint interno protegido: usa el
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