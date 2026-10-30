# PW-03C3 — Retiro de tablas comerciales legadas en DEV

**Estado:** cerrado y validado funcionalmente en DEV el **29-oct-2026 (Chile)**.  
**Ejecución:** Render Shell de `mininode-backend-dev`, BD `mininode_db_dev`.  
**Código:** [PR #414](https://github.com/rodrigo-nodo/mininode/pull/414), merge a `dev` `503f65d70dd2b691e2fd3a8a3585469e199a20b8`.  
**PROD:** sin cambios: conserva tablas y registros históricos; `main` continúa utilizando el flujo comercial legado.

## Inventario previo, verificado en ambas bases

| Relación | DEV previo | PROD (solo lectura) |
|---|---:|---:|
| `privacy.correction_plan` | 0 | 2 |
| `privacy.correction_plan_order` | 0 | 3 |
| `privacy.correction_plan_check` | 0 | 1 |
| `privacy.entitled_plan` | 3 | No existe |
| `privacy.entitled_plan_check` | 3 | No existe |

Las tres órdenes legadas de PROD incluyen dos marcadas `paid` y una `pending_payment`; no inferir cobros reales. Conservar todos estos registros y sus dependencias en PROD.

## Operación realizada en DEV

1. Revisión independiente del PR #414: **PASS**; Access CI: **SUCCESS**. PR preparado, sin ejecución automática.
2. Merge autorizado a `dev`; despliegue manual a Render DEV del SHA `503f65d` confirmado **LIVE**.
3. Render Shell (consulta de solo lectura): verificó `mininode_db_dev`, las tres tablas legadas con **0 filas**, las dos tablas nuevas con **3 filas cada una**, y el archivo `/app/migrations/20261029_pw03c3_retire_legacy_dev.sql` presente.
4. Comprobación de dependencias SQL en DEV: **0 FK externas, 0 vistas dependientes, 0 funciones relacionadas y 0 triggers de usuario**.
5. El Product Owner eligió como referencia el respaldo del **28-oct-2026** y **aceptó expresamente el riesgo de no haber comprobado su restauración**. No se verificó un restore ni se debe describir ese respaldo como probado.
6. Tras autorización específica de la limpieza en DEV, se ejecutó **manualmente en Render Shell** `python scripts/run_migration.py migrations/20261029_pw03c3_retire_legacy_dev.sql`. El comando devolvió `Migration applied: 20261029_pw03c3_retire_legacy_dev.sql`.
7. Verificación posterior de solo lectura: las tres tablas legadas **ya no existen**; `privacy.entitled_plan` = **3**, `privacy.entitled_plan_check` = **3** y `privacy.diagnostic` = **67**. Resultado mostrado: **PASS**.
8. El Product Owner confirmó que `dev.mininode.io` se ve y funciona como antes. No se identificó regresión visible en el Plan. **PW-03C3 cerrado funcionalmente en DEV**.

## Salvaguardas que se aplicaron

La migración exige el nombre exacto de BD `mininode_db_dev`, la existencia de las tres tablas legadas y de las dos tablas nuevas, toma bloqueos `ACCESS EXCLUSIVE ... NOWAIT` antes del examen de filas, rechaza cualquier contenido legado y usa `DROP TABLE ... RESTRICT` sin `CASCADE`. El runner ejecutó el SQL dentro de una transacción, con rollback ante error. La migración **no** figura en `APPROVED_CHECKSUMS`, por lo que no se ejecuta automáticamente mediante Pre-deploy.

`site_group_operator.py` conserva la protección de órdenes históricas **cuando existe** `privacy.correction_plan_order`. Al estar comprobada vacía antes de eliminarla en DEV, no se perdió evidencia de órdenes en ese ambiente. La validación de Billing, entitlements y la autorización por sitio permanece; no trasladar esta conclusión a PROD, donde existen órdenes legadas.

## Límites y próximos pasos

- **Sin restauración ensayada:** el éxito del DDL no demuestra recuperabilidad del respaldo elegido. Si se descubriera un problema posterior, el rollback transaccional ya no aplica; requeriría restauración selectiva y autorizada, sin sobreescribir la BD actual.
- **PROD excluido:** no ejecutar este SQL en PROD ni promover su borrado. La base PROD no tiene las tablas del Plan nuevo; antes de cualquier cambio debe promoverse y validarse el modelo nuevo, definir compatibilidad histórica y un plan de respaldo/restauración específico.
- **PW-04:** siguiente frente en DEV, integración de checkout, confirmación de pago por proveedor, creación de entitlement y validación de punta a punta. No se habilitan pagos reales por documentar este cierre.
- La migración es de **un solo uso**: después de ejecutarla, fallará deliberadamente por ausencia de tablas. Mantener su historial en este documento; no reintentarla.
