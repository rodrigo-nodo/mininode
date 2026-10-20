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
- Dos dominios distintos redirigidos: sugerir y pedir confirmación, con verificación técnica.
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
- `site_url` (**sin cambios**): URL HOME final inspeccionada después de redirecciones. Continúa determinando la identidad de sitio en el guardado anónimo y las asociaciones actuales.

`requested_url` se registra en los diagnósticos anónimos, por URL dentro del workspace y sobre una ficha previamente guardada (en este caso corresponde a la URL almacenada desde la que se inicia la inspección). Los diagnósticos anteriores quedan con `requested_url = NULL`, sin reconstrucción inferida. El contenido `diagnostic_snapshot`, score, control de compra, API pública de resultados y algoritmo de agrupación/alias permanecen iguales.

La migración `20261020_privacy_requested_url.sql` es aditiva e idempotente; se incorpora al catálogo de checksums del Pre-deploy, pero requiere autorización explícita en `MIGRATION_APPROVED_FILES` **solo en Render DEV** antes de ejecutar el nuevo backend. No autoriza despliegue en PROD, merge automático ni nuevas conciliaciones.
