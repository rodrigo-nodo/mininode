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
2. Identificar y confirmar en tiempo real la BD de destino, responsable operativo,
   registro de recuentos/estados, dependencias, versión desplegada y ausencia de
   nuevos derechos u obligaciones pendientes. Volver a ejecutar el inventario.
3. Confirmar respaldo **restaurable y probado** de los datos relevantes, o documentar
   una aceptación explícita y específica de pérdida irreversible. DEV no es un respaldo de PROD.
4. Ensayar primero en PostgreSQL 18 desechable/DEV con datos sintéticos;
   conservar evidencia de las pruebas y revisión independiente.
5. Asegurar que la operación se realice fuera de despliegues, con una conexión
   identificada, usando `psql -X -v ON_ERROR_STOP=1`. No utilizar el conector de
   consultas de solo lectura ni habilitar la migración en Render Pre-deploy.

## Procedimiento de operación, solo después de la autorización

Archivo **manual**: `backend/operations/pw03_pr5_retire_legacy_commerce.sql`.
Está deliberadamente fuera de `backend/migrations/`, del catálogo de checksums
y de `MIGRATION_APPROVED_FILES`. No hay automatismo que lo ejecute.

En la **misma sesión psql** conectada a la base explícitamente validada:

```sql
SELECT current_database(); -- En PROD, debe responder mininode
SELECT set_config('mininode.pw03_pr5_target_database', 'mininode', false);
SELECT set_config('mininode.pw03_pr5_ack', 'DELETE_2_PAID_1_PENDING_LEGACY_ORDERS', false);
```

Luego, desde la raíz del repositorio, en esa **misma conexión psql**:

```text
\i backend/operations/pw03_pr5_retire_legacy_commerce.sql
```

Antes del script, la consola debe usar `ON_ERROR_STOP=1`; no ejecutar si la identidad
o los recuentos difieren. El SQL usa una transacción, locks `NOWAIT`, comprobaciones
estrictas del inventario y `DROP TABLE ... RESTRICT` en orden de dependencias.
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
