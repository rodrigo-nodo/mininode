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

**Estado del ejecutor:** el PR #426 incorpora en Docker únicamente los dos
SQL de PW-03 y `backend/scripts/pw03_retire_legacy_shell.py`. **Todavía
no está desplegado en PROD**: los comandos de Render Shell estarán disponibles
solo tras CI, revisión independiente, merge autorizado y confirmación del
backend LIVE. El ejecutor usa Python/`psycopg`, sin instalar `psql`.

**Seguridad de destino (B1):** para conectar, el ejecutor exige el hostname
interno **completo y exacto** `dpg-da5fjmbm8hqs73chdceg-a`, sin sufijos
ni dominios alternativos, así como la base, usuario y puerto aprobados.
Rechaza `hostaddr`, `service`, múltiples destinos y otros parámetros libpq
no aprobados, y también cualquier variable de entorno `PG*` con valor,
incluidas `PGHOSTADDR` y `PGSERVICE`. Debe contrastarse este hostname exacto
contra **Internal Database URL** de la instancia Render primaria durante la
validación real, sin publicar el URL ni desactivar controles si falla.
La coincidencia de huellas por sí sola no identifica un clon físico.

**El merge de este PR tampoco autoriza ejecutar el borrado.**

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

**Pendiente:** completar la revisión/CI del ejecutor del PR #426,
verificarlo en Render Shell una vez LIVE, aprobar privadamente destino,
huellas y controles de logs, y obtener **autorización destructiva específica
para PROD**. Hasta entonces, las tres tablas siguen intactas.

## Ejecutor Render Shell — implementación preparada (pendiente de CI/merge/autorización)

El PR de ejecutor incorpora **solo** los dos SQL aprobados de PW-03 en la
imagen Docker y `backend/scripts/pw03_retire_legacy_shell.py` con `psycopg`.
No añade `psql`, no crea endpoint HTTP, no cambia Pre-deploy ni toca la base
durante el despliegue. Hasta completar CI, revisión y merge del PR, **no
es posible ejecutar los comandos siguientes en el servicio PROD**.

En **Render → `mininode-backend-prod` → Shell**, solo cuando el commit
del PR aprobado esté desplegado y el backend esté LIVE.

**Validación de identidad:** el ID inmutable `RENDER_SERVICE_ID` sigue
siendo obligatorio y se contrasta con la rama, repositorio, tipo de servicio,
hostname público y SHA desplegado. `RENDER_SERVICE_NAME` es un identificador
legible que puede diferir del nombre mostrado en el Dashboard; no se usa
para autorizar ni denegar una operación destructiva. El rechazo por ese
nombre observado en la primera prueba `--check` se corrige en un PR
independiente. La comprobación exacta del destino PostgreSQL permanece
sin cambios.

**Inspección, una sola línea de Render Shell:**

```sh
python scripts/pw03_retire_legacy_shell.py --check
```

Este comando verifica las variables automáticas de Render (servicio PROD,
rama `main`, repositorio, SHA desplegado), la URL interna de la BD sin
mostrarla, y ejecuta únicamente el preflight SQL de lectura. Además de
recuentos 2/3/1, comprueba estados, enlaces e indicadores de pago del
inventario esperado. **PASS significa solo que el preflight estructural
coincide; NO significa que las huellas/filas se hayan aprobado
independientemente ni que la operación destructiva esté autorizada.**
No imprime huellas, IDs ni datos personales. Si el hostname interno exacto
no coincide, **detenerse y revisar, no desactivar el guard**.

**Ejecución destructiva, exclusivamente después de autorización PO separada
y de la aprobación privada y previa de las dos huellas y SHA exacto:**

```sh
python scripts/pw03_retire_legacy_shell.py --execute
```

