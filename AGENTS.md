# Mininode - Guía de trabajo para agentes de código

## Propósito

Mininode se desarrolla mediante cambios pequeños, revisables y reversibles. Las Issues en lenguaje natural definen la tarea y el agente debe realizar el cambio mínimo necesario para cumplirlas.

## Flujo de trabajo

1. Leer este archivo.
2. Leer completamente la Issue.
3. Identificar el producto o área afectada.
4. Leer solo el contexto necesario para esa tarea.
5. Revisar primero los archivos directamente relacionados.
6. Ampliar la exploración solo si imports, llamadas, pruebas o errores lo requieren.
7. Implementar y ejecutar las pruebas relevantes.
8. Dejar commit, push y creación del Pull Request a la automatización.

## Contexto disponible

- `docs/architecture.md` - contexto general y arquitectura estable de Mininode. Consultarlo cuando la tarea necesite comprender plataforma, dominios, frontend/backend, despliegue o estructura general.
- `docs/privacy.md` - contexto específico de Mininode Privacy y Privacy Web Inspector. Leerlo para tareas de Privacy.

No leer todos los documentos por defecto. La Issue determina qué contexto es necesario.

## Mapa básico del repositorio

- `frontend/` - HTML/CSS/JavaScript y código frontend servido mediante Cloudflare Pages.
- `backend/` - backend Python/FastAPI desplegado en Render.
- `.github/workflows/` - automatización GitHub Actions. No modificar salvo que la Issue lo solicite explícitamente.
- `docs/` - contexto estable de arquitectura y productos.

## Enrutamiento de contexto

- Tarea general de arquitectura, infraestructura o integración Mininode -> leer `docs/architecture.md`.
- Mininode Privacy / Privacy Web Inspector -> leer `docs/privacy.md`; leer `docs/architecture.md` solo si la tarea necesita contexto general adicional.
- Otras áreas -> usar la Issue y revisar únicamente el código relacionado, salvo que se indique otro documento de contexto.

## Reglas

- Todo cambio de producto debe pasar por Pull Request hacia `main`.
- Nunca modificar `main` directamente.
- Preferir cambios pequeños y reversibles.
- No inventariar ni resumir todo el repositorio salvo que la Issue solicite explícitamente un análisis de arquitectura/repositorio.
- No leer documentación de productos no relacionados solo como contexto general.
- Tratar los hechos y diagnósticos entregados en la Issue como información ya investigada por ChatGPT/revisión humana; no redescubrirlos salvo que sea necesario validarlos para implementar con seguridad.
- Mantener la arquitectura y convenciones existentes.
- Ejecutar primero pruebas focalizadas; ampliar las pruebas cuando la superficie afectada lo requiera.
- No debilitar controles de seguridad salvo que la Issue solicite explícitamente un cambio de seguridad revisado.
- No modificar workflows, infraestructura, secrets, configuración de despliegue, base de datos, autenticación o pagos salvo que estén explícitamente dentro del alcance.

## Convención para MVP frontend-only

Para un MVP estático pequeño, preferir:

```text
frontend/<nombre_mvp>/index.html
```

Partir frontend-only cuando la Issue no requiera capacidades backend.

## Calidad del Pull Request

El resultado debe permitir responder fácilmente:

- ¿Qué cambió?
- ¿Por qué era necesario?
- ¿Cómo se probó?
- ¿Qué archivos cambiaron?
- ¿Cambió algo fuera del alcance de la Issue?

El merge requiere revisión humana.