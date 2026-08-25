# Mininode - Guía de trabajo para agentes de código

## Propósito

Mininode se desarrolla mediante cambios pequeños, revisables y reversibles. Las Issues en lenguaje natural definen la tarea y el agente debe realizar el cambio mínimo necesario para cumplirlas.

## Jerarquía de contexto

Usar el contexto en este orden y detenerse cuando exista información suficiente para implementar con seguridad:

```text
Issue
  -> AGENTS.md
  -> documento específico del producto
  -> docs/architecture.md solo si hace falta contexto general
  -> código y pruebas directamente relacionados
```

No leer todos los documentos ni recorrer todo el repositorio por defecto.

## Flujo de trabajo

1. Leer este archivo y completamente la Issue.
2. Identificar el producto o área afectada.
3. Leer el documento específico de ese producto cuando exista.
4. Consultar `docs/architecture.md` solo si la tarea necesita contexto general de Mininode.
5. Revisar primero los archivos de código y pruebas directamente relacionados.
6. Ampliar la exploración solo si imports, llamadas, pruebas o errores lo requieren.
7. Implementar y ejecutar las pruebas relevantes.
8. Dejar commit, push y creación del Pull Request a la automatización.

## Contexto disponible

- `docs/architecture.md` - contexto general y arquitectura estable de Mininode: plataforma, dominios, frontend/backend, despliegue y estructura general.
- `docs/privacy.md` - contexto específico de Mininode Privacy y Privacy Web Inspector.
- `docs/UI.md` - reglas UX/UI y referencia de tokens y componentes para interfaces frontend.

La Issue determina qué contexto es necesario.

## Mapa básico del repositorio

- `frontend/` - HTML/CSS/JavaScript y código frontend servido mediante Cloudflare Pages.
- `backend/` - backend Python/FastAPI desplegado en Render.
- `.github/workflows/` - automatización GitHub Actions. No modificar salvo que la Issue lo solicite explícitamente.
- `docs/` - contexto estable de arquitectura y productos.

## Enrutamiento de contexto

- Tarea general de arquitectura, infraestructura o integración Mininode -> leer `docs/architecture.md`.
- Mininode Privacy / Privacy Web Inspector -> leer `docs/privacy.md`; leer `docs/architecture.md` solo si la tarea necesita contexto general adicional.
- Tarea que cree o modifique interfaz frontend, página, componente visual o estilos -> leer `docs/UI.md` antes de implementar.
- Otras áreas -> usar la Issue y revisar únicamente el código relacionado, salvo que se indique otro documento de contexto.

## Reglas

- Preferir cambios pequeños y reversibles.
- No inventariar ni resumir todo el repositorio salvo que la Issue solicite explícitamente un análisis de arquitectura/repositorio.
- No leer documentación de productos no relacionados solo como contexto general.
- Tratar los hechos y diagnósticos entregados en la Issue como información ya investigada por ChatGPT/revisión humana; no redescubrirlos salvo que sea necesario validarlos para implementar con seguridad.
- Mantener la arquitectura y convenciones existentes.
- Ejecutar primero pruebas focalizadas; ampliar las pruebas cuando la superficie afectada lo requiera.
- No debilitar controles de seguridad salvo que la Issue solicite explícitamente un cambio de seguridad revisado.
- No modificar workflows, infraestructura, secrets, configuración de despliegue, base de datos, autenticación o pagos salvo que estén explícitamente dentro del alcance.

## Mantenimiento del contexto

Si una implementación cambia una decisión estable de arquitectura, producto, seguridad o comportamiento que será relevante para trabajos futuros, actualizar en el mismo cambio el documento correspondiente (`docs/architecture.md`, `docs/privacy.md` u otro documento específico).

No usar estos documentos como historial de Pull Requests. Deben describir cómo funciona y debe entenderse Mininode en su estado actual.

## Convención para MVP frontend-only

Para un MVP estático pequeño, preferir:

```text
frontend/<nombre_mvp>/index.html
```

Partir frontend-only cuando la Issue no requiera capacidades backend.

## Calidad del resultado

El resultado debe permitir responder fácilmente:

- ¿Qué cambió?
- ¿Por qué era necesario?
- ¿Cómo se probó?
- ¿Qué archivos cambiaron?
- ¿Cambió algo fuera del alcance de la Issue?

La aprobación y el merge son responsabilidad del flujo de revisión humana.
