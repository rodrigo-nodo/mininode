# Privacy Web - Identidad de sitio lógico (Etapa A)

## Decisión de producto
- `access.sites.id` conserva la identidad del sitio lógico, con el hostname original como dirección principal.
- `access.site_aliases` incorpora hostnames alternativos **verificados** que resuelven a ese mismo `site_id`.
- Un workspace conserva una sola relación `workspace_site` por sitio lógico; Billing y entitlements mantienen sus claves actuales.
- El score vigente proviene de la última revisión válida; cada diagnóstico conserva su propio score histórico y URL inspeccionada.
- Dos workspaces que siguen un mismo sitio no comparten derechos comerciales.

## Primera entrega: fundación aditiva
La migración `20261019_access_site_aliases.sql` agrega sólo la tabla de aliases, sin borrar datos ni modificar tablas existentes. `services/site_aliases.py` ofrece consulta **read-only** del sitio principal o un alias verificado. Una colisión entre identidades primarias y aliases de sitios distintos falla explícitamente.

No se crean aliases automáticamente, no se hacen solicitudes HTTP, no se modifica `follow_site`, ni se agrupan historiales o fichas todavía. No cambia el motor de diagnóstico, scoring, controles, Billing, entitlements ni pagos.

## Reglas aprobadas para la fase siguiente
- HTTP/HTTPS del mismo hostname: equivalencia de dirección; no son dos hostnames.
- Dominio raíz y `www`: agrupar automáticamente sólo con redirección estable verificada.
- Dos dominios distintos con redirección pública HTTPS efectivamente comprobada durante el diagnóstico: reutilizar automáticamente la identidad de la HOME final; casos sin evidencia, independientes por defecto o pendientes de revisión solicitada.
- Contenido parecido sin redirección: mantener separados.
- Subdominios de aplicaciones o tiendas: independientes por defecto.
- Una declaración del usuario no basta para ampliar prestaciones pagadas.
- Las direcciones se normalizan y se validan con la política pública existente; ningún alias habilita redirecciones SSRF inseguras.

## Despliegue
La migración queda catalogada con checksum revisado, pero **no se ejecuta** mientras Render no incluya explícitamente el nombre en `MIGRATION_APPROVED_FILES`. Revisar dependencias y estado DEV antes de permitir la DDL. No activar en PROD sin autorización.

Siguiente PR: verificación/registro seguro de equivalencias, integración en `follow_site`, diagnósticos e interfaz, con tests de colisión entre hostnames principales y aliases. Evitar unir datos o conceder derechos entre workspaces.

## Etapa A.2 - Asociación de aliases existentes
`follow_site` y el guardado de diagnósticos anónimos consultan el mismo resolver **en su propia transacción**. Si el hostname coincide con un alias ya verificado, ambos reutilizan el `site_id` y, dentro del workspace, el `workspace_site_id` existente. De esta manera la ficha, último score e historial se consolidan sin modificar sus tablas o cálculos.

Hasta que la migración esté aprobada/aplicada en cada entorno, el resolver usa sólo `access.sites` y mantiene el comportamiento anterior. Ninguna escritura registra nuevos aliases. Sigue pendiente detectar redirecciones públicas de manera SSRF-safe, registrar evidencias y solicitar confirmación cuando corresponda; esa fase no debe inferir equivalencias de contenido similar.

## Etapa A.3 - Evidencia de redirección apex/www
`services/site_equivalence.py` inspecciona pasivamente las dos direcciones HTTPS y requiere que ambas terminen en el mismo hostname, con una redirección real y respuestas válidas. Reutiliza el cliente de transporte con IP fijada, validación de DNS/destino, límite de redirecciones y tiempos del inspector. No infiere equivalencia por contenido parecido, no soporta agrupación implícita de subdominios de aplicaciones y rechaza evidencias incompletas.

Este paso detecta evidencia; todavía **no registra aliases, no fusiona sites preexistentes y no cambia la asociación del usuario**. La unión automática debe quedar protegida por restricciones contra colisiones con hostnames principales y entre workspaces; una declaración de usuario tampoco otorga prestaciones.

