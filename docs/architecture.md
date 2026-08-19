# Mininode - Arquitectura

## Qué es Mininode

Mininode es una plataforma orientada a crear soluciones digitales livianas para micro y pequeñas empresas, incluyendo micro-SaaS y agentes IA especializados.

El sitio principal es `mininode.io`.

La arquitectura busca mantener los productos simples, modulares, reutilizables y fáciles de validar mediante Pull Requests y previews antes de producción.

## Arquitectura tecnológica base

### Frontend

- HTML, CSS y JavaScript.
- Despliegue mediante Cloudflare Pages.
- `mininode.io` es el dominio principal.
- Las ramas/PR pueden generar previews para validación visual antes del merge.

### Backend

- Python y FastAPI.
- Despliegue mediante Render.
- `api.mininode.io` corresponde al backend público cuando aplica.

### Datos

- PostgreSQL en Render cuando un producto necesita persistencia.
- No asumir que toda funcionalidad necesita base de datos.

### Código y despliegue

- GitHub es la fuente de verdad del código.
- `main` representa la versión aprobada.
- Los cambios deben realizarse mediante ramas y Pull Requests hacia `main`.
- La validación debe privilegiar el resultado funcional/preview además de las pruebas técnicas.

## Estructura general del repositorio

- `frontend/` - sitio y productos frontend.
- `backend/` - API, servicios y lógica backend.
- `.github/workflows/` - automatizaciones de GitHub Actions.
- `docs/` - documentación estable de arquitectura y contexto de productos.

## Principios

- Cambios pequeños antes que grandes refactorizaciones.
- Reutilizar componentes y servicios cuando exista una abstracción adecuada.
- No agregar infraestructura antes de que sea necesaria.
- Mantener frontend y backend desacoplados cuando sea razonable.
- Mantener seguridad y trazabilidad como restricciones de diseño, no como ajustes posteriores.
- No modificar infraestructura, despliegue, secrets, autenticación, pagos o base de datos por conveniencia si la tarea no los requiere.

## Productos y contexto específico

La arquitectura general no debe contener todos los detalles de cada producto.

Cada producto puede tener un documento específico dentro de `docs/`.

Actualmente:

- `docs/privacy.md` - Mininode Privacy y Privacy Web Inspector.

Los agentes de código deben leer únicamente los documentos necesarios para la Issue que están implementando.