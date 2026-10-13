# Mininode Access

## Objetivo

Access es el nodo transversal que define **quién es el usuario y a qué contexto de
Mininode puede acceder**.

El avance se divide así:

- **A0:** modelo canónico y persistencia.
- **A1:** identidad Cloudflare Access → usuario interno Mininode.
- **A1.1:** transición backend a Clerk como identidad cliente, conservando Cloudflare como fallback temporal.
- **A1.2:** UX cliente Clerk con Google o email + código, sin contraseña Mininode.
- **A2:** autorización canónica por workspace.
- **A2.1:** sitio público + relación privada workspace ↔ sitio.
- **A3:** aplicación Privacy Web autenticada.
- **A4:** Billing → entitlement.

## Modelo

```text
Usuario ↔ Workspace
             │
             ↓
       WorkspaceSite
        ↙         ↘
 Empresa          Sitio público
 (opcional)       (hostname)
             │
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

Un workspace puede contener varias empresas, varios usuarios y varios sitios seguidos.

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

Recurso web público observado por Mininode. No declara propiedad ni pertenencia a una empresa.

- `hostname` es la identidad canónica normalizada y global del sitio;
- `canonical_url` puede conservar la URL pública preferida;
- un hostname existe una sola vez en `access.sites`.

### workspace_site

Relación privada entre un workspace y un sitio público.

- dos workspaces pueden seguir independientemente el mismo sitio;
- el mismo sitio no se duplica dentro de un workspace;
- `company_id` es opcional y sirve sólo para agrupar el seguimiento; la BD exige que esa empresa pertenezca al mismo workspace;
- su UUID es la identidad que las aplicaciones usan para autorización e historial.

### entitlement

Representa que un producto está habilitado para una relación workspace-sitio durante una vigencia.

Campos base:

- `workspace_site_id`;
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
usuario → workspace → workspace_site → sitio
```

### Entitlement

Responde qué producto está habilitado para el seguimiento privado `workspace_site` y durante qué período.

### Billing

Billing es un nodo separado y proveedor-independiente. Mantiene órdenes internas con
producto, precio y moneda resueltos por backend; el frontend no decide el monto.

Para Privacy Web, una orden se asocia a `workspace_site` y al diagnóstico elegible que
la originó. La activación solo puede solicitarse dentro de las 24 horas del diagnóstico.

La operación interna `payment_confirmed` recibe una confirmación ya verificada por un
adaptador de pago y crea el entitlement de forma transaccional e idempotente. La vuelta
del navegador desde un checkout nunca concede acceso por sí sola.

La vigencia pagada es un mes calendario desde `paid_at`. Si ya existe una vigencia
activa, una compra anticipada agrega el nuevo mes después de `active_until`, sin perder
días. Solo se permite mantener un período futuro ya pagado: una nueva compra queda
bloqueada hasta que comience ese período. Las fuentes no comerciales (`internal`, `qa`, `demo` y posteriormente
`partner`) pueden crear entitlements sin convertir al proveedor de pago en autoridad
comercial.

A4.1 dejó Billing Core independiente del proveedor. A4.2 integra Mercado Pago Checkout Pro
mediante la Orders API recomendada para integraciones nuevas. Mininode crea la order del
proveedor desde una orden interna ya autorizada, usando el UUID interno como referencia e
idempotency key, y devuelve únicamente el `checkout_url` para redirección en la misma pestaña.

La vuelta del navegador sigue sin activar el producto. El webhook de Mercado Pago valida
`x-signature` mediante HMAC-SHA256 y luego consulta la order directamente a Mercado Pago.
Solo una order vinculada cuyo estado sea `processed/accredited`, moneda CLP y montos
coincidentes puede invocar `payment_confirmed`. Las credenciales
`MERCADOPAGO_ACCESS_TOKEN` y `MERCADOPAGO_WEBHOOK_SECRET` viven exclusivamente como
secretos de entorno; `MININODE_PUBLIC_URL` define las URLs HTTPS de retorno.

A4.2 se valida primero en sandbox/test users. No habilita cobros reales de producción ni
elimina todavía las estructuras comerciales antiguas de Privacy Web.

## Seguridad

- La autenticación y autorización se resuelven en backend.
- El frontend nunca es autoridad para seleccionar un `workspace_id`, `company_id`
  o `site_id`.
- La pertenencia se demuestra recorriendo
  `workspace_member → workspace → workspace_site → site`.