## Etapa A.4 - Registro conservador de alias verificado
Al asociar una URL en un workspace autorizado o guardar un diagnóstico anónimo con prueba de titularidad del diagnóstico, si el hostname no está registrado y existe su par raíz/www en `access.sites`, el backend verifica en tiempo real la redirección usando el inspector público protegido. Con evidencia positiva, inserta solo el hostname libre como alias del site existente. La escritura es transaccional, utiliza bloqueo advisory por par de hostnames y `ON CONFLICT DO NOTHING`.

No fusiona fichas ya existentes ni mueve aliases asignados; si ambos hostnames ya tienen `site_id` distintos se conservan independientes para revisión posterior. Sin contraparte previamente registrada o sin evidencia no hace consultas de equivalencia ni fuerza la agrupación. El mismo workspace reutiliza su `workspace_site_id` y sus diagnósticos conservan URL y snapshot individuales. No se extiende una contratación a hostnames ajenos al sitio lógico verificado. No se alteran Billing, scoring o controles.

## Etapa A.5 - Desvincular sitio en un workspace
Se añade `access.workspace_sites.detached_at` mediante migración aditiva. Desvincular marca **esa asociación** como inactiva en una transacción autorizada y la omite del contexto, acceso al sitio y últimos diagnósticos del workspace. No elimina snapshots, `access.sites`, aliases, ni derechos de otros workspaces.

El backend bloquea desvincular si hay entitlements vigentes o compras pendientes. Compras pagadas cuyo período ya expiró no bloquean la operación. Billing impide crear nuevas órdenes sobre sitios desvinculados (serializado por bloqueo de fila); los errores 404/409 se comunican en frontend. Asociar de nuevo el mismo sitio, incluso desde un nuevo guardado gratuito, restaura la relación existente y su historial, no crea una nueva identidad.

**Condición de despliegue:** DEV tiene autodeploy al merge; NO mergear este PR mientras la allowlist y el despliegue coordinado no estén listos. Deshabilitar temporalmente autodeploy antes de merge, luego lanzar un único despliegue controlado con el commit fusionado y la migración allowlisted en Pre-deploy, comprobando sus logs y el funcionamiento. El bootstrap crea la columna solo en instalaciones nuevas; para BD existente se exige migración previa. No habilitar en PROD sin revisión y autorización de migración propia.

**Límite del experimento gurbana:** desvincular `www.gurbana.cl` y diagnosticarlo nuevamente puede restaurar el mismo sitio global preexistente. Desvincular no fusiona identidades existentes; esa conciliación requiere una tarea separada.

## Corrección DEV - Transporte de desvinculación

La acción web «Desvincular» utiliza `POST /access/workspaces/{workspace_id}/sites/{workspace_site_id}/unlink`, autenticada y restringida en el proxy Cloudflare, como alternativa al DELETE original conservado para compatibilidad. Ambas rutas invocan exactamente el mismo servicio transaccional y responden 204 al éxito. El frontend diferencia problemas al obtener token, fallos de conexión y fallos de refresco posteriores al éxito: si la desvinculación tuvo éxito pero el contexto no se actualizó, no se informa como operación fallida. Este cambio no requiere migración adicional ni modifica scoring o Billing.

## Etapa A.6 - Conciliación controlada de dos identidades preexistentes

Se añade un servicio interno y un script de operador, **sin endpoint público ni ejecución automática**. Por defecto solo presenta el plan: `python scripts/reconcile_existing_www.py --workspace-id UUID --primary ejemplo.cl --alias www.ejemplo.cl`. El modo `--apply` requiere una confirmación literal `--confirm UUID:ejemplo.cl:www.ejemplo.cl`; el script rechaza bases distintas de DEV o `mininode_test`. **Ningún dato real de DEV se reconcilia por instalar el código ni por ejecutar la migración aditiva.**

