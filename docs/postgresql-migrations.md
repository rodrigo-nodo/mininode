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


## Preparación integral DEV → PROD - octubre 2026 (solo código)

Se incorporan siete SQL aditivos de DEV, sin cambiar sus contenidos, al catálogo revisado de `main`. Por defecto el runner no se conecta a la base si `MIGRATION_APPROVED_FILES` está vacío. Este PR no ejecuta SQL, no cambia Render ni autoriza el despliegue funcional.

### Base inspeccionada en solo lectura

Render PROD `mininode` PostgreSQL 18: 289 diagnósticos, 4 asociaciones de sitio, 3 usuarios, 2 workspaces, 0 `billing.orders`, 0 `access.entitlements`, 3 `privacy.correction_plan_order` (2 marcadas `paid`). Existen Access, Billing, Privacy y FK canónica `privacy_diagnostic_workspace_site_fk`. No existen `public.schema_migrations`, las cinco tablas nuevas de site aliases/solicitudes/operador/reconciliaciones/auditoría, ni `workspace_sites.detached_at` ni `privacy.diagnostic.requested_url`. No inferir que órdenes antiguas son cobros reales; conservar todo.

### Autorización operativa PROD separada del merge

Antes de cualquier DDL: confirmar respaldo restaurable; identificar base y servicio; validar compatibilidad de la versión anterior del backend; registrar recuentos y esquema; obtener autorización expresa para PROD. El servicio `mininode-backend-prod` sigue rama `main`, despliega automáticamente y **no tiene actualmente Pre-deploy command**. No cambiar Render sin autorización operativa específica. Configurar Pre-deploy como `python scripts/predeploy_migrations.py` solo cuando esté autorizado y se haya verificado `DATABASE_URL` interno correcto. Mantener `MIGRATION_APPROVED_FILES` vacío hasta esa autorización.

**Tanda A** (seis nombres, ordenados alfabéticamente):

```text
20261019_access_site_aliases.sql,20261019_access_workspace_site_unlink.sql,20261020_access_site_group_review_requests.sql,20261020_access_site_reconciliations.sql,20261020_privacy_requested_url.sql,20261022_access_entitlement_admin_events.sql
```

Verificar tabla de solicitudes antes de **Tanda B**, que contiene solamente:

```text
20261020_access_site_group_operator.sql
```

**Dependencia:** el operador requiere la tabla creada por la migración `site_group_review_requests`, que alfabéticamente viene después de `site_group_operator`; no intentar los siete nombres en una única lista ordenada. El runner registra cada migración transaccionalmente en `public.schema_migrations`; revisar las siete filas con sus hashes y la estructura resultante. Repetir recuentos de registros de Access, Billing, Privacy y órdenes históricas. Los cambios ya aplicados en una transacción previa no se revierten al hacer rollback del backend. Si falla una tanda, detener publicación funcional y corregir forward-only, sin borrar datos.

Tras ambas tandas, retirar/limpiar `MIGRATION_APPROVED_FILES` y verificar entorno antes de publicar el PR funcional. Las migraciones `20260928_...` y `20261006_a4_billing_core.sql` permanecen bloqueadas. No ejecutar scripts de reconciliación `--apply`, ni activar Mercado Pago, ni agregar secretos al repositorio. La BD PROD permite conexiones externas `0.0.0.0/0`; revisar esa exposición mediante gestión operativa separada.

**PR posterior:** integrar funcionalidades DEV sobre `main` conservando Content Reader V1 y CI actual, con validación E2E y merge autorizado individualmente.


## Cierre de observaciones independientes O1-O3 (PR #377)

- **O1 — Ensayo PostgreSQL 18:** `backend/tests/test_prod_promotion_e2e.py` crea una BD temporal solo desde `mininode_test` de CI, inicializa esquemas Access/Privacy/Billing, inserta registros sintéticos vinculados, demuestra que B antes de A falla, aplica A→B y verifica siete registros de checksum, las tablas/columnas, conservación de datos, reintentos idempotentes y rollback transaccional ante SQL fallido. CI lo ejecuta en PostgreSQL 18 descartable. No presupone respaldo ni autorización para DDL de producción.
- **O2 — Segunda inspección de solo lectura de PROD:** PostgreSQL `18.6`, BD `mininode`: `public.schema_migrations` ausente, cinco tablas nuevas ausentes, `access.workspace_sites.detached_at` ausente y `privacy.diagnostic.requested_url` ausente. Se revisaron FKs e índices en tablas Access/Privacy y se confirmaron 289 diagnósticos, 4 vínculos, 3 usuarios, 2 workspaces, 3 órdenes históricas, 0 `billing.orders` y 0 `access.entitlements`. La inspección debe repetirse en la ventana real de ejecución; no confirma restaurabilidad de respaldo.
- **O3 — Ruta alternativa bloqueada:** `.github/workflows/production-db-migration.yml` rechaza expresamente los siete nombres de la promoción antes de ejecutar `scripts/run_migration.py`. El único procedimiento autorizado para este alcance será el runner canónico `scripts/predeploy_migrations.py` con checksums y allowlist exacta, en tandas separadas.

