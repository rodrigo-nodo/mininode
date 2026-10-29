# PW-03C3 — Preparación de limpieza física DEV (sin ejecutar)

**Estado:** migración propuesta en PR; ninguna eliminación autorizada ni ejecutada.
**Alcance exclusivo:** Render DEV, PostgreSQL `mininode_db_dev`.
**PROD:** fuera de alcance; `main` todavía inicializa y consulta el flujo antiguo.

## Evidencia previa (29-oct-2026)

| Relación | DEV (consulta interna) | PROD (consulta read-only) |
|---|---:|---:|
| `privacy.correction_plan` | 0 | 2 |
| `privacy.correction_plan_order` | 0 | 3 |
| `privacy.correction_plan_check` | 0 | 1 |
| `privacy.entitled_plan` | 3 | No existe |
| `privacy.entitled_plan_check` | 3 | No existe |

PROD: dos órdenes antiguas marcadas `paid` y una `pending_payment`; una revisión histórica. No suponer cobros reales. Los registros y dependencias comerciales se conservan. Los snapshots en `privacy.diagnostic` no se eliminan.

## Código y dependencias

- En `dev` el backend del modelo comercial antiguo ya fue retirado (PW-03C2); la migración preparada no lo restaura.
- `site_group_operator.py` conserva intencionalmente el control de órdenes antiguas: lee/retiene un candado de `privacy.correction_plan_order` **si existe**. Si la migración elimina tablas verificadas vacías, el control no pierde ninguna orden histórica; sigue comprobando Billing y entitlements.
- En `main` el backend aún usa las tablas antiguas, por lo tanto **no aplicar este retiro ni promoverlo a PROD**.
- El modelo nuevo, `privacy.diagnostic`, Access y Billing quedan fuera de la limpieza.

## Archivo preparado, deshabilitado por defecto

`backend/migrations/20261029_pw03c3_retire_legacy_dev.sql`:

1. Exige el nombre exacto de BD `mininode_db_dev`; en otras bases falla.
2. Exige las tres tablas legadas y las dos tablas del Plan nuevo.
3. Bloquea las tres tablas `ACCESS EXCLUSIVE ... NOWAIT` **antes** de consultar registros; falla ante actividad concurrente.
4. Rechaza la operación si **cualquier tabla** contiene un solo registro.
5. Usa `DROP TABLE ... RESTRICT`, **sin CASCADE**: una dependencia inesperada cancela toda la transacción.

No está registrado en `APPROVED_CHECKSUMS`; Render Pre-deploy no puede ejecutarlo por allowlist. Su mera presencia en `dev` **no aplica DDL**.

## Checklist antes de una ejecución futura (otra autorización)

1. Confirmar SHA de `dev` y Render DEV en servicio, y que el backend antiguo no se ejecute en ese ambiente.
2. Volver a inspeccionar **en la sesión de ejecución**, mediante solo lectura, las cinco tablas, filas y referencias; no confiar únicamente en las cifras del 29-oct.
3. Preparar **respaldo/exportación verificable** de la estructura, constraints, índices y cualquier contenido de las tres tablas, en almacenamiento protegido. Verificar recuperación en una BD aislada (restore de prueba). No suponer que el plan básico de Render ofrece PITR.
4. Revisar dependencias de claves foráneas, vistas, funciones, permisos y procesos externos; comprobar especialmente la guarda `site_group_operator.py`.
5. Obtener **autorización explícita separada** para ejecutar la migración DEV. Elegir exclusivamente el workflow manual `Development DB Migration`, con secreto del entorno development y confirmación consciente. No ejecutar en PROD, desde Shell ni mediante predeploy automático como parte de este PR.
6. Tras ejecutar, comprobar ausencia exclusiva de las tres tablas, integridad de `privacy.diagnostic`, `entitled_plan` y `entitled_plan_check`, y flujo de agrupación/Billing/Plan en DEV.

**Rollback:** si falla cualquier verificación SQL, la transacción revierte y no se elimina tabla alguna. Si el DDL terminara correctamente y se detectara después un problema, no existe un down-migration que regenere evidencia. Restaurar **únicamente** las tres tablas desde el respaldo probado en un entorno aislado y con nueva autorización, respetando claves foráneas e historial; no restaurar toda la BD sobre datos nuevos. Sin respaldo comprobado, **no ejecutar**.

## Decisión pendiente

Este PR **solo prepara** el archivo y sus pruebas: no cambia la guarda actual, no registra la migración para Pre-deploy, no toca datos y no autoriza ejecución. El paso siguiente es validar el runbook, verificar respaldos y decidir una operación separada sobre DEV.
