# Content Reader - Primera pieza agnóstica

## Objetivo

Entregar contenido completo de un documento HTML público para que una pieza posterior lo interprete. **Content Reader no determina relevancia, significado, cumplimiento, estados ni hallazgos.**

Plan de piezas independientes:

1. **Content Reader** - adquirir y representar contenido sin filtrado semántico.
2. **Semantic Engine** - ejecutar prompt + Markdown de instrucciones sobre contenido.
3. **Output Validator** - verificar el contrato de salida y las evidencias.

Solo la primera pieza está incluida en este cambio.

## Contrato V1

`read_html_document(html, final_url, requested_url=None)` recibe HTML ya obtenido. `read_public_html_url(url)` utiliza el `WebFetcher` existente, con sus protecciones de red, restricciones de robots y límites HTTP.

Devuelve `ContentDocument` con:

- URL solicitada y URL final tras redirecciones;
- título y contenido textual completo del HTML estático, manteniendo orden, encabezados y listas;
- enlaces observables y destinos absolutos;
- tamaño en caracteres, SHA-256 del texto y alcance `static_html`;
- indicador `truncated=false`.

No se seleccionan ni resumen párrafos según su materia. Encabezados, formularios y pies se mantienen porque pueden contener información relevante para algún consumidor.

## Límites explícitos

- No ejecuta JavaScript ni reproduce contenido generado en el navegador.
- No aplica estilos CSS ni garantiza equivalencia pixel a pixel con el documento renderizado.
- Omite scripts, estilos, plantillas y SVG/canvas. Conserva el texto de nodos `hidden` y `aria-hidden` para no excluir contenido estático silenciosamente.
- Solo acepta el HTML respaldado por el `WebFetcher` existente; no incorpora PDF ni otras fuentes en V1.
- Límite explícito de 200.000 caracteres de texto extraído. Si se supera, se devuelve `document_too_large`, **nunca un documento parcial presentado como completo**.
- Un documento sin texto devuelve `empty_document`; los errores de obtención siguen siendo explícitos.
- El lector no almacena documentos, no utiliza LLM ni transmite contenido a proveedores.
- La procedencia y el hash permiten verificar que una comparación posterior utilice la misma captura.

Nota de fidelidad: al concatenar fragmentos HTML inline, se añade una separación para etiquetas textuales contiguas cuando el siguiente fragmento comienza con mayúscula y el anterior termina en minúscula o puntuación de cierre. Este ajuste evita uniones detectadas en abc.cl sin introducir espacios indiscriminados entre fragmentos de una misma palabra. No sustituye el renderizado CSS/JS del navegador.\n\nLa integridad garantizada es **respecto del texto del HTML estático obtenido**, no de cualquier contenido dinámico o de recursos vinculados. La preparación de contexto adicional del sitio y selección de documentos corresponden a integraciones futuras.

## Compatibilidad y validación

Se agrega un paquete independiente bajo `backend/src/mininode_api/content_reader/`. No modifica `Web Inspector`, `EvidenceContract`, controles, evaluaciones, scoring, API ni UI de Privacy Web.

Los tests incluyen un documento con información al final después de 12.000 caracteres, preservación de estructura/enlaces, errores ante límites, reutilización del fetcher y ausencia de interpretación semántica.
