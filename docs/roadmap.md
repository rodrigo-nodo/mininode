# Mininode — Roadmap estratégico transversal

**Actualizado:** 04-11-2026  
**Referencia oficial:** únicamente este archivo en `main` (`docs/roadmap.md`). DEV enlaza esta referencia y mantiene separados sus documentos de ejecución.  
**Estado:** iniciativas registradas; no equivalen a implementaciones aprobadas.

Este roadmap contiene prioridades **independientes de la rama y el ambiente**. El seguimiento técnico DEV/PROD y las evidencias de cada producto permanecen en sus documentos específicos, por ejemplo [Privacy Web](privacy-web/roadmap.md).

## Iniciativas

| ID | Ámbito | Iniciativa | Estado | Momento |
|---|---|---|---|---|
| MIN-01 | Plataforma / calidad | Evaluar preproducción integrada `preview.mininode.io` para validar el SHA candidato a PROD | **Por definir** | Al terminar desarrollos pendientes de Privacy Web, antes de pilotos o ventas |
| MIN-02 | Gobierno / propiedad intelectual | Modelo híbrido: producto comercial privado y presencia pública selectiva | **Política aprobada; transición pendiente** | Antes de escalar pilotos, partners y distribución |
| PW-22 | Privacy Web / negocio | Definir tarifas según la superficie web efectivamente evaluada, con entrada simple y volumen multisitio | **Por definir** | Medir en pilotos antes de aprobar nuevas tarifas |

### MIN-01 — Entorno QA / preproducción

**Problema:** `dev.mininode.io` valida integración de cambios en `dev`, pero no necesariamente el SHA exacto del PR construido sobre `main`. Un preview `*.pages.dev` por sí solo tampoco valida Clerk ni el backend PROD.

**Evaluar:** dominio estable `preview.mininode.io`, despliegue de un candidato congelado en SHA, Clerk y orígenes autorizados explícitamente, backend/BD compatibles, aislamiento de datos de prueba, costos, criterios PASS, trazabilidad y rollback. Comparar QA completo frente a QA liviano. No conectar escrituras a PostgreSQL PROD sin autorización expresa.

**Secuencia aprobada:** no crear el dominio ni modificar infraestructura mientras queden desarrollos pendientes de Privacy Web. Definir e implementar PREVIEW al cerrar esos desarrollos, **antes de pilotos o ventas**. Arquitectura, identidad, aislamiento, presupuesto y criterios de QA aún requieren aprobación específica.

**Criterio de cierre:** capacidad de probar el SHA candidato, autenticación y recorrido E2E en un entorno configurado y autorizado, documentando diferencias con PROD.

### MIN-02 — Visibilidad del repositorio

**Situación verificada (03-11-2026):** `rodrigo-nodo/mininode` es público; el archivo `LICENSE` de `main` contiene licencia MIT y aviso de copyright 2025 a nombre de Rodrigo.

**Política de producto aprobada:** adoptar el modelo **híbrido**, con desarrollo comercial futuro de Privacy Web, Privacy Data, Capture, Access, Billing y lógica de scoring en repositorio privado; mantener presencia pública para portafolio, documentación seleccionada y componentes publicables bajo licencia expresa, según [política de código y licencias](code-visibility-license-policy.md).

**Límite legal y técnico:** la decisión **no elimina ni revoca** derechos MIT sobre copias y versiones ya publicadas bajo esa licencia; un repositorio privado no protege contenido ya distribuido. No basta con quitar `LICENSE` o cambiar un permiso. Revisar titularidad y condiciones de aportes antes de declarar nuevos módulos propietarios. La empresa debe proteger secretos y datos personales sin depender de la visibilidad.

**Transición pendiente de aprobación operativa:** inventario de licencias y dependencias, historial/forks, revisión de derechos y titularidad, nueva estructura de repositorios, CI/CD, Cloudflare/Render, colaboradores y costos. **No se autoriza por este roadmap** cambiar visibilidad, mover código, transferir titularidad, cambiar la licencia MIT vigente ni modificar despliegues; cada operación tendrá alcance, pruebas y autorización específicos.

### PW-22 — Precio según superficie del sitio

**Hipótesis:** la cobertura, esfuerzo y costo de Privacy Web pueden variar con el tamaño de la superficie observable. El número total de URLs del dominio no equivale a las páginas **efectivamente inspeccionadas**.

**Variables a medir:** páginas únicas evaluadas, profundidad y límites de recorrido, formularios/secciones relevantes, dominios y subdominios, frecuencia de revisiones y costos por revisión. Distinguir tarifa por sitio de descuentos por volumen de sitios para instituciones y partners, sin recargo basado exclusivamente en ser municipio o empresa.

**Referencia comercial actual:** CLP $9.900 por sitio por mes calendario, sin renovación automática. No se aprueban tarifas nuevas con este roadmap.

**Antes de decidir:** probar sitios representativos pequeños/medianos/grandes, cuantificar cobertura y costos, proponer umbrales/planes claros, mantener un precio base simple y declarar límites al cliente. No modificar Billing, entitlements, contratos o cobros sin decisión posterior.

## Gobierno MAIN / DEV

- **Estrategia única:** este archivo existe únicamente en `main`. Los documentos de DEV deben enlazarlo sin replicar el roadmap estratégico. Retirar la copia histórica de DEV mediante un PR documental independiente, revisando referencias y tests, sin arrastrar otros cambios entre ramas.
- **Seguimiento por entorno:** los roadmaps de ejecución y sus estados en DEV/PROD pueden diferir porque describen hechos distintos. No reemplazar `docs/privacy-web/roadmap.md` de una rama por el de otra; conciliar decisiones y conservar evidencias propias.
- **Página pública:** `frontend/roadmap/index.html` es una pieza editorial diferente, no un espejo automático de este documento ni anuncio de funciones pendientes.
- **Estados:** `Por definir` (hipótesis registrada), `Planificado` (alcance aprobado), `En curso`, `Validado` y `Publicado`. MIN-01 y PW-22 siguen **Por definir**; MIN-02 tiene política híbrida aprobada y ejecución de transición pendiente.
