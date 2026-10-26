# Privacy Web - Promoción funcional DEV → MAIN (26 octubre 2026)

## Objetivo

Publicar selectivamente las funcionalidades de Privacy Web probadas en DEV sobre la fuente técnica `main`, conservando Content Reader V1, el resto de productos, la API pública existente y las garantías de seguridad.

## Incluido

- Guardado gratuito del diagnóstico anónimo tras sesión Clerk, con prueba temporal, selección de workspace y confirmación de resultado.
- UX de resultados anónimos/guardados, sitios asociados y última revisión; desasignación lógica con protección de prestaciones activas/compras pendientes.
- Identidad lógica y aliases mediante evidencia pública HTTPS; verificación conservadora de redirecciones sin equivalencia por similitud.
- Revisión solicitada por el usuario y decisión **manual** y auditada de un operador autorizado para agrupar sitios.
- Mininode Admin `/admin/`, cortesías gratuitas `source=internal_grant`, revocación y auditoría, sin simular pagos.
- Tests de API, PostgreSQL, inspector, proxy y UI; documentación del contrato.

## Conservado y fuera de alcance

- Content Reader V1 y sus workflows y tests: no se modifican.
- Las siete migraciones A/B de PROD ya fueron ejecutadas previamente y sus checksums verificados. Este PR no incluye SQL ni modifica Render.
- No se habilita checkout ni webhook Mercado Pago en `main`. El archivo `api/billing.py` existente conserva sus rutas sin cobros reales.
- No se ejecuta `reconcile_existing_www.py --apply` ni conciliación masiva; el análisis de sitios existentes requiere decisión posterior.
- Se preservan los snapshots y órdenes históricas (`privacy.correction_plan_order`); la transición al recorrido comercial único será un trabajo separado, no una migración destructiva implícita.
- Los cambios de controles/scoring no forman parte de esta promoción: sin cambios en `controls.json` ni `scoring.json`.
- No se copia `render.yaml` antiguo de DEV.

## Operación y seguridad

La autorización de operador usa `MININODE_REVIEW_OPERATOR_EMAILS` verificado por backend; sin configuración, la administración no debe conceder acceso. La URL por defecto en las notificaciones administrativas apunta a `https://mininode.io/admin/` y puede ajustarse con `MININODE_REVIEW_PANEL_URL`.

El envío de notificaciones solo sucede tras una solicitud explícita del usuario, si existen credenciales/configuración operativa. El servicio de diagnóstico conserva su política de inspección pública y SSRF protegido. La asociación y los entitlements siguen siendo particulares de cada workspace, no del hostname global.

## Validación previa al merge

1. CI del último SHA, incluyendo pruebas nuevas PostgreSQL 18, SSRF, APIs, accesos y frontend.
2. Branch Preview del último commit: recorrido anónimo gratuito → iniciar sesión → guardar → Mis sitios; sitio ya guardado; desvinculación.
3. Acceso al panel Admin sin rol: denegado. Con un operador autorizado en entorno de validación: búsqueda de sitios y concesión/revocación de prueba, sin tocar datos PROD.
4. Confirmar que las pantallas comerciales informan que el pago en línea todavía no está disponible.
5. Reviewer independiente para backend/seguridad/contratos; no merge sin autorización del PO.

Tras merge, validar despliegues de Cloudflare y Render del commit de `main` y confirmar que las migraciones no se reaplican (`MIGRATION_APPROVED_FILES` vacío).