Condiciones obligatorias (fail closed):
- Dos filas principales existentes, `raíz` y `www` normalizados, redirección HTTPS estable comprobada mediante el inspector pasivo con protección SSRF.
- Exactamente un `workspace_site` por identidad, ambos exclusivos del mismo workspace; principal activo y secundario ya desvinculado; sin `company_id`.
- Ninguna compra u entitlement en cualquiera de los dos sitios, **incluso histórico**; ninguna relación de alias dependiente de la identidad secundaria ni hostname alias ocupado.
- Sin relaciones foráneas desconocidas contra `access.sites` **ni `access.workspace_sites`**; se comprueban tablas y columnas de las dependencias conocidas. Se rechazan nuevas referencias, incluso `ON DELETE CASCADE` o `ON DELETE SET NULL`, antes de cualquier eliminación. Bloqueo transaccional por par raíz/www compartido con la asociación de sitios para impedir carreras.

Tras **aprobación operativa específica** y una segunda verificación en la misma transacción, se reasignan únicamente los diagnósticos del `workspace_site` secundario al principal (sin modificar URL inspeccionada, score, contenido ni fecha), se retira la asociación e identidad global secundarias ya vacías, se registra `www` como alias verificado del principal y se registra el ID/hostname original, destino, workspace, IDs de asociación, **copias JSONB completas de las dos filas originales** (incluyendo `canonical_url`, `created_at`, `updated_at`, `detached_at`), cantidad de revisiones y método de evidencia en `access.site_reconciliations`, antes de eliminar dichas filas.

Se eliminan dos filas **estructurales** obsoletas (`workspace_sites` secundario y `sites` secundario) solo luego de trasladar las referencias admitidas. Sus identificadores y metadatos originales completos quedan preservados en el registro de conciliación; los snapshots de diagnósticos, fechas, scores y evidencias permanecen intactos. Cualquier excepción provoca rollback completo. El resolver sigue la identidad principal, y la consulta de última revisión ya existente obtiene el score más reciente.

La migración `20261020_access_site_reconciliations.sql` solo crea la tabla de trazabilidad y está catalogada con checksum. Debe ejecutarse **de forma coordinada** en DEV, no en PROD. Auto-Deploy DEV continúa desactivado. La futura aplicación concreta para `gurbana.cl` requiere primero dry-run comprobable en DEV y autorización adicional; no modificar datos reales ni habilitar despliegue PROD en esta etapa.

## Etapa A.7 - Trazabilidad de URL solicitada (Privacy Web)

Cada diagnóstico nuevo conserva de forma independiente en `privacy.diagnostic`:

- `requested_url` (**columna nullable nueva**): origen normalizado de la URL entregada para inspección (`scheme://host[:port]/`). Permite distinguir `www` de la raíz. Se excluyen usuario/contraseña, ruta, query y fragmento para evitar registrar tokens o datos sensibles.
- `site_url` (**sin cambios**): URL HOME final inspeccionada después de redirecciones. Determina la identidad de sitio en el guardado anónimo; la asociación por URL dentro del workspace se unifica con este criterio en la etapa A.8.

`requested_url` se registra en los diagnósticos anónimos, por URL dentro del workspace y sobre una ficha previamente guardada (en este caso corresponde a la URL almacenada desde la que se inicia la inspección). Los diagnósticos anteriores quedan con `requested_url = NULL`, sin reconstrucción inferida. El contenido `diagnostic_snapshot`, score, control de compra, API pública de resultados y algoritmo de agrupación/alias permanecen iguales.

La migración `20261020_privacy_requested_url.sql` es aditiva e idempotente; se incorpora al catálogo de checksums del Pre-deploy, pero requiere autorización explícita en `MIGRATION_APPROVED_FILES` **solo en Render DEV** antes de ejecutar el nuevo backend. No autoriza despliegue en PROD, merge automático ni nuevas conciliaciones.

## Etapa A.8 - Consistencia de identidad por URL final (DEV)

