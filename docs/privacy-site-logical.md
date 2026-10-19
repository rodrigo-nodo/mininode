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
