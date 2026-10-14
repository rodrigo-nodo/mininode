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
real de cada base con las cuatro migraciones históricas y sus efectos. La primera
implementación NO autoriza ejecutar automáticamente los SQL anteriores,
especialmente `20260928_access_a2_1_workspace_sites.sql`, que destruye tablas.
No marcar una migración como aplicada sin comprobar su efecto y checksum.
Cada nueva migración requiere evaluación de seguridad, compatibilidad hacia atrás
con la versión de backend aún activa y autorización operativa antes de sumar
su nombre a la lista. No añadir archivos destructivos a la allowlist sin
autorización específica y respaldo/plan de recuperación.

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