El ejecutor exige una terminal interactiva: solicita `postgresId`,
commit completo aprobado y, con entrada oculta, las dos huellas aprobadas
y la frase destructiva específica. **No copiar aquí ni publicar las huellas,
contraseñas o la cadena `DATABASE_URL`.** No se permite automatizar esa
interacción mediante un pipe ni establecer aprobaciones en variables de
entorno. Una vez confirmadas, el ejecutor abre **una única conexión**,
carga las aprobaciones como variables de sesión, ejecuta el SQL íntegro
con `BEGIN/COMMIT`, locks `NOWAIT` y `DROP RESTRICT`, y valida que
las tablas antiguas hayan desaparecido mientras el esquema nuevo permanece.
**No derivar ninguna de las huellas de la sesión a borrar:** deben provenir
del preflight independiente ya revisado. Sin la autorización explícita
adicional del PO, no invocar `--execute`.

La ejecución imprime solo `PASS` o `FAIL` sin datos sensibles.
Ante `FAIL`, **no reintentar**: consultar estado real mediante conexión
de solo lectura. Si hubo fallo después del `COMMIT`, el borrado podría
haber sucedido a pesar del mensaje `FAIL`; no asumir rollback.
La verificación funcional y administrativa posterior continúa siendo
obligatoria. Se requiere que el servicio permanezca LIVE.

### Comprobación obligatoria de logs (O3, solo antes de ejecutar)

No considerar las huellas invisibles para el servidor solo porque Python
no las imprime: PostgreSQL podría registrar **parámetros de consultas**
según su configuración. En el preflight de solo lectura de PROD del
03-11-2026 se observaron `log_statement=none`,
`log_min_duration_statement=2000` (ms),
`log_parameter_max_length=-1` (sin límite de longitud) y
`log_parameter_max_length_on_error=0`. Esto implica que una consulta
lenta que establezca las huellas podría registrarlas completas en logs
del servidor, aunque el programa no las muestre en consola.

**Antes de autorizar `--execute`**, verificar de nuevo en la instancia
primaria las configuraciones de logging (incluidos parámetros de consultas
lentas, errores y muestreo), determinar si existe posibilidad de registrar
las huellas y **resolver el riesgo** con una configuración de servidor
compatible y aprobada. No cambiar ajustes de PostgreSQL por iniciativa
del ejecutor ni afirmar que los logs están seguros sin esta comprobación.
Si no puede garantizarse que no se registren las huellas, **detener el
borrado y revisar el mecanismo**, sin rebajar el control de destino.
Referencias: [PostgreSQL 18 — parámetros de logs](https://www.postgresql.org/docs/18/runtime-config-logging.html).

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
6. Asegurar que la operación se realice fuera de despliegues, en
   **Render Shell** con el ejecutor Python/`psycopg` del PR #426, tras
   comprobar el commit LIVE y sin acceso a una conexión de otro recurso.
   No utilizar el conector de solo lectura para DDL ni habilitar la
   migración en Render Pre-deploy.
7. Revisar y resolver el riesgo de registros de parámetros sensibles
   descrito en O3 antes de conectar para la ejecución destructiva.

## SQL manual: contrato técnico, no una segunda ruta operativa

El archivo `backend/operations/pw03_pr5_retire_legacy_commerce.sql`
permanece fuera de `backend/migrations/` y de Pre-deploy. El ejecutor
Render Shell lo carga completo **en una única conexión y sesión**, carga
las huellas aprobadas como variables de sesión, y respeta `BEGIN/COMMIT`,
`ACCESS EXCLUSIVE NOWAIT`, recuentos, huella del inventario bajo lock
y `DROP TABLE ... RESTRICT` sin cambios al SQL ya auditado.
**No usar `psql` ni ejecutar manualmente comandos SQL parciales**; las
instrucciones `psql` anteriores se retiraron porque no son la vía
seleccionada para PW-03.

El preflight privado independiente sigue disponible en
`backend/operations/pw03_pr5_readonly_preflight.sql`. Ejecutarlo por
la conexión Render **de lectura**, confirmar `UTC` y aprobar
privadamente el inventario completo y ambas huellas (no volcarlas en
GitHub, logs ni chat). El ejecutor **nunca obtiene esas huellas de la
sesión a borrar para autoautorizarse**.

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