Los dos flujos que crean una relación de sitio tras un diagnóstico exitoso usan el mismo criterio de identidad: el `site_url` (HOME final inspeccionada). Antes, `/privacy/workspaces/{workspace_id}/diagnose` utilizaba `body.url` al llamar a `access.follow_site`, mientras el guardado anónimo (`claim_anonymous_diagnostic`) ya utilizaba `site_url`. El diagnóstico por ficha existente (`/privacy/workspace-sites/{id}/diagnose`) conserva su asociación explícita: no puede trasladar la ficha a otra identidad por redirección.

`requested_url` sigue guardando el origen ingresado por el usuario, sin ruta, query, fragmento ni credenciales, y `site_url` sigue siendo la URL efectivamente inspeccionada. No se modifican historiales, diagnósticos previos, scoring, snapshots, controles, Billing ni entitlements. No se fusionan dos identidades `access.sites` preexistentes: el resolver de alias continúa rechazando colisiones y exigiendo redirección verificada.

El inspector solo permite redirecciones dentro de un mismo hostname o su variante raíz/`www`. Las redirecciones entre dominios diferentes (`.cl` → `.com`) quedan **fuera de esta etapa**, para una decisión e implementación separadas. No hay cambios de esquema ni migraciones en esta etapa.

## Etapa A.9 - Redirecciones entre dominios y revisión de fichas existentes (DEV)

Al diagnosticar una URL, el inspector mantiene el límite normal de navegación dentro del mismo hostname/raíz-`www`. Únicamente si una redirección desde la HOME es bloqueada por salir de ese límite, se efectúan **dos comprobaciones adicionales independientes** mediante GET público. Ambas deben llegar a la misma HOME final HTTPS/200; no se acepta ningún salto HTTP intermedio, ni cambio del destino durante la inspección ordinaria posterior. Se mantienen IP fijada, revalidación DNS/SSRF en cada salto, máximo de redirecciones y tiempo total compartido. La verificación representa dos observaciones de esa ejecución, **no garantiza que el dominio mantendrá su redirección en el futuro**. Antes de obtener evidencia positiva, una redirección a IP privada, respuesta inválida o error técnico conserva el rechazo existente. El contenido de la comprobación no se emplea para puntuar: Privacy Web vuelve a inspeccionar normalmente la HOME de destino, incluido `robots.txt`. No se siguen dominios cruzados desde páginas descubiertas, formularios, enlaces ni recursos adicionales.

Si la HOME final validada difiere del origen, las nuevas revisiones se asocian por `site_url` como en A.8; `requested_url` conserva el origen original normalizado. Este mecanismo **no inserta aliases permanentes de dominios diferentes ni fusiona identidades antiguas**. La asociación directa por `/access/workspaces/{id}/sites` sigue usando sus reglas actuales.

Si existen dos fichas separadas, el usuario puede seleccionar exactamente dos y solicitar revisión. Se crea una solicitud idempotente con estado `pending` en `access.site_group_review_requests`, vinculada a su workspace y usuario autorizado. PostgreSQL protege que **ambas fichas pertenezcan al mismo workspace** mediante claves foráneas compuestas. Cuando cualquiera de las fichas es desvinculada, un trigger transaccional pasa las solicitudes pendientes a `invalidated` y registra cuándo ocurrió. Revincular la ficha no restaura automáticamente la solicitud: solo un nuevo envío explícito del usuario puede pasarla nuevamente a `pending`. No se borra la auditoría de las solicitudes anteriores ni se modifican entitlements. La interfaz muestra «Agrupación pendiente de validación» pero las fichas, sus historiales, `site_id`, `workspace_site_id`, órdenes y entitlements **permanecen separados**. La cola se consulta únicamente mediante rutas autenticadas y filtradas por workspace, nunca por el frontend público sin sesión. No existe endpoint de aprobación/fusión ni concesión comercial automática; solo un operador podrá resolver las solicitudes tras la futura etapa de reglas comerciales.

