# QA A4.2 - Mercado Pago DEV

## Objetivo
Validar orden Mininode → checkout de prueba → webhook firmado → acceso Privacy Web por un mes. No realizar cobros reales.

## Fase A - Automatizada (ya existe en CI)
Los tests `backend/tests/test_billing_core.py` usan PostgreSQL aislado de CI y verifican órdenes, acceso, vigencia e idempotencia. Los tests `backend/tests/test_mercadopago_adapter.py` simulan la API de Mercado Pago y verifican firma, payload, acreditación y rechazo de inconsistencias. **No equivalen a un E2E real.** Nunca ejecutar los fixtures de Billing contra DEV o producción: eliminan esquemas.

## Fase B - E2E sandbox real (pendiente)
Precondiciones: Render DEV Live; credenciales y webhook de pruebas configurados; comprador de prueba distinto del vendedor; diagnóstico vigente asociado a workspace/site de prueba y usuario autenticado en DEV. No usar medios de pago reales.

1. Crear orden por `POST /billing/orders` con `workspace_site_id` y `diagnostic_id` válidos. PASS: CLP 9900 y estado pending.
2. Solicitar `POST /billing/orders/{id}/checkout`. PASS: URL HTTPS de Checkout Mercado Pago y referencia a la orden creada.
3. Completar checkout con comprador y medio de pago de prueba. PASS: no hay cargo real.
4. Comprobar webhook tipo `order` con firma válida y verificación del estado por la API de Mercado Pago.
5. Consultar `GET /billing/orders/{id}` y `GET /billing/sites/{workspace_site_id}/entitlement`. PASS: orden paid, entitlement activo un mes.
6. Reenviar webhook; PASS: no se duplica el acceso.
7. En orden separada, comprobar pago pendiente/rechazado y firma inválida; PASS: no se activa acceso.

## Criterios
PASS solo con las siete verificaciones; NEEDS FIX si falla cualquiera. Conservar IDs y evidencias no sensibles; no guardar tokens, claves ni datos personales en repositorio o logs.

## Límite actual
El backend no tiene una pantalla de compra integrada. La fase B requiere crear una orden desde un usuario autenticado con un diagnóstico DEV elegible. No exponer endpoints de QA ni sembrar datos falsos en DEV para evitar esta precondición.