- Los identificadores son UUID internos; el email no funciona como clave primaria.
- `X-Api-Key` no sustituye identidad de usuario.
- Para rutas Access, un `Authorization: Bearer ...` se interpreta exclusivamente
  como sesión Clerk. Si existe y falla, no se intenta autenticar silenciosamente con
  Cloudflare Access.
- Un `workspace_site_id` sólo se acepta cuando `get_authorized_site()` demuestra que el usuario
  pertenece al workspace de ese seguimiento.
- Roles desconocidos quedan fuera de las consultas de autorización y, por tanto, no
  conceden acceso.

## Persistencia

El modelo vive en el schema PostgreSQL `access`:

- `access.users`;
- `access.workspaces`;
- `access.workspace_members`;
- `access.companies`;
- `access.sites`;
- `access.workspace_sites`;
- `access.entitlements`.

La inicialización es idempotente y se ejecuta de forma independiente durante el startup
del backend. Si Access no puede inicializarse, el resto de servicios puede continuar
siguiendo el patrón de disponibilidad parcial existente.

A2.1 no migra ni reescribe datos actuales de Privacy Web o Privacy Data. Como todavía no existen clientes Access, la migración A2.1 reemplaza de forma destructiva únicamente las tablas estructurales `access.sites` y `access.entitlements` y crea `access.workspace_sites`; conserva usuarios, workspaces, membresías y empresas.

## A1 - Identidad Cloudflare Access

Cloudflare Access fue la identidad inicial de `app.mininode.io` y su flujo E2E quedó
validado. La aplicación cliente de Cloudflare Access ya fue retirada de ese dominio;
Clerk es ahora la identidad cliente activa. El soporte backend para el header
`Cf-Access-Jwt-Assertion` se conserva temporalmente como compatibilidad mientras no se
retire explícitamente en una etapa posterior.

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

El backend mantiene temporalmente la compatibilidad de transición:

1. `Authorization: Bearer <Clerk JWT>` tiene prioridad;
2. si no existe Bearer, puede resolver el JWT de Cloudflare Access como fallback;
3. un Bearer inválido **no** cae a Cloudflare;
4. Pages reenvía ambos headers solamente para las rutas protegidas de Access.

La aplicación cliente de Cloudflare Access ya no protege `app.mininode.io`. Clerk es
la identidad de clientes; Cloudflare continúa proporcionando DNS/CDN/Pages/WAF.

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

La integración frontend con Clerk está centralizada en `frontend/assets/js/core-auth.js`,
que expone la abstracción transversal `window.MininodeAuth`. Es la única pieza frontend
que puede cargar/configurar Clerk, observar cambios de sesión, obtener el JWT y cerrar
sesión. Landing, Learn, Contacto, Access, Privacy Web, Privacy Data y futuros productos
consumen ese contrato común; no inicializan Clerk directamente.

Cuando una aplicación necesita autenticarse contra el backend, solicita un token fresco a
`MininodeAuth.getToken()` y lo envía como `Authorization: Bearer ...` a la ruta
protegida correspondiente. Pages lo reenvía al backend y A1.1 verifica firma y claims
antes de resolver el UUID interno de Mininode.

`/access/` conserva únicamente la experiencia visual de ingreso (Google o email + código)
y solicita a `MininodeAuth` montar/desmontar esa UI. La pantalla no decide autorización
de workspace, empresa o sitio. Su objetivo es completar autenticación y mostrar la cuenta.

El E2E de producción quedó validado con ambos métodos: Google y email + código llegan
a `Clerk → Pages → Render → /access/me → access.users`. Ambos métodos resolvieron el
mismo registro interno de usuario, sin duplicar la identidad canónica. Tras esa
validación se retiró la aplicación cliente de Cloudflare Access de `app.mininode.io`.

## A2 - Autorización

A2/A2.1 toman el `user_id` autenticado y resuelven únicamente el contexto privado al que pertenece.

```text
user_id
  ↓
workspace_member
  ↓
workspace
  ↓
workspace_site
  ↓
site público
```

### Contexto autorizado

`GET /access/context` devuelve solamente los workspaces autorizados del usuario y,
dentro de ellos, sus relaciones privadas con sitios. Cada sitio puede incluir `company_id` y `company_name` como agrupación opcional.

Un usuario sin membresías obtiene:

```json
{"workspaces":[]}
```