**Despliegue:** migración aditiva `20261020_access_site_group_review_requests.sql`, con checksum catalogado, que requiere autorización explícita en `MIGRATION_APPROVED_FILES` para DEV y pre-deploy coordinado. No ejecutar la DDL en PROD ni activar auto-deploy automáticamente. La ausencia de la tabla produce una respuesta 503 controlada al solicitar revisión, sin interferir con los diagnósticos existentes. Al cambiar la interfaz, confirmar también el Cloudflare Branch Preview asociado al último commit.

**Fuera de alcance:** conciliación de fichas existentes, permisos entre workspaces, pagos compartidos, entitlements por agrupación y decisión administrativa final; se tratarán en el PR 3, sin inferir que una solicitud pendiente es una aprobación.

## Etapa A.10 - Operación de revisiones de agrupación (PR 3A, pendiente de despliegue)

La solicitud `pending` puede avisarse al correo comercial de Mininode usando Resend, sin secretos en el repositorio. El backend envía después de guardar la solicitud; si falla o no está configurado el envío, la solicitud se mantiene y puede reintentarse al reenviar. El panel es `/operator/site-reviews/`, visible solo con sesión: el backend impone una lista de correos de operador verificados por Clerk/Access (`MININODE_REVIEW_OPERATOR_EMAILS`); la página estática y el enlace de correo **no conceden permisos**.

Un operador puede **rechazar** con motivo, o **aprobar** si la redirección HTTPS pública desde una HOME al hostname destino queda confirmada en dos GET independientes, con la protección IP fijada/SSRF del inspector y destino estable. Aprobación y reconciliación ocurren en una sola transacción PostgreSQL. Si falta evidencia, si interviene otro workspace, empresa, alias conflictivo, reconciliación previa, orden o entitlement (incluso histórico), **se devuelve 409, queda pendiente y no cambia ningún dato**. También se bloquean órdenes previas del Plan de corrección vinculadas a los diagnósticos. Una solicitud no se aprueba por la mera declaración de un usuario.

Para preservar las claves foráneas de la cola de solicitudes, el origen se conserva como **identidad retirada** (`retired-UUID.invalid`) y su `workspace_site` se desvincula, sin eliminarlos; se registran copias JSONB completas del sitio y vínculo originales en `access.site_group_operator_merges` junto a prueba y número de diagnósticos trasladados. El hostname público original se registra como alias verificado del destino. Todos los snapshots pasan al vínculo privado destino, conservando sus URLs originales, scores y fechas; la cuenta queda con una sola ficha activa. La solicitud pasa a `approved` solo si esa operación termina satisfactoriamente. La opción `rejected` registra operador, fecha y motivo sin agrupar nada. Las decisiones cerradas no pueden repetirse desde el panel.

El estado `approved` o `rejected` queda disponible para el workspace que solicitó la revisión. No se exponen datos de otros workspaces, no se emiten entitlements, no se crean ni modifican órdenes y no hay transferencias comerciales entre workspaces. **Fuera de alcance:** unificación de los circuitos de activación/entitlements (PR 3B), historial visible para clientes, administración general de workspaces y reconciliación de casos comerciales bloqueados.

**Configuración Render DEV previa a probar avisos:** `MININODE_REVIEW_OPERATOR_EMAILS` (correos exactos de operadores permitidos), `MININODE_CONTACT_EMAIL` (misma casilla usada para contacto comercial), `MININODE_REVIEW_FROM_EMAIL` (remitente verificado en Resend), `RESEND_API_KEY` (secreto), opcional `MININODE_REVIEW_PANEL_URL` (link DEV del panel). Si faltan los parámetros de correo, no se envía ningún aviso y el backend deja constancia no sensible en logs. Solo activar estos valores en DEV, sin escribirlos en el repo, tests, PR o documentación.

**Migración aditiva:** `20261020_access_site_group_operator.sql`, catalogada por checksum pero su ejecución está detenida salvo aprobación explícita por entorno mediante `MIGRATION_APPROVED_FILES`. No habilitar en producción hasta autorización independiente.