**Estado operativo:** el cierre en código y el resultado de CI NO autorizan ejecutar migraciones en PROD. Pendiente verificar respaldo restaurable, identidad de conexión, configuración efectiva de Pre-deploy y aprobación específica de cada tanda. No habilitar automáticamente un deploy funcional, no registrar falsamente las migraciones como aplicadas y no autorizar merge sin revisión de CI del PR.

## PW-03 / PROD - PR 1: esquema aditivo preparado (sin ejecución)

El archivo `20261026_privacy_entitled_plans.sql` se incorpora **idéntico al validado en DEV** y al catálogo SHA-256 del runner. El workflow manual legado `.github/workflows/production-db-migration.yml` rechaza explícitamente este archivo (y variantes de ruta) antes de cualquier conexión; el test del guard verifica el rechazo real de estos argumentos. El único camino admitido para aplicar este SQL, tras aprobación operativa separada, es `scripts/predeploy_migrations.py`. Crear `privacy.entitled_plan` y `privacy.entitled_plan_check` no elimina ni transforma `privacy.correction_plan`, `privacy.correction_plan_order`, `privacy.correction_plan_check` ni `privacy.diagnostic`. El backend actual de `main` debe seguir funcionando con el esquema ampliado. El modelo nuevo solo será consumido por una promoción posterior de PW-03.

**Estado:** preparado en GitHub; no se ha cambiado ninguna base, variable de Render ni allowlist. El merge del PR no autoriza ejecutar la migración. Mientras `MIGRATION_APPROVED_FILES` permanezca vacío, Pre-deploy no se conecta a PostgreSQL.

### Preflight obligatorio, SOLO lectura, antes de ejecutar en PROD

1. Identificar servicio Render PROD, base actual (`current_database()`), versión PostgreSQL, SHA backend y configuración efectiva del Pre-deploy; nunca deducirlos solo de `render.yaml`.
2. Revisar `to_regclass` para `access.workspace_sites`, `access.entitlements`, `privacy.diagnostic`, ambas tablas nuevas y las tres tablas legadas; revisar columnas necesarias, PK, FK, historial en `public.schema_migrations` y permisos DDL del usuario de migración.
3. Registrar recuentos de diagnósticos, entitlements, `billing.orders`, planes y órdenes comerciales antiguos, así como dependencias externas. Contrastar con la última auditoría, que podría estar desactualizada.
4. Confirmar respaldo **recuperable** y procedimiento de recuperación; no suponer que un backup no ensayado permite restore.
5. Verificar que la migración ya no figure como aplicada en el historial (o que su checksum coincida exactamente), CI verde y Reviewer PASS; obtener autorización separada de ejecución en PROD.

### Orden autorizado solo después del preflight y aprobación operativa

Configurar y ejecutar exclusivamente `20261026_privacy_entitled_plans.sql` en el runner con allowlist exacta por entorno; no reactivar tandas A/B anteriores ni mezclar DDL destructivo. Confirmar las dos tablas nuevas, cinco FK, índices, checksum en `public.schema_migrations`, cero registros nuevos, y recuentos históricos intactos. Vaciar otra vez la allowlist tras la ventana aprobada. La configuración efectiva del servicio y el despliegue no se cambian en este PR.

**Rollback:** una aplicación transaccional fallida se revierte automáticamente junto a su registro de historial. Si la migración ya fue confirmada, volver al backend anterior **no** elimina las tablas: conservar el esquema expandido para compatibilidad y usar corrección forward-only ante problemas. No hacer `DROP` ni restaurar sobre una base con datos nuevos como respuesta automática.

### Próximas etapas

**Riesgo observado por Reviewer (O1, requisito PR 2):** las FK individuales del esquema nuevo verifican existencia pero no que `entitlement_id` y `original_diagnostic_id` correspondan al mismo `workspace_site_id`. Antes de habilitar la API en PROD, sus rutas de escritura **y lectura** deben verificar la pertenencia y contar con tests negativos de asociaciones cruzadas. Esta verificación no se sustituye por la aplicación de la migración.

PR 2 habilitará el backend nuevo, PR 3 el frontend, PR 4 retirará código legado y PR 5 preparará la eliminación física de tres tablas comerciales antiguas de PROD **solo después** de demostrar que no existen pagos ni derechos comerciales pendientes, preservar evidencia necesaria y obtener autorización destructiva independiente. No transportar `20261029_pw03c3_retire_legacy_dev.sql` a PROD. PW-04 Mercado Pago queda fuera de la etapa 1.