El endpoint no acepta un workspace, empresa o sitio enviado por frontend para decidir
qué mostrar; el contexto se deriva desde `user_id` en PostgreSQL.

### Guardia por sitio

`get_authorized_site(user_id, workspace_site_id)` recorre en una sola consulta:

```text
workspace_site → site + workspace → workspace_member(user)
```

Si la cadena no existe o el rol no es `owner`/`member`, devuelve `None`.

A3 deberá reutilizar esta función —o una dependencia construida sobre ella— antes de
operar sobre cualquier seguimiento. Dos workspaces pueden apuntar al mismo `site_id` sin compartir autorización, entitlement ni historial.

### Alcance que A2 no cubre

A2 no agrega:

- creación automática de workspaces;
- gestión de miembros;
- permisos específicos por empresa o `workspace_site`;
- diferencias funcionales entre `owner` y `member`;
- UI;
- entitlements ni Billing;
- lógica propia de Privacy Web.

Por ahora, una membresía válida da acceso a todos los `workspace_sites` de ese workspace. `company_id` puede agruparlos, pero no expresa propiedad del sitio.

## A3 - Cuenta Mininode y aplicación de productos

A3 no debe construir un portal aislado de Privacy Web. Access es transversal a Mininode y la experiencia autenticada debe servir también para Privacy Data y futuros productos.

El acceso objetivo es:

```text
mininode.io
  ↓
Acceder
  ↓
Cuenta Mininode
  ↓
Workspace
  ↓
Productos
  ├─ Privacy Web
  ├─ Privacy Data
  └─ futuros SaaS
```

La portada pública puede ofrecer una acción **Acceder**. Clerk autentica una única identidad Mininode; después del acceso, el usuario entra a un home autenticado desde el que ve los productos y servicios disponibles en su workspace.

### Onboarding gratuito

Crear una cuenta no requiere pago. Para el MVP:

- un usuario nuevo puede crear su cuenta Mininode gratuitamente;
- su primer uso puede crear un workspace personal y dejarlo como `owner`;
- puede asociar sitios públicos a su workspace mediante `workspace_site`;
- `company_id` continúa siendo opcional;
- crear cuenta, workspace o `workspace_site` no crea por sí mismo un entitlement.

La cuenta y el workspace son infraestructura transversal de Mininode, no recursos exclusivos de Privacy Web.

### Privacy Web gratuito

Por ahora no se implementan controles antiabuso ni límites de diagnósticos gratuitos.

Un usuario puede:

- ejecutar diagnósticos gratuitos;
- repetir el diagnóstico de un sitio;
- mantener el sitio asociado a su workspace;
- volver posteriormente al sitio y ejecutar un nuevo diagnóstico.

El sitio público `access.sites` no se elimina por falta de pago. Tampoco se considera propiedad del usuario o del workspace.

Sin Privacy Web activo, el producto se comporta como una revisión actual: el usuario no obtiene las capacidades pagadas de continuidad, historial o seguimiento.

### Privacy Web activo

El pago no habilita la identidad ni la propiedad del sitio. Habilita capacidades del producto sobre un `workspace_site`.

La propuesta comercial vigente para Privacy Web activo es un período de un mes, sin renovación automática. Durante la vigencia, las capacidades pagadas incluyen:

- historial de revisiones;
- seguimiento y evolución del sitio;
- colaboración mediante miembros del workspace.

La colaboración es una capacidad comercial pagada, pero `workspace_member` sigue siendo una entidad transversal de Access y no debe acoplarse estructuralmente a Privacy Web. Inicialmente no se define cobro por usuario adicional.

Cuando expire Privacy Web, la cuenta, el workspace y el sitio asociado permanecen. La última revisión continúa disponible según la regla comercial vigente. La política exacta para historial anterior —por ejemplo, conservarlo oculto para una futura reactivación— se definirá con Billing antes de implementarla.

### Entitlement

La separación conceptual es:

```text
Access       → quién es el usuario y a qué workspace/recurso puede acceder
Aplicación   → qué puede hacer gratuitamente
Entitlement  → qué capacidades pagadas están activas para el recurso
Billing      → cómo un pago crea o extiende ese entitlement
```

Para Privacy Web, el entitlement pertenece a `workspace_site`, no a cada usuario. Por ello, cuando un sitio tenga Privacy Web activo, los miembros autorizados del workspace podrán compartir las capacidades habilitadas conforme a las reglas del producto.

