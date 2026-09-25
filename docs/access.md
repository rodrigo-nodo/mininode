# Mininode Access

## Objetivo

Access es el nodo transversal que define **quién es el usuario y a qué contexto de
Mininode puede acceder**.

El avance se divide así:

- **A0:** modelo canónico y persistencia.
- **A1:** identidad Cloudflare Access → usuario interno Mininode.
- **A1.1:** transición backend a Clerk como identidad cliente, conservando Cloudflare como fallback temporal.
- **A1.2:** UX cliente Clerk con Google o email + código, sin contraseña Mininode.
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

La capa de identidad mapea una identidad verificada de Cloudflare Access o Clerk a este registro. El UUID interno permanece estable y el email es un atributo normalizado, no la clave de negocio.

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
- Para rutas Access, un `Authorization: Bearer ...` se interpreta exclusivamente
  como sesión Clerk. Si existe y falla, no se intenta autenticar silenciosamente con
  Cloudflare Access.
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

## A1.1 - Transición a Clerk

Para la experiencia cliente se decidió separar la autenticación visual de la capa
Cloudflare. La arquitectura objetivo es:

```text
UX Mininode
  ↓
Clerk (email + OTP + sesión)
  ↓
JWT Clerk
  ↓
Pages
  ↓
Backend Mininode
  ↓
access.users
  ↓
A2
```

Clerk gestiona generación/envío/verificación del OTP y la sesión. Mininode controla la
UX y nunca valida el código OTP por su cuenta.

El backend verifica el JWT Clerk criptográficamente mediante el JWKS público de la
instancia y exige:

- firma RS256 válida;
- issuer configurado;
- `exp`, `nbf`, `iss` y `sub`;
- `azp` perteneciente a la lista explícita de orígenes autorizados;
- sesión no pendiente;
- claim `email` presente y no vacío.

Configuración backend:

- `CLERK_ISSUER`: Frontend API URL HTTPS de la instancia Clerk;
- `CLERK_AUTHORIZED_PARTIES`: orígenes HTTPS permitidos, separados por coma.

El claim `email` se agrega al token estándar `__session` desde la configuración de
Clerk. No se necesita `CLERK_SECRET_KEY` para esta validación.

Durante la migración:

1. `Authorization: Bearer <Clerk JWT>` tiene prioridad;
2. si no existe Bearer, se mantiene el JWT de Cloudflare Access como fallback;
3. un Bearer inválido **no** cae a Cloudflare;
4. Pages reenvía ambos headers solamente para las rutas protegidas de Access;
5. Cloudflare Access continúa activo hasta completar y validar E2E la nueva UX.

El objetivo posterior es usar Clerk para identidad de clientes y reservar Cloudflare
Access para herramientas internas si sigue siendo útil.

## A1.2 - UX cliente Clerk

La experiencia cliente de acceso vive en `/access/`. `app.mininode.io` deriva a esa
ruta mientras el sitio público `mininode.io` conserva su landing actual.

La interfaz utiliza los componentes de autenticación de Clerk con apariencia Mininode.
Las alternativas del MVP son:

- Google, cuando la conexión social esté habilitada en Clerk;
- email + código de verificación;
- sin contraseña propia de Mininode.

La Publishable Key de Clerk puede estar en el frontend. No se utiliza ni se expone
`CLERK_SECRET_KEY`.

Cuando Clerk crea una sesión, el navegador obtiene el JWT mediante
`session.getToken()` y lo envía como `Authorization: Bearer ...` únicamente a
`/api/access/me`. Pages lo reenvía al backend y A1.1 verifica la firma y claims antes
de resolver el UUID interno de Mininode.

La pantalla de acceso no decide autorización de workspace, empresa o sitio. Su único
objetivo es completar autenticación y confirmar que Mininode reconoce la identidad.

Cloudflare Access sigue delante de `app.mininode.io` durante esta etapa. Se retira del
flujo cliente sólo después de validar E2E Clerk → Pages → Render → `access.users`.

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

1. **Validación E2E Clerk:** validar Google y email + código contra
   `Clerk → /api/access/me → mismo access.users`.
2. **Retiro de Cloudflare Access cliente:** sólo después del E2E, manteniendo
   Cloudflare DNS/CDN/Pages/WAF.
3. **A3 - App Privacy Web:** usar identidad y autorización canónicas.
4. **A4 - Billing:** pago confirmado → entitlement.
