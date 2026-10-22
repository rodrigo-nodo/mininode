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


## PW-02 - Auditoría de cortesías

La tabla `access.entitlement_admin_events` se crea **exclusivamente mediante** la migración versionada
`20261022_access_entitlement_admin_events.sql`. No hay DDL de PW-02 en el startup de FastAPI.
El SQL es aditivo, conserva los registros existentes y está aprobado por checksum en
`backend/scripts/predeploy_migrations.py`. El despliegue **no la ejecuta automáticamente**:
antes de habilitar PW-02 en un entorno nuevo, verificar que existan `access.users` y
`access.entitlements`, revisar el estado real de la tabla y autorizar explícitamente
el nombre en `MIGRATION_APPROVED_FILES` para ese servicio, con la secuencia de
pre-deploy documentada más arriba. Si la tabla ya existía por el inicializador
anterior, se debe verificar que su estructura y restricciones coincidan; la
migración es idempotente sobre un esquema compatible.

**DEV y PROD requieren autorizaciones operativas separadas.** No activar ni ejecutar
DDL en PROD por el merge del código. El rollback del código no elimina la tabla,
y sus eventos de auditoría deben preservarse.


## Consultas PostgreSQL mediante Render Shell (DEV)

**Procedimiento operativo validado en octubre de 2026.** El PostgreSQL DEV
`mininode-db-dev` (`mininode_db_dev`) no permite conexiones externas porque su
lista de IP autorizadas está vacía. No abrir el acceso público para inspeccionar la BD.
Usar la pestaña **Shell** del servicio Render **`mininode-backend-dev`**, que
dispone de conexión interna mediante la variable `DATABASE_URL`.

- Entregar al operador **un comando por paso, en una sola línea**, para copiar
  directamente en Shell. Nunca imprimir `DATABASE_URL`, contraseñas ni tokens.
- Identificar el entorno con una consulta de solo lectura antes de cualquier
  operación; confirmar `mininode_db_dev`.
- Por defecto usar exclusivamente `SELECT` y consultas al catálogo PostgreSQL.
  No ejecutar DDL, migraciones, inserts o updates sin autorización explícita
  para la base y entorno concretos.
- Tras cambios de backend en `dev`, comprobar que Render desplegó el último
  commit: el despliegue automático de `mininode-backend-dev` puede estar
  deshabilitado. El código fusionado en GitHub no garantiza que la Shell ya lo tenga.
- **PROD** requiere identificación, inspección y autorización independientes;
  no reutilizar automáticamente permisos ni comandos de ejecución de DEV.

Comandos de solo lectura, cada uno en **una línea** (desde `/app` en Render Shell):

**1. Identificar base y existencia de tablas:**

```bash
python -c 'import os,psycopg; c=psycopg.connect(os.environ["DATABASE_URL"]); print(c.execute("SELECT current_database(),to_regclass('\''access.entitlement_admin_events'\'')::text,to_regclass('\''public.schema_migrations'\'')::text").fetchone()); c.close()'
```

**2. Inspeccionar estructura, restricciones e índices de PW-02:**

```bash
python -c 'import os,psycopg; c=psycopg.connect(os.environ["DATABASE_URL"]); q=["SELECT column_name,data_type,is_nullable,column_default FROM information_schema.columns WHERE table_schema=%s AND table_name=%s ORDER BY ordinal_position","SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid=%s::regclass ORDER BY conname","SELECT indexname,indexdef FROM pg_indexes WHERE schemaname=%s AND tablename=%s"]; p=[("access","entitlement_admin_events"),("access.entitlement_admin_events",),("access","entitlement_admin_events")]; [(print("CONSULTA",i+1),[print(r) for r in c.execute(s,a).fetchall()]) for i,(s,a) in enumerate(zip(q,p))]; c.close()'
```

**3. Revisar migración registrada y eventos de auditoría sin mostrar motivos ni
correos personales:**

```bash
python -c 'import os,psycopg; c=psycopg.connect(os.environ["DATABASE_URL"]); print("MIGRACION:",c.execute("SELECT filename,checksum_sha256 FROM public.schema_migrations WHERE filename=%s",("20261022_access_entitlement_admin_events.sql",)).fetchall()); print("AUDITORIA:",c.execute("SELECT id::text,entitlement_id::text,action,created_at FROM access.entitlement_admin_events ORDER BY id").fetchall()); c.close()'
```

### Caso validado - PW-02 en DEV

Antes de ejecutar `20261022_access_entitlement_admin_events.sql` se comprobó
que la tabla, restricciones e índices existentes coincidían con el SQL versionado.
Se registraron **cuatro eventos históricos**. La primera ejecución desde Shell
falló con `Migration not in reviewed catalog` porque Render aún usaba un deploy
anterior a PR #375; se desplegó el merge de `dev` y se validó el checksum.

Con autorización expresa para **DEV**, se aplicó mediante el runner canónico:

```bash
MIGRATION_APPROVED_FILES=20261022_access_entitlement_admin_events.sql python scripts/predeploy_migrations.py
```

Resultado: `Applied: 20261022_access_entitlement_admin_events.sql`.
Posteriormente, `public.schema_migrations` confirmó el checksum revisado
`80ca278aeb683725b64995ba60a54dc42da899ac68c264972f1e8f7bac7c3208`;
los cuatro eventos originales conservaron sus identificadores. Una prueba
funcional conceder→revocar agregó ambos eventos para el mismo entitlement.
**Este caso documenta una ejecución manual autorizada en DEV; no implica
autorizar futuras ejecuciones ni PROD.**
