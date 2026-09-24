# Mininode Access - Modelo canónico A0

## Objetivo

Access es el nodo transversal que define **quién puede acceder a qué contexto de Mininode**.

A0 establece únicamente el modelo canónico y su persistencia base. No implementa login,
Cloudflare Access, autorización de endpoints, Billing ni una aplicación autenticada.

## Modelo

```text
Usuario
  ↓
Workspace
  ↓
Empresa
  ↓
Sitio
  ↓
Entitlement
```

Un usuario puede pertenecer a uno o más workspaces mediante `workspace_member`.

```text
Usuario ↔ Workspace
```

El mismo modelo sirve tanto para una cuenta directa como para un partner. No existe un
tipo estructural `partner`.

Ejemplo directo:

```text
Workspace Rodrigo
├─ Empresa A
│  ├─ empresa-a.cl
│  └─ tienda-a.cl
└─ Empresa B
   └─ empresa-b.cl
```

Ejemplo partner:

```text
Workspace Surtika
├─ Cliente A
│  └─ cliente-a.cl
├─ Cliente B
│  └─ cliente-b.cl
└─ Cliente C
   └─ cliente-c.cl
```

Las diferencias futuras de partner se expresarán mediante capacidades, no mediante otra
aplicación ni otra jerarquía de datos.

## Entidades

### user

Identidad interna de Mininode.

- `id`: UUID interno y estable.
- `email`: atributo de identidad normalizado a minúsculas; no es la PK.

La identidad externa que entregue Cloudflare Access se mapeará a este registro en A1.

### workspace

Raíz de autorización y cuenta administrativa.

Un workspace puede contener varias empresas y varios usuarios.

### workspace_member

Relaciona usuarios con workspaces.

A0 persiste un campo `role`, pero **no fija todavía el vocabulario ni los permisos de
cada rol**. Esa semántica pertenece a A2.

### company

Empresa administrada dentro de un workspace.

Una empresa siempre pertenece a un solo workspace.

### site

Sitio perteneciente a una empresa.

- `hostname` es la identidad canónica normalizada del sitio.
- `canonical_url` puede conservar la URL pública preferida cuando corresponda.
- un mismo hostname no se duplica dentro de una empresa.

### entitlement

Representa que un producto está habilitado para un sitio durante una vigencia.

Campos base:

- `site_id`;
- `product_code`;
- `active_from`;
- `active_until`;
- `status`;
- `source`;
- `source_id`.

A0 no define todavía el catálogo de estados ni de fuentes. Billing será responsable más
adelante de crear o renovar entitlements a partir de una compra; Access y las
aplicaciones los consumirán para decidir qué producto está habilitado.

## Fronteras

### Access

Responsable de identidad interna, membresía y autorización.

```text
usuario → workspace → empresa → sitio
```

### Entitlement

Responde qué producto está habilitado para el sitio y durante qué período.

### Billing

Será un nodo separado. Un pago confirmado podrá originar o extender un entitlement,
pero Billing no decidirá quién tiene permiso sobre un workspace.

## Seguridad

- La autorización se resolverá siempre en backend.
- El frontend nunca será autoridad para seleccionar un `workspace_id`, `company_id`
  o `site_id`.
- La pertenencia debe demostrarse recorriendo
  `workspace_member → workspace → company → site`.
- Los identificadores son UUID internos; el email no funciona como clave primaria.
- A0 no introduce endpoints públicos ni cambia la autenticación existente por
  `X-Api-Key`.

## Persistencia

El modelo vive en el schema PostgreSQL `access`:

- `access.users`;
- `access.workspaces`;
- `access.workspace_members`;
- `access.companies`;
- `access.sites`;
- `access.entitlements`.

La inicialización es idempotente y se ejecuta de forma independiente durante el startup
del backend. Si Access no puede inicializarse, el resto de servicios puede continuar
siguiendo el patrón de disponibilidad parcial existente.

A0 no migra ni reescribe datos actuales de Privacy Web o Privacy Data.

## Próximas etapas

1. **A1 - Identidad:** Cloudflare Access → usuario interno Mininode.
2. **A2 - Autorización:** resolver membresía y permisos por workspace/empresa/sitio.
3. **A3 - App Privacy Web:** usar el modelo canónico para la aplicación autenticada.
4. **A4 - Billing:** pago confirmado → entitlement.
