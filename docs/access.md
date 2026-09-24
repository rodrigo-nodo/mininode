# Mininode Access

## Objetivo

Access es el nodo transversal que define **quién es el usuario y a qué contexto de
Mininode puede acceder**.

El avance se divide así:

- **A0:** modelo canónico y persistencia.
- **A1:** identidad Cloudflare Access → usuario interno Mininode.
- **A2:** autorización por workspace → empresa → sitio.
- **A3:** aplicación Privacy Web autenticada.
- **A4:** Billing → entitlement.

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
tipo estructural `partner`; las diferencias futuras se expresarán mediante capacidades.

## Entidades

### user

Identidad interna de Mininode.

- `id`: UUID interno y estable.
- `email`: atributo normalizado a minúsculas; no es la PK.

A1 mapea la identidad verificada de Cloudflare Access a este registro.

### workspace

Raíz de autorización y cuenta administrativa.

Un workspace puede contener varias empresas y varios usuarios.

### workspace_member

Relaciona usuarios con workspaces.

A2 reconoce inicialmente dos roles:

- `owner`;
- `member`.

En A2 ambos roles autorizan acceso al contexto completo del workspace. La diferencia
entre ellos queda reservada para futuras acciones administrativas.

Los valores de rol no reconocidos **no otorgan autorización**. A2 no introduce todavía
endpoints para crear o administrar membresías.

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

Billing será responsable más adelante de crear o renovar entitlements a partir de una
compra. Access y las aplicaciones los consumirán para decidir qué producto está
habilitado.

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

- La autenticación y autorización se resuelven en backend.
- El frontend nunca es autoridad para seleccionar un `workspace_id`, `company_id`
  o `site_id`.
- La pertenencia se demuestra recorriendo
  `workspace_member → workspace → company → site`.
- Los identificadores son UUID internos; el email no funciona como clave primaria.
- `X-Api-Key` no sustituye identidad de usuario.
- Un `site_id` sólo se acepta cuando `get_authorized_site()` demuestra que el usuario
  pertenece al workspace del sitio.
- Roles desconocidos quedan fuera de las consultas de autorización y, por tanto, no
  conceden acceso.

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

Access no migra ni reescribe datos actuales de Privacy Web o Privacy Data.

## A1 - Identidad Cloudflare Access

`app.mininode.io` está protegido externamente por Cloudflare Access. Cloudflare añade
un JWT de aplicación al header `Cf-Access-Jwt-Assertion`.

El backend requiere:

- `CF_ACCESS_TEAM_DOMAIN`: issuer HTTPS del equipo de Cloudflare Access;
- `CF_ACCESS_AUD`: Application Audience (AUD) de la aplicación protegida.

La resolución de usuario autenticado está centralizada en
`mininode_api.core.access_auth.require_access_user`. Ese componente:

1. exige que Access esté disponible;
2. valida criptográficamente el JWT;
3. valida issuer y audience;
4. exige un token de aplicación con email;
5. normaliza el email;
6. crea o recupera `access.users`.

`GET /access/me` devuelve solamente `user_id` y `email`.

El flujo A1 fue validado E2E en producción mediante
`app.mininode.io → Cloudflare Access → Pages → Render → access.users`.

## A2 - Autorización

A2 toma el `user_id` autenticado y resuelve únicamente el contexto al que pertenece.

```text
user_id
  ↓
workspace_member
  ↓
workspace
  ↓
company
  ↓
site
```

### Contexto autorizado

`GET /access/context` devuelve solamente los workspaces autorizados del usuario y,
dentro de ellos, sus empresas y sitios.

Un usuario sin membresías obtiene:

```json
{"workspaces":[]}
```

El endpoint no acepta un workspace, empresa o sitio enviado por frontend para decidir
qué mostrar; el contexto se deriva desde `user_id` en PostgreSQL.

### Guardia por sitio

`get_authorized_site(user_id, site_id)` recorre en una sola consulta:

```text
site → company → workspace → workspace_member(user)
```

Si la cadena no existe o el rol no es `owner`/`member`, devuelve `None`.

A3 deberá reutilizar esta función —o una dependencia construida sobre ella— antes de
operar sobre cualquier recurso asociado a un sitio.

### Alcance que A2 no cubre

A2 no agrega:

- creación automática de workspaces;
- gestión de miembros;
- permisos específicos por empresa o sitio;
- diferencias funcionales entre `owner` y `member`;
- UI;
- entitlements ni Billing;
- lógica propia de Privacy Web.

Por ahora, una membresía válida da acceso a todas las empresas y sitios de ese
workspace.

## Próximas etapas

1. **A3 - App Privacy Web:** usar identidad y autorización canónicas.
2. **A4 - Billing:** pago confirmado → entitlement.
