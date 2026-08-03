# Mininode MVP Factory

## Propósito

Este repositorio puede usarse como una fábrica liviana de MVPs para Mininode. La idea es crear pequeños productos o experimentos de forma controlada usando lenguaje natural, IA y Pull Requests.

El flujo base es:

1. Idea en lenguaje natural.
2. IA propone o crea cambios.
3. Se crea una rama de trabajo.
4. Se abre un Pull Request hacia `main`.
5. Cloudflare genera un Preview.
6. Se revisa el Preview.
7. Se aprueba y se hace merge a `main`.
8. Producción se actualiza automáticamente.

## Regla principal

Todo cambio debe ir por Pull Request hacia `main`.

No se debe modificar `main` directamente. Producción solo cambia cuando un Pull Request revisado se fusiona en `main`.

## Convención para nuevos MVPs

Los MVPs pequeños deben partir como rutas estáticas dentro de `frontend/`.

Convención:

```text
frontend/<nombre_mvp>/index.html
```

Ejemplo:

```text
/factory_demo -> frontend/factory_demo/index.html
```

Siempre que sea posible, partir frontend-only. Esto reduce riesgo, costo y complejidad.

## Restricciones por defecto

Salvo instrucción explícita, no se debe tocar:

- `backend/`
- base de datos
- migraciones
- modelos
- Render
- Cloudflare
- variables de entorno
- `frontend/functions/`
- login
- pagos
- APIs
- configuración de infraestructura

## Estilo de cambios

Los cambios deben ser:

- pequeños
- revisables
- reversibles
- consistentes con el estilo visual de Mininode
- fáciles de probar desde Cloudflare Preview

Si un cambio requiere backend, base de datos, autenticación, pagos, workers, secrets o infraestructura, debe declararse explícitamente antes de implementarlo.

## Checklist para crear un nuevo MVP

Antes de implementar, confirmar:

- [ ] Nombre de la ruta, por ejemplo `/costos_saas`.
- [ ] Objetivo del MVP.
- [ ] Usuario o problema que atiende.
- [ ] Si puede ser frontend-only.
- [ ] Archivos esperados a modificar.
- [ ] Confirmación de que no requiere backend.
- [ ] Confirmación de que no requiere base de datos.
- [ ] Confirmación de que no requiere variables de entorno.
- [ ] Confirmación de que no requiere cambios en Cloudflare o Render.

## Checklist antes de abrir Pull Request

Antes de abrir un PR, confirmar:

- [ ] La rama no es `main`.
- [ ] El cambio está en una rama con nombre claro.
- [ ] El PR apunta hacia `main`.
- [ ] El resumen explica qué cambió.
- [ ] El resumen explica cómo probarlo.
- [ ] El diff contiene solo archivos esperados.
- [ ] No se tocaron archivos restringidos sin instrucción explícita.

## Checklist antes de merge

Antes de hacer merge a `main`, confirmar:

- [ ] El PR fue revisado.
- [ ] Cloudflare Preview funciona.
- [ ] La ruta nueva carga correctamente.
- [ ] No hay cambios inesperados.
- [ ] No se modificó backend, base de datos, Render, Cloudflare ni variables de entorno, salvo que el PR lo indique explícitamente.
- [ ] El cambio es suficientemente pequeño para revertirlo si algo falla.

## Criterio de escalamiento

Un MVP puede escalar de nivel cuando demuestra utilidad.

Ruta sugerida:

1. Celular: idea, instrucción, PR simple y revisión básica.
2. Tablet: revisión visual, previews, GitHub, Cloudflare y Render.
3. Notebook: depuración, backend, base de datos, pagos, login o infraestructura.

No agregar complejidad antes de validar utilidad.