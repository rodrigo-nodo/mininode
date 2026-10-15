# Mininode - Migraciones PostgreSQL con Render Pre-deploy

## Decisión
La imagen Docker incluye `backend/scripts/predeploy_migrations.py` y `backend/migrations/`.
Configurar por servicio de Render el **Pre-deploy command**:
`python scripts/predeploy_migrations.py` (directorio de trabajo `backend`).

Render debe disponer de `DATABASE_URL` **interno** de su propia BD (DEV o PROD).
El comando no ejecuta SQL cuando `MIGRATION_APPROVED_FILES` está vacío o ausente.
El cambio de código **no activa Pre-deploy** por sí solo: la configuración efectiva
del servicio en Render debe comprobarse por separado.

## Política de aprobación
`MIGRATION_APPROVED_FILES` contiene nombres SQL exactos, separados por coma, ordenados
alfabéticamente, por ejemplo `20261013_privacy_anonymous_claim.sql`.
Es una allowlist **por entorno**, no una invitación a ejecutar todo el directorio.

**Antes de configurar cualquier allowlist**, conciliar manualmente el estado
real de cada base con las cuatro migraciones históricas y sus efectos. El runner **bloquea en código**, incluso cuando figuren en la allowlist,
`20260928_access_a2_1_workspace_sites.sql`,
`20260928_access_a3_2_privacy_workspace_site.sql` y
`20261006_a4_billing_core.sql`. No se pueden ejecutar mediante Pre-deploy.
En vez de intentar interpretar SQL con expresiones regulares, Pre-deploy exige
que el nombre figure en el catálogo revisado `APPROVED_CHECKSUMS` del runner
y que el SHA-256 del archivo coincida exactamente. Cambios de contenido o archivos
nuevos requieren modificar el catálogo mediante PR revisado y CI. Esto impide
que cualquier variante de SQL no autorizado pase simplemente mediante la allowlist.
El catálogo inicial contiene exclusivamente `20261013_privacy_anonymous_claim.sql`.
La allowlist de Render es una **segunda condición independiente**, no la fuente
de aprobación de contenido. Un checksum no convierte SQL destructivo en seguro:
la revisión humana del SQL es obligatoria antes de catalogarlo.
Una operación destructiva se gestiona fuera de este mecanismo con aprobación
específica, respaldo y procedimiento separado.
No marcar una migración como aplicada sin comprobar su efecto y checksum.
Cada nueva migración requiere evaluación de seguridad, compatibilidad hacia atrás
con la versión de backend aún activa, incorporación explícita de su hash al catálogo
en un PR revisado, y autorización operativa por entorno antes de sumar
su nombre a la allowlist. No añadir archivos destructivos a la allowlist sin
autorización específica y respaldo/plan de recuperación.

Las garantías de rollback, checksum, idempotencia y dos ejecutores simultáneos
se prueban contra PostgreSQL temporal `mininode_test` en Access CI.

El runner usa `public.schema_migrations` (`filename`, `checksum_sha256`,
`applied_at`). Verifica el checksum al reencontrar una migración, y falla si
se editó un SQL ya registrado. Utiliza bloqueo advisory transaccional para
serializar ejecuciones, y confirma SQL + registro en la misma transacción.
Los SQL existentes tienen `BEGIN;` y `COMMIT;` externos; el runner elimina
exclusivamente esas líneas envolventes. Migraciones con SQL que no admite
transacción requieren procedimiento separado, no este ejecutor.

## Activación gradual
1. Merge del mecanismo tras CI y revisión. **Sin tocar bases de datos**.
2. Verificar configuración real del servicio DEV, su rama y su URL PostgreSQL
   interna; comprobar historial y estructura inicial.
3. Configurar Pre-deploy solamente para DEV, con allowlist vacía inicialmente.
4. Aprobar y activar explícitamente la migración pendiente
   `20261013_privacy_anonymous_claim.sql`, sólo tras confirmar dependencias.
5. Inspeccionar logs, `schema_migrations`, esquema y pruebas funcionales;
   verificar que reintentar no reaplica el cambio.
6. PROD: mantener desactivado/sin allowlist hasta autorización explícita,
   conciliación independiente y evaluación de respaldo y compatibilidad.

Si Pre-deploy falla, Render no debe activar la nueva versión de la aplicación.
El rollback de despliegue **no revierte automáticamente** el esquema ya confirmado.
Usar migraciones compatibles con la versión anterior y correcciones forward-only.

## Relación con workflows anteriores
Los workflows manuales de GitHub utilizan conexión externa y permanecen sin
modificar en este PR. No ejecutarlos contra bases cerradas a Internet. Evaluar su
retiro por separado cuando Pre-deploy esté validado en ambos entornos.

## Alcance
El archivo `render.yaml` corresponde a una configuración antigua de servicio Free;
no modificarlo ni asumir que representa el estado efectivo actual de Render.
Este PR no cambia servicios, credenciales, planes, permisos ni bases.


## Reconciliación de FK duplicada de Privacy Web
`20261015_privacy_workspace_site_fk_dedup.sql` conserva la FK canónica
`privacy_diagnostic_workspace_site_fk` y elimina únicamente la FK redundante
`diagnostic_workspace_site_id_fkey` sobre `privacy.diagnostic.workspace_site_id`.
Antes de eliminarla exige que coincidan columnas, tabla y columnas de destino,
acciones ON DELETE/UPDATE, política MATCH, deferrability y validación; aborta
si falta la FK canónica o si las definiciones difieren. Es idempotente. No borra
filas ni columnas y no altera la FK de `claimed_by_user_id`.

Causa histórica: el `CREATE TABLE IF NOT EXISTS` en el inicializador genera
una FK con nombre automático cuando crea la tabla; A3.2 agregó después la
FK canónica. En tablas existentes, el inicializador no recrea la duplicada.
La migración A3.2 histórica permanece bloqueada por el runner.

Esta nueva migración solo queda **catalogada en código**. La habilitación
mediante `MIGRATION_APPROVED_FILES` en DEV exige revisión de CI, inspección
previa del estado de ambas FK y autorización explícita de la operación de DDL.
No habilitar ni ejecutar en PROD como parte de este PR.
