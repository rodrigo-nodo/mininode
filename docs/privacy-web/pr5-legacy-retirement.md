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

Las marcas `paid` **no prueban un cobro real**. El Product Owner confirmó
posteriormente que ambas órdenes eran pruebas, sin pagos reales y que
sus datos pueden descartarse. Se mantiene la verificación operativa
de que no aparecieron nuevos derechos u obligaciones.

No se observaron vistas, funciones ni triggers SQL externos que dependan de las tablas.
Se identificaron FK entre las tablas antiguas, y hacia `privacy.diagnostic`.
Una FK externa agregada posteriormente abortará la operación por `RESTRICT`.

## Decisión operativa — 03-11-2026

Para este retiro puntual se eligió **Render Shell + ejecutor Python/`psycopg`**
como mecanismo provisional de ejecución en cloud, **sin instalaciones en Windows**.
No confundir esa decisión con autorización para borrar.

**Limitación técnica actual:** el `backend/Dockerfile` copia `src/`,
`migrations/` y `scripts/`, pero no `backend/operations/`; tampoco
instala explícitamente `psql`. Por ello el SQL de este runbook **existe
en GitHub, pero todavía no puede lanzarse directamente desde Render Shell**.
El comando de un solo paso **no existe aún**. Hace falta un PR independiente
que incorpore únicamente este SQL en la imagen y un ejecutor manual seguro
con `psycopg`, sin activar Render Pre-deploy, sin modificar el backend
funcional y sin iniciar la operación durante el despliegue.

El ejecutor propuesto deberá usar una única conexión/sesión, los permisos
y la conexión interna del servicio PROD verificado, las dos huellas
**previamente autorizadas** (clúster e inventario), las comprobaciones
bajo `ACCESS EXCLUSIVE NOWAIT`, la secuencia transaccional íntegra y
`DROP TABLE ... RESTRICT`. Debe fallar sin efectos si falta una
aprobación, hay cambios en las filas o existen nuevas dependencias. Registrar
solo PASS/FAIL y evidencia no sensible. No copiar o pegar el SQL por partes.
**El merge de ese futuro PR tampoco autorizará ejecutarlo.**

Otras modalidades no elegidas para este caso: GitHub Actions manual
(requeriría workflow nuevo y conexión externa validada), y el runner
Render Pre-deploy (reservado para migraciones revisadas no incluidas en
este retiro). Política general:
[procedimiento operativo PostgreSQL](../postgresql-migrations.md).

### Decisiones comerciales y de recuperación

El Product Owner confirmó expresamente que las **dos órdenes antiguas
marcadas `paid` fueron pruebas, sin pagos reales**, y que no desea
conservarlas. También decidió **no efectuar un respaldo adicional
de estas tres tablas**, aceptando el riesgo de pérdida irreversible
de sus datos históricos. Ambas decisiones están limitadas a este
retiro; no constituyen una renuncia general a respaldos ni prueban por
sí solas la ausencia de otros derechos u obligaciones.

**Estado de seguridad:** PR #423 y #424 integrados en `main`. Ensayo
del SQL con datos sintéticos en PostgreSQL 18 desechable
[PASS: 436 tests](https://github.com/rodrigo-nodo/mininode/actions/runs/41645175977/attempts/2).
En preflight de PROD de solo lectura se identificaron la BD y el
recurso Render primario, el inventario 2 planes / 3 órdenes / 1 revisión,
las huellas y ausencia de FK externas inesperadas; no se registran aquí
identificadores de filas ni huellas. Antes de ejecutar deberán
contrastarse de nuevo desde una vía independiente y aprobarse los
valores exactos de forma privada.

**Pendiente:** implementar y validar el ejecutor Render Shell, documentar
identidad y huellas autorizadas para la sesión operativa, y obtener
**autorización destructiva específica para PROD**. Hasta entonces,
las tres tablas siguen intactas.

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

## Procedimiento SQL existente — referencia condicionada a autorización

**Importante:** la secuencia `psql` de abajo documenta el contrato
del archivo SQL; **no** es una instrucción lista para ejecutar hoy
desde Render Shell. Requiere un cliente `psql` y el SQL disponible
en el entorno que lo ejecute. La vía elegida para este caso es el
**ejecutor Python/`psycopg` pendiente de implementación y revisión**;
mantener la secuencia como referencia técnica, sin usarla como atajo
operativo. No se ejecutará desde el chat ni se añadirá a Pre-deploy.


Archivo **manual**: `backend/operations/pw03_pr5_retire_legacy_commerce.sql`.
Está deliberadamente fuera de `backend/migrations/`, del catálogo de checksums
y de `MIGRATION_APPROVED_FILES`. No hay automatismo que lo ejecute.

**Primero, en modo solo lectura:** ejecutar
`backend/operations/pw03_pr5_readonly_preflight.sql` desde la instancia
PostgreSQL de Render confirmada. Comprobar que `timezone` sea `UTC` o `Etc/UTC`.
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
