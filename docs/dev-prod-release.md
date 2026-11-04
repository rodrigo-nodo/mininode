# Mininode - Desarrollo y publicación DEV → PROD

## Objetivo

Validar cambios en DEV y publicar en PROD únicamente el alcance aprobado, manteniendo `main` como fuente de verdad técnica de producción. No se fusiona `dev` completa por defecto.

## Entornos

- **DEV:** rama permanente `dev`, Cloudflare DEV y backend/base de datos DEV. Sirve para integración y validación funcional.
- **PROD:** rama `main`, Cloudflare Production y backend/base de datos de producción. Recibe exclusivamente cambios aprobados.
- La configuración de infraestructura, identidad, variables y datos puede diferir entre entornos. La equivalencia de código no demuestra equivalencia de configuración ni de despliegue.

## Flujo de un cambio

1. **Definir el alcance.** Acordar objetivo, comportamiento y criterios de validación antes de implementar.
2. **Desarrollar en DEV.** Crear cambios enfocados por **objetivo funcional completo** y validar pruebas, CI y comportamiento en el entorno DEV. Registrar los archivos y dependencias del alcance aprobado; no fragmentar artificialmente un recorrido que requiere frontend, backend o contratos coordinados.
3. **Preparar la publicación.** Partir de `main` actualizado en una rama nueva. Incorporar únicamente el **alcance funcional aprobado** desde DEV, con sus dependencias, pruebas, documentación y migraciones necesarias. Adaptar las diferencias legítimas de MAIN y DEV en vez de copiar archivos completos; no fusionar `dev` masivamente ni arrastrar otras funciones.
4. **Revisar el PR a `main`.** Examinar el diff respecto a `main`; comprobar que no incluya otros trabajos de DEV, que preserve los cambios propios de `main` y que CI del último commit esté correcto. Si el cambio requiere migraciones o configuración, establecer su orden y compatibilidad antes de desplegar.
5. **Validar antes de merge.** Utilizar preferentemente el Branch Preview estable del PR, confirmado para su último commit. El usuario valida producto, UX, textos y recorrido; una revisión técnica independiente es opcional según el riesgo. No hacer merge sin autorización explícita.
6. **Publicar y verificar.** Tras el merge autorizado, confirmar que Cloudflare y Render (cuando corresponda) desplegaron el commit esperado de `main`. Validar el comportamiento en PROD y sus integraciones, sin suponer que un CI verde demuestra el despliegue. Cerrar esta publicación antes de iniciar otra publicación dependiente; el desarrollo independiente puede continuar en DEV.
7. **Comprobar equivalencia del alcance.** Contrastar los archivos, contratos y comportamiento aprobados en DEV con lo publicado en PROD. Documentar diferencias deliberadas de configuración o de adaptación a `main`. La comparación debe centrarse en el alcance publicado, no en el número de commits divergentes.

## Principios para reducir fragmentación

- **Unidad de entrega funcional:** PRs pequeños por comportamiento y riesgo, no necesariamente por archivo o capa. Un mismo objetivo puede incluir frontend, backend, pruebas, contratos y documentación para que el recorrido sea utilizable.
- **Paridad de producto y contrato:** lo aprobado en DEV debe comportarse igual en PROD. No se exige identidad textual ni de commits entre entornos cuando existen adaptaciones legítimas; las diferencias operativas deben quedar identificadas.
- **QA proporcionado:** GitHub Actions valida automáticamente el alcance. Incorporar regresiones web determinísticas con Playwright cuando sean repetibles y valiosas, sin exigirlo en cada cambio. Usar Work para QA exploratorio de alto valor, no una automatización por PR. El PO valida UX y recorrido.
- **Publicación secuencial cuando hay dependencia:** cerrar CI, autorización, despliegue y comprobación de una publicación antes de promocionar la siguiente dependiente. Los PRs independientes no requieren bloqueo mutuo.
- **Sin PREVIEW integrado por ahora:** el Branch Preview ayuda a revisar frontend y CI, pero no sustituye las pruebas integradas con Clerk y Render. `preview.mininode.io` se evaluará al terminar los desarrollos pendientes de Privacy Web y **antes de pilotos o ventas**. Hasta entonces no se crea infraestructura ni se considera validado un candidato por SHA en preproducción.

## Criterio de cierre de una publicación

- El PR contiene solo el alcance aprobado y sus dependencias.
- CI relevante del último commit aprobado está correcto.
- Preview y validación del usuario completados cuando apliquen.
- Merge expresamente autorizado.
- Despliegues de producción comprobados contra el commit publicado.
- Equivalencia del alcance DEV/PROD comprobada; excepciones conocidas documentadas.

Si falta alguno de estos controles, no declarar la publicación completamente validada.

## Ramas divergentes

`dev` y `main` pueden tener historiales distintos porque PROD recibe publicaciones selectivas. Los conteos de commits o el diff histórico desde el ancestro común **no** equivalen a funcionalidades pendientes: incluyen cambios ya publicados por otros PR y commits con historial distinto. Para detectar pendientes reales, comparar el contenido actual relevante y las dependencias de cada funcionalidad, y verificar el despliegue de ambos entornos.

No sincronizar las ramas masivamente para eliminar diferencias de historial. Resolver únicamente divergencias funcionales reales mediante cambios específicos, sin sobrescribir avances exclusivos de `main`.

## Responsabilidades

- **ChatGPT:** revisar `main`, DEV y PR relacionados; preparar el PR enfocado, inspeccionar diff, comprobar CI, preview y equivalencia de publicación.
- **Usuario (PO):** aprobar alcance, validar el resultado visible y autorizar expresamente el merge.
- **Reviewer independiente (opcional):** revisar cambios relevantes de backend, seguridad, contratos, base de datos o lógica crítica sin implementar modificaciones.

Este procedimiento complementa la arquitectura de `docs/architecture.md` y no sustituye los controles específicos de cada producto.

## Roadmap compartido y QA propuesto

Las iniciativas estratégicas se mantienen únicamente en [`docs/roadmap.md`](roadmap.md) de `main`. DEV debe enlazar esa referencia, sin mantener una copia estratégica paralela. Los documentos de ejecución y sus evidencias sí pueden diferir por entorno; no copiar roadmaps de producto completos entre ramas.

Se propone `preview.mininode.io` como futuro entorno integrado de preproducción con SHA candidato congelado. Su implementación queda **postergada hasta finalizar los desarrollos pendientes de Privacy Web y debe preceder pilotos o ventas**. No está habilitado por esta documentación. Mientras tanto un Branch Preview `*.pages.dev` comprueba build/maquetación, pero no el E2E autenticado con Clerk/Render. Revalidar solo en DEV tampoco acredita la promoción sobre `main`: conservar CI, revisión, autorización de merge, comprobación del destino y rollback cuando aplique.
