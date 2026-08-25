# Mininode Privacy - Contexto de producto

Usar este documento para Issues cuyo alcance sea Mininode Privacy o Privacy Web Inspector.

## Alcance del producto

Mininode Privacy realiza un diagnóstico inicial de señales públicas de privacidad presentes en un sitio web.

El resultado es orientativo: no constituye una certificación legal, una auditoría completa ni un porcentaje oficial de cumplimiento.

## Foco técnico actual

- Backend: Python/FastAPI en Render.
- Frontend: HTML/CSS/JavaScript en Cloudflare Pages.
- El trabajo actual de Web Inspector pertenece a la implementación backend existente de Privacy y sus pruebas.
- Mantener el contrato de la API pública salvo que la Issue solicite explícitamente modificarlo.

## Persistencia de Planes de corrección

Los Planes de corrección se guardan como snapshots inmutables en
`privacy.correction_plan` (PostgreSQL). El snapshot JSONB conserva sin recalcular
el contrato generado, mientras `site_url`, las versiones y el puntaje inicial se
guardan también como metadatos del registro. Un mismo sitio puede tener varios
planes independientes.

El acceso es una capability: al crear un plan se entrega una sola vez un token
URL-safe generado con 32 bytes aleatorios (256 bits). PostgreSQL guarda únicamente
su hash SHA-256, nunca el token original. La recuperación pública requiere el token
pero no una sesión ni identidad, solo considera registros `active` y responde con
el mismo 404 neutro para tokens inexistentes o planes `revoked`. No existe endpoint
de listado ni de actualización del snapshot.

La tabla impone unicidad sobre el hash. Debido a la entropía de 256 bits no se
agrega un retry de colisión en esta etapa; una colisión excepcional falla el
`INSERT` sin debilitar ni revelar el token. La inicialización es idempotente e
independiente de Learn: si PostgreSQL no está disponible, los endpoints de Planes
responden 503 sin afectar Health ni el diagnóstico gratuito.

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
