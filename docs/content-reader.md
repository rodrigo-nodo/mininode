# Content Reader V1 - Contrato estructurado

## Propósito

Content Reader obtiene y representa íntegramente el texto y la estructura del **HTML estático recibido**, sin decidir relevancia ni interpretar significado. Su salida sirve como entrada a las piezas futuras: **2. Semantic Engine** (contenido + prompt + Markdown) y **3. Output Validator** (contrato y evidencia).

## Contrato

`read_html_document(html, final_url, requested_url=None)` o `read_public_html_url(url)` (mediante el WebFetcher seguro existente) produce `ContentDocument`:

- `nodes`: referencia **primaria** y ordenada (recorrido DOM preorder). Cada `ContentNode` tiene `id`, `parent_id`, `kind` (`element` o `text`), `tag`, `text` exacto decodificado del HTML, `href` absoluto si corresponde y flags `hidden`/`aria_hidden`. Las relaciones permiten reconstruir el árbol y distinguir fragmentos contiguos dentro de un enlace.
- `source_text`: concatenación **exacta** de los valores de los nodos de texto incluidos, sin espacios inventados ni normalización de palabras, puntuación o saltos. `source_sha256` y `source_character_count` identifican esa representación.
- `text`: vista legible **derivada** que normaliza espacio en blanco y marca límites de bloque, sin adivinar separaciones entre etiquetas inline. Puede diferir del texto renderizado por el navegador; **no constituye la fuente de verdad**.
- `links`, título, URL solicitada y final, hash y tamaño de la vista, alcance `static_html`, `truncated=false`.

Ejemplo: `<a><span>Mis compras</span>Haz seguimiento</a>` conserva dos nodos de texto `Mis compras` y `Haz seguimiento`, ambos bajo la misma rama `a`. La vista no afirma que sea una oración ni un salto visual. Igualmente `anti<span>virus</span>` conserva `anti` y `virus`, sin introducir espacio.

## Límites

Se excluyen únicamente contenido técnico de `script`, `style`, `template`, `svg` y `canvas`, y comentarios HTML. Los nodos `hidden` y `aria-hidden` **se conservan**, marcados en la estructura (el segundo atributo no implica invisibilidad visual). No se ejecutan JavaScript ni CSS. No se procesan PDF, iframes externos ni documentos enlazados en V1. El límite de 200.000 caracteres aplica tanto a `source_text` como a `text`: si se supera, hay error explícito `document_too_large`, no truncamiento silencioso. El lector no usa LLM, no persiste textos y no realiza llamadas fuera del WebFetcher existente.

## Validación

Los tests unitarios tienen **resultados esperados explícitos** para fragmentos, espacios, puntuación, enlaces, jerarquía y límites HTML ambiguos. El QA público compara el texto fuente exacto y la secuencia de nodos/etiquetas contra la captura original, sin crear espacios entre nodos al construir la referencia. Los enlaces también deben conservar destino y orden.

El QA compara **HTML estático**, no garantiza equivalencia visual con Chrome ni contenido generado por JS. Cualquier capa de renderizado futuro debe ser un adaptador independiente.

No se modifican Web Inspector, Privacy Web, scoring, Semantic Engine ni Output Validator.
