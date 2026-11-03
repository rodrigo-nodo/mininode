# PW-03 PR 5 — Retiro físico del comercio antiguo (procedimiento manual)

**Estado:** preparado en código; **NO ejecutado**. El merge del PR 5 no constituye autorización para borrar datos en ningún entorno.

## Alcance

Borrar únicamente `privacy.correction_plan_check`, `privacy.correction_plan_order` y `privacy.correction_plan`.
Conservar `privacy.diagnostic`, `privacy.entitled_plan`, `privacy.entitled_plan_check`,
`access.entitlements`, `billing.orders`, usuarios, workspaces y sus historiales.
El backend nuevo ya no utiliza las tablas antiguas; el operador de agrupación
de sitios consulta su existencia y puede operar cuando desaparezcan.

## Inventario auditado en PROD (2 de noviembre de 2026)

| Tabla | Registros |
|---|---:|
| `privacy.correction_plan` | 2, ambos `active` |
| `privacy.correction_plan_order` | 3: 2 `paid` con `paid_at` y Plan, 1 `pending_payment` sin Plan |
| `privacy.correction_plan_check` | 1 |
| `privacy.diagnostic` | 298 |
| `privacy.entitled_plan` / `privacy.entitled_plan_check` | 2 / 1 |
| `access.entitlements` / `billing.orders` | 2 (ambos `internal_grant`) / 0 |

Las marcas `paid` **no prueban un cobro real**. El Product Owner ha indicado que no existen
clientes comerciales, pero antes de ejecutar debe confirmar expresamente el
tratamiento de las dos órdenes marcadas como pagadas.

No se observaron vistas, funciones ni triggers SQL externos que dependan de las tablas.
Se identificaron FK entre las tablas antiguas, y hacia `privacy.diagnostic`.
Una FK externa agregada posteriormente abortará la operación por `RESTRICT`.

## Requisitos previos (obligatorios, no automatizados)

1. Obtener **autorización destructiva específica** que identifique las tres tablas,
   el entorno y el tratamiento de las 2 órdenes `paid`.
2. Identificar y confirmar en tiempo real el **recurso PostgreSQL exacto en Render**:
   workspace, postgresId, tipo primary, ausencia de réplicas y base seleccionada.
   Obtener la huella de cluster SHA-256 del archivo de preflight, contrastarla por
   una segunda vía (Render PostgreSQL, no solo el cliente psql), y vincularla
   expresamente a la autorización operativa. Un nombre de BD coincidente no basta.
   Revisar dependencias, backend LIVE y derechos u obligaciones pendientes.
3. Autorizar **un inventario privado de filas individuales**, con IDs, estados,
   vínculos entre orden/Plan/revisión y la huella SHA-256 de las tres tablas.
   El archivo de preflight produce estos manifiestos sin correos ni snapshots;
   su huella incluye *todas* las columnas de las filas, incluido el contenido
   sensible, sin exponerlo. El hash debe aprobarse de manera independiente y
   permanecer fijo hasta la ejecución; no regenerarlo automáticamente justo
   antes de borrar.
4. Confirmar respaldo **restaurable y probado** de los datos relevantes, o documentar
   una aceptación explícita y específica de pérdida irreversible. DEV no es un respaldo de PROD.
5. Ensayar primero en PostgreSQL 18 desechable/DEV con datos sintéticos;
   conservar evidencia de las pruebas y revisión independiente.
6. Asegurar que la operación se realice fuera de despliegues, con una conexión
   identificada, usando `psql -X -v ON_ERROR_STOP=1`. No utilizar el conector de
   consultas de solo lectura ni habilitar la migración en Render Pre-deploy.

## Procedimiento de operación, solo después de la autorización

Archivo **manual**: `backend/operations/pw03_pr5_retire_legacy_commerce.sql`.
Está deliberadamente fuera de `backend/migrations/`, del catálogo de checksums
y de `MIGRATION_APPROVED_FILES`. No hay automatismo que lo ejecute.

**Primero, en modo solo lectura:** ejecutar
`backend/operations/pw03_pr5_readonly_preflight.sql` desde la instancia
PostgreSQL de Render confirmada. Comprobar que `timezone` sea `UTC`.
Su salida contiene: identificador de BD, huella SHA-256 de clúster y huella
SHA-256 de **todas las filas antiguas**, más manifiestos con IDs y estados
(no emails ni snapshots). Guardar el inventario completo en evidencia privada,
con la identidad del recurso Render (postgresId) y la aprobación independiente.
No publicar los manifiestos ni huellas aprobadas en el repositorio.

**Solo después de autorización destructiva, ensayos y confirmación de respaldo
o aceptación de riesgo**, en la **misma sesión psql** conectada al recurso
previamente verificado:

```sql
SELECT current_database(); -- En PROD debe responder mininode
SELECT set_config('mininode.pw03_pr5_target_database', 'mininode', false);
SELECT set_config('mininode.pw03_pr5_target_cluster_sha256', '<HUELLA_CLUSTER_APROBADA>', false);
SELECT set_config('mininode.pw03_pr5_approved_inventory_sha256', '<HUELLA_FILAS_APROBADA>', false);
SELECT set_config('mininode.pw03_pr5_ack', 'DELETE_2_PAID_1_PENDING_LEGACY_ORDERS', false);
```

Las dos huellas deben provenir de la evidencia **previamente aprobada**, no de
consultas a la conexión que se va a borrar en ese instante. Los valores vacíos
o diferentes abortan la operación. El identificador físico de clúster puede
compartirse entre clones o réplicas físicas: combinar siempre el hash con la
identidad independiente del recurso Render y verificar que sea la instancia
primaria adecuada.

Luego, desde la raíz del repositorio, en esa **misma conexión psql**:

```text
\i backend/operations/pw03_pr5_retire_legacy_commerce.sql
```

Antes del script, la consola debe usar `ON_ERROR_STOP=1`; no ejecutar si la identidad
o los recuentos difieren. El SQL usa una transacción, locks `NOWAIT`, validación de clúster,
comprobaciones estrictas del inventario **bajo lock**, comparación del
hash de todas las filas y `DROP TABLE ... RESTRICT` en orden de dependencias.
Las variables de sesión son controles contra errores operativos, no un sistema
de autorización que reemplace los permisos de la base. Los timestamps del
inventario se normalizan con TimeZone UTC; el procedimiento configura UTC
durante la transacción.
Si algo falla **antes de COMMIT**, cerrar/abortar la transacción (no forzar commit).
No ejecutar la sentencia por partes.

## Evidencias posteriores y recuperación

Comprobar con SELECT que las tres tablas ya no existen; registrar diagnósticos,
entitlements y nuevos Planes con los recuentos previos; verificar las APIs de
diagnósticos, `/privacy/mi-plan/` y agrupación de sitios. Confirmar que el Plan
nuevo sigue accesible y que el despliegue Render permanece LIVE.

**Rollback:** antes de COMMIT, la transacción se revierte. Tras COMMIT, la eliminación
de tablas y filas **no se deshace con un rollback de código**. Solo un respaldo
restaurable adecuado puede recuperar ese contenido; si se aceptó el riesgo sin
respaldo, no prometer reconstrucción. Nunca recrear automáticamente estas tablas
en PROD desde fixtures de tests.

## Relación con PW-04

La limpieza de comercio legado no habilita checkout, no concede entitlements y
no activa Mercado Pago. PW-04 es un trabajo separado.
