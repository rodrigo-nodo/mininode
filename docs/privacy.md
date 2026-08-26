# Privacy Web y Privacy Data - Contexto de producto

Usar este documento para Issues cuyo alcance sea Privacy Web, Privacy Data o Privacy Web Inspector.

## Alcance del producto

Mininode ofrece actualmente dos productos relacionados con privacidad:

- **Privacy Web** - producto operativo actual. Revisa señales públicas visibles del sitio web.
- **Privacy Data** - próximamente. Ayuda a ordenar el manejo interno de datos personales.

Privacy Web realiza un diagnóstico inicial de señales públicas de privacidad presentes en un sitio web.

El resultado es orientativo: no constituye una certificación legal, una auditoría completa ni un porcentaje oficial de cumplimiento.

## Foco técnico actual

- Backend: Python/FastAPI en Render.
- Frontend: HTML/CSS/JavaScript en Cloudflare Pages.
- El trabajo actual de Web Inspector pertenece a la implementación backend existente de Privacy y sus pruebas.
- Mantener el contrato de la API pública salvo que la Issue solicite explícitamente modificarlo.

## Plan de corrección: frontera comercial

El Plan de corrección Privacy Web es un producto único de pago único por CLP
$49.900 (`PRIVACY_CORRECTION_PLAN`). La solicitud pública crea solamente una orden
`pending_payment` con el identificador del snapshot y un email normalizado. El precio, la
moneda, el producto y el estado son definidos por el backend. Crear una orden no
genera el Plan, su token o su entrega. Durante el Design Partner, la generación puede
autorizarse manualmente mediante un endpoint interno protegido: la activación usa el
`diagnostic_snapshot` asociado, no vuelve a inspeccionar el sitio, genera un único
`CorrectionPlan`, lo vincula a la orden y marca técnicamente la orden como `paid`.
En esta etapa `paid` significa autorización manual; representará un pago confirmado
cuando se integre posteriormente un proveedor de pagos. El enlace se entrega
manualmente y no se almacena el token en texto plano en la orden. El snapshot permite
solicitar el Plan durante las 24 horas posteriores
al diagnóstico y pueden existir varias órdenes para un mismo diagnóstico, sin
deduplicación en este MVP. El Plan incluye una única comprobación de mejoras
utilizable hasta 90 días después de `paid_at`, que durante el Design Partner es el
momento de activación manual. Esta capacidad vuelve a inspeccionar la URL persistida
en el diagnóstico original, crea un nuevo snapshot y compara solamente las mejoras
del Plan por código de control estable. Un advisory lock por Plan y una restricción
única evitan la doble ejecución. El diagnóstico gratuito no queda
limitado por la compra y puede volver a ejecutarse independientemente del Plan.
La ventana de 24 horas se valida al crear la orden, no al activarla posteriormente.
Las activaciones de una misma orden se serializan y la vinculación exige que siga
`pending_payment`, evitando generar dos planes por reintentos. La creación del Plan y
la actualización de la orden usan actualmente conexiones separadas; por ello, un
fallo de base de datos exactamente entre ambas operaciones podría dejar un Plan
huérfano sin exponer su token. Esta limitación se resolverá junto con una unidad de
trabajo transaccional, sin almacenar el secreto para facilitar reintentos.
La nueva inspección y su snapshot usan conexiones separadas de la inserción final de
`correction_plan_check`: un fallo posterior puede dejar ese snapshot huérfano, pero
la comprobación no se considera utilizada hasta guardar el resultado final.

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
