# PW-03 — Retiro de tres tablas antiguas de Privacy Web

**Estado:** limpieza física pendiente. El ejecutor actual (#426, #427, #428)
está desplegado en producción, pero **no se ha ejecutado el borrado**.
Este documento describe la versión simplificada propuesta en un PR posterior.
**Aprobar o integrar el PR NO autoriza ejecutar `--execute`.**

## Alcance exacto

Se eliminan **solamente** estas tres tablas de datos de prueba:

| Tabla | Filas esperadas |
| --- | ---: |
| `privacy.correction_plan` | 2 (`active`) |
| `privacy.correction_plan_order` | 3 (2 `paid`, 1 `pending_payment`) |
| `privacy.correction_plan_check` | 1 |

Se conservan `privacy.diagnostic` (298 en el preflight del 03-11-2026),
`privacy.entitled_plan`, `privacy.entitled_plan_check`,
`access.entitlements`, `billing.orders` y todas las demás tablas.
Las dos órdenes antiguas marcadas `paid` son pruebas **sin pagos reales**,
según la confirmación previa del Product Owner. La decisión de esta operación
es **no realizar un respaldo adicional de las tres tablas** y aceptar
la pérdida irreversible de los seis registros. Esta decisión no se extiende
a otros datos ni significa que existan pagos verificados por sistema.

## Decisión de simplificación

La versión previa exigía dos huellas SHA-256 privadas de clúster y filas,
cuya transmisión a PostgreSQL abría un riesgo de exposición en logs de
sentencias lentas. Ese mecanismo se reemplaza por una autorización manual
explícita y verificaciones estructurales y de destino.

- Se **eliminan** la entrada y la transmisión de huellas privadas, y el
  control especial de parámetros/módulos de logs asociado a esas huellas.
  No se necesita pedir a Render que cambie la configuración de PostgreSQL.
- Se **mantienen** identificación estricta del servicio Render PROD,
  branch `main`, SHA LIVE, URL y host interno PostgreSQL exactos, rol/base
  y comprobación de nodo primario.
- Se **mantienen** recuentos, estados y relaciones de planes, órdenes y
  revisiones, además de locks `NOWAIT`, una única transacción,
  `DROP TABLE ... RESTRICT`, validación posterior y rollback por error
  previo al `COMMIT`.
- **Riesgo aceptado al simplificar:** ya no se detectan cambios en otras
  columnas de filas que mantengan la misma cantidad, estados y relaciones.
  Por eso hay que reconfirmar que continúan siendo datos descartables
  antes de autorizar el borrado.
- Ningún secreto, correo, huella o URL de conexión se imprime ni se
  introduce como argumento de terminal. La frase destructiva se
  introduce oculta por terminal interactiva y **no se envía a SQL**.
  Los valores de destino y acuse enviados al servidor son constantes
  públicas, no credenciales.

## Procedimiento manual — tres pasos

**1. Verificar.** Confirmar con el conector Render de solo lectura el recurso
PostgreSQL primario `mininode-db` (`dpg-da5fjmbm8hqs73chdceg-a`),
sin réplicas, y el inventario comercial. Confirmar que el nuevo backend está
LIVE en Render en el último commit de `main`.
En **Render → mininode-backend-prod → Shell**, ejecutar **una sola línea**:

```sh
python scripts/pw03_retire_legacy_shell.py --check
```

Esperado: PASS con **2 planes / 3 órdenes / 1 revisión** y sin
acciones destructivas. El control es solo lectura y no otorga autorización.
Si falla o cambian los registros, **detenerse, no reintentar a ciegas**.

**2. Autorizar.** Tras revisar el resultado, obtener **una autorización
posterior, específica y explícita del Product Owner** para eliminar
las tres tablas concretas en PostgreSQL PROD, confirmando que los seis
registros siguen siendo pruebas descartables, que las dos órdenes
`paid` no son cobros reales y que se acepta no hacer respaldo adicional.
El permiso para crear o mergear el PR **no es este permiso**.

**3. Ejecutar y comprobar.** Solo con esa autorización y la versión LIVE
validada, en la misma Render Shell invocar **una única línea**:

```sh
python scripts/pw03_retire_legacy_shell.py --execute
```

El ejecutor exige terminal interactiva, el **postgresId aprobado**, el
**SHA completo del backend LIVE** y una **frase destructiva oculta**.
No acepta confirmación automática por argumentos o variables de entorno.
Revalida conexión y estructura antes de solicitar confirmación. Una vez
confirmada, el SQL verifica la base/usuario/primaria, bloquea las tres
tablas con `ACCESS EXCLUSIVE NOWAIT` y **reverifica los recuentos,
estados y relaciones bajo esos locks** antes de ejecutar exactamente
tres `DROP TABLE ... RESTRICT` dentro de `BEGIN/COMMIT`.

No ejecutar el SQL parcial, no habilitarlo en Pre-deploy, ni crear
endpoint HTTP o workflow automático. El SQL solo vive en
`backend/operations/pw03_pr5_retire_legacy_commerce.sql`.

Tras el resultado, comprobar por lectura que no existen las tres tablas
y que permanecen diagnósticos, entitlements, planes actuales y billing.
Comprobar que Privacy Web y `/privacy/mi-plan/` siguen funcionando.
Si falla, **no reintentar**: si el fallo ocurrió antes del `COMMIT`, se
revierte toda la transacción; después del `COMMIT` podría haber eliminado
las tablas aunque el ejecutor haya mostrado FAIL en la comprobación final.

## Evidencia y límites

- Último `--check` real (versión previa del ejecutor): PASS con commit
  `b555f1fca9e1` y recuentos **2 / 3 / 1**; el bloqueo antiguo de logs
  funcionó, y **no eliminó datos**.
- La versión simplificada se debe ensayar en PostgreSQL 18 **desechable**
  durante CI; después del merge, volver a validar la misma versión
  desplegada en Render mediante `--check`.
- El chequeo comercial de ausencia de pagos reales es una declaración
  aprobada por el PO y debe seguir vigente; los estados `paid` en las
  tablas antiguas **no demuestran por sí solos pagos realizados**.
- Tras el `COMMIT`, estas tablas no se recuperan con un rollback de Git;
  sin respaldo adicional, la pérdida de sus registros es irreversible.

## Relación con PW-04

Este retiro **no** habilita checkout, no concede entitlements y no integra
Mercado Pago. PW-04 es independiente.
