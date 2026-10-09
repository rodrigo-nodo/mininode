# Mininode Billing - A4.1

Billing registra pedidos comerciales sin depender del proveedor de pagos. Access sigue siendo la autoridad de autorización sobre workspace_site y mantiene los entitlements.

## Contrato inicial

- Producto: `privacy_web`; precio fijado por backend: CLP $9.900.
- `billing.orders`: pedido vinculado a `workspace_site_id` y a un diagnóstico de Privacy Web con ventana de compra vigente (24 horas).
- Estados: `pending`, `paid`, `failed`, `cancelled`.
- `payment_confirmed` es una operación interna para adaptadores de pago **que ya verificaron el pago**; no se expone como endpoint público.
- La confirmación crea `access.entitlements` con `source=payment` y `source_id=order.id`, en la misma transacción que marca el pedido pagado.
- Una repetición de la confirmación con igual referencia devuelve el mismo entitlement; una referencia diferente se rechaza.
- La duración es un mes calendario, no 30 días. Si se confirma otro pedido mientras hay vigencia, se agrega un mes desde el vencimiento vigente.
- `active_until` determina expiración efectiva; no requiere un proceso que cambie el estado a `expired`.
- No hay checkout, webhook ni cobros reales en A4.1. El frontend tampoco recibe aún un flujo de compra.

## Siguiente fase

A4.2: Mercado Pago Sandbox, firma y verificación de webhook, estados de pagos, rutas autenticadas de consulta y checkout, QA extremo a extremo. Ninguna redirección del navegador autoriza un entitlement.