A3 puede crear y utilizar un `workspace_site` sin entitlement. A4 será responsable de conectar pago y vigencia con el entitlement.

### Secuencia de implementación A3

1. **A3.1 - Onboarding Access:** workspace personal automático y alta de sitios seguidos. El onboarding es explícito e idempotente: una cuenta autenticada puede crear su primer workspace personal sin pago ni entitlement; si ya pertenece a un workspace válido, se reutiliza y no se crea otro. Un usuario autenticado puede además asociar una URL pública a un workspace autorizado; el hostname se normaliza globalmente y la relación `workspace_site` es idempotente y privada por workspace.
2. **A3.2 - Privacy Web autenticada:** existen dos entradas. Al abrir un sitio ya guardado, el diagnóstico se inicia por `workspace_site_id`; el backend autoriza membership, obtiene la URL desde Access y vincula el snapshot al recurso existente. Al iniciar un diagnóstico nuevo con una URL dentro de un workspace autorizado, el backend inspecciona primero y, si el diagnóstico resulta exitoso, crea o reutiliza automáticamente el `workspace_site` y vincula el snapshot. El usuario no necesita crear el sitio manualmente.
3. **A3.3 - Home Mininode:** entrada autenticada transversal organizada por producto. La jerarquía visible es `producto → recursos del producto`: Privacy Web presenta los sitios ya asociados al workspace; Privacy Data presenta conceptualmente sus mapas y permanece como próximo paso. El home no expone la creación manual de sitios. Los recursos técnicos compartidos de Access no se elevan por sí mismos al primer nivel de navegación.

A3 no incluye Billing, cobros ni creación de entitlements pagados.

### Regla de navegación de Cuenta Mininode

La navegación principal se organiza por **productos**, no por las entidades técnicas de Access. La identidad del usuario se agrupa globalmente bajo **Mi cuenta**: con sesión iniciada, el header expone ese menú como punto de entrada a `/access/` y aloja allí **Cerrar sesión**. El workspace no se trata como una cuenta ni se muestra como navegación global cuando existe uno solo.

Cada producto presenta dentro de su contexto los recursos que el usuario reconoce para trabajar:

```text
Cuenta Mininode
  ├─ Privacy Web
  │    └─ sitios
  ├─ Privacy Data
  │    └─ empresas / mapas
  └─ futuros productos
       └─ sus propios recursos
```

Esto no modifica el modelo de autorización. Un sitio continúa siendo un recurso público global y `workspace_site` continúa siendo la relación privada reutilizable por aplicaciones. La jerarquía de interfaz y la jerarquía técnica se mantienen deliberadamente separadas.

A3.3 reutiliza A3.1 para onboarding y no expone en la cuenta una acción manual para crear sitios. Privacy Web crea o reutiliza automáticamente el `workspace_site` después de un diagnóstico autenticado exitoso. Crear o asociar un `workspace_site` no expresa intención de compra y no crea entitlement. Privacy Web público continúa disponible sin cuenta.

La cuenta muestra para cada sitio, cuando existe, un resumen de su **última revisión Privacy Web** (score, estado y fecha) y permite volver a abrir ese resultado almacenado sin ejecutar una nueva inspección. Esta vista no introduce historial completo ni cambia las reglas comerciales de Privacy Web activo; utiliza el snapshot más reciente ya vinculado al `workspace_site`.

## Próximas etapas

1. **A3 - Cuenta Mininode y aplicaciones:** implementar el flujo autenticado sobre Access.
2. **A4 - Billing:** pago confirmado → entitlement.


## Entornos DEV y PROD

Mininode mantiene separados los recursos de validación y producción:

```text
DEV
dev.mininode.io
  → rama dev / Cloudflare Preview
  → mininode-backend-dev
  → mininode-db-dev
  → Clerk Development

PROD
app.mininode.io
  → main / Cloudflare Production
  → mininode-backend-prod
  → PostgreSQL producción
  → Clerk Production
```

Las migraciones SQL son explícitas y controladas. Producción usa el environment de
GitHub `production` y el secret `PRODUCTION_DATABASE_URL`; DEV usa el environment
`development` y el secret `DEVELOPMENT_DATABASE_URL`. Ambos workflows exigen el
nombre exacto de un archivo en `backend/migrations` y una confirmación propia del
entorno. El workflow DEV ejecuta la migración contra el contenido de la rama permanente
`dev`; no reutiliza credenciales ni confirmaciones de producción.
