# Mininode — Roadmap estratégico transversal

**Actualizado:** 30-10-2026  
**Referencia oficial:** este archivo en `main` (`docs/roadmap.md`). La versión de `dev` debe ser una réplica textual, sin decisiones estratégicas propias.  
**Estado:** iniciativas registradas; no equivalen a implementaciones aprobadas.

Este roadmap contiene prioridades **independientes de la rama y el ambiente**. El seguimiento técnico DEV/PROD y las evidencias de cada producto permanecen en sus documentos específicos, por ejemplo [Privacy Web](privacy-web/roadmap.md).

## Iniciativas

| ID | Ámbito | Iniciativa | Estado | Momento |
|---|---|---|---|---|
| MIN-01 | Plataforma / calidad | Evaluar preproducción estable `qa.mininode.io` para validar el SHA candidato a PROD | **Por definir** | Tras estabilizar PW-03; priorizar según frecuencia de releases |
| MIN-02 | Gobierno / propiedad intelectual | Decidir política de repositorio público/privado y eventual separación de código abierto/propietario | **Por definir** | Antes de escalar pilotos, partners y distribución |
| PW-22 | Privacy Web / negocio | Definir tarifas según la superficie web efectivamente evaluada, con entrada simple y volumen multisitio | **Por definir** | Medir en pilotos antes de aprobar nuevas tarifas |

### MIN-01 — Entorno QA / preproducción

**Problema:** `dev.mininode.io` valida integración de cambios en `dev`, pero no necesariamente el SHA exacto del PR construido sobre `main`. Un preview `*.pages.dev` por sí solo tampoco valida Clerk ni el backend PROD.

**Evaluar:** dominio estable `qa.mininode.io`, despliegue de un candidato congelado en SHA, Clerk y orígenes autorizados explícitamente, backend/BD compatibles, aislamiento de datos de prueba, costos, criterios PASS, trazabilidad y rollback. Comparar QA completo frente a QA liviano. No conectar escrituras a PostgreSQL PROD sin autorización expresa.

**Pendiente decidir:** arquitectura, identidad, infraestructura exclusiva o compartida, presupuesto y prioridad. No se crea el dominio ni se cambian configuraciones por añadirlo al roadmap. No bloquear automáticamente PW-03 por esta iniciativa.

**Criterio de cierre:** capacidad de probar el SHA candidato, autenticación y recorrido E2E en un entorno configurado y autorizado, documentando diferencias con PROD.

### MIN-02 — Visibilidad del repositorio

**Situación verificada:** `rodrigo-nodo/mininode` es público (30-10-2026).

**Evaluar:** mantenerlo público, privatizarlo o separar un repositorio público de portafolio/documentación/componentes seleccionados y uno privado para lógica comercial y propiedad intelectual. Revisar licencias existentes, dependencias, forks/historial público, secretos, CI/CD, colaboradores, acceso de partners, costos y mantenimiento.

**No decidido:** ningún cambio de visibilidad ni partición de repositorios. Un cambio a privado no elimina copias o accesos históricos. Evitar secretos y datos personales en ambas modalidades. Cualquier cambio requiere plan de continuidad y aprobación expresa.

### PW-22 — Precio según superficie del sitio

**Hipótesis:** la cobertura, esfuerzo y costo de Privacy Web pueden variar con el tamaño de la superficie observable. El número total de URLs del dominio no equivale a las páginas **efectivamente inspeccionadas**.

**Variables a medir:** páginas únicas evaluadas, profundidad y límites de recorrido, formularios/secciones relevantes, dominios y subdominios, frecuencia de revisiones y costos por revisión. Distinguir tarifa por sitio de descuentos por volumen de sitios para instituciones y partners, sin recargo basado exclusivamente en ser municipio o empresa.

**Referencia comercial actual:** CLP $9.900 por sitio por mes calendario, sin renovación automática. No se aprueban tarifas nuevas con este roadmap.

**Antes de decidir:** probar sitios representativos pequeños/medianos/grandes, cuantificar cobertura y costos, proponer umbrales/planes claros, mantener un precio base simple y declarar límites al cliente. No modificar Billing, entitlements, contratos o cobros sin decisión posterior.

## Gobierno MAIN / DEV

- **Estrategia única:** este archivo en `main` es la referencia oficial; `dev` contiene una **copia idéntica**. Primero se aprueban/mergean cambios estratégicos a `main` y luego se sincronizan por PR documental enfocado hacia `dev`, sin merge masivo de ramas.
- **Seguimiento por entorno:** los roadmaps de ejecución y sus estados en DEV/PROD pueden diferir porque describen hechos distintos. No reemplazar `docs/privacy-web/roadmap.md` de una rama por el de otra; conciliar decisiones y conservar evidencias propias.
- **Página pública:** `frontend/roadmap/index.html` es una pieza editorial diferente, no un espejo automático de este documento ni anuncio de funciones pendientes.
- **Estados:** `Por definir` (hipótesis registrada), `Planificado` (alcance aprobado), `En curso`, `Validado` y `Publicado`. Las iniciativas aquí siguen **Por definir**.
