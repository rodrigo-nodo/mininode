# Content Reader PDF V1 - Micropieza independiente

## Objetivo y frontera

Procesar PDFs **digitales con texto seleccionable** sin OCR, LLM ni interpretación semántica. Es un módulo separado de Content Reader HTML y no reutiliza su DOM. PDF usa páginas y coordenadas. Semantic Engine podrá consumir ambas representaciones mediante un contrato de intercambio posterior.

## Entrada

- `read_pdf_document(bytes, final_url=None)`: bytes de un PDF descargado/autorizado.
- `read_public_pdf_url(url)`: GET pasivo y público a través de WebFetcher, con protección robots, SSRF, IP fijada, redirecciones same-host y límite binario de 2 MiB.
- Solo `application/pdf` declarado y encabezado `%PDF-` válido. No solicitudes de login, POST o formularios.

## Salida

- `PdfDocument`: URLs, `file_sha256` (bytes originales), `text_sha256` (texto reconstruido), `text`, páginas, recuentos, `truncated=false`.
- `PdfPage`: número 1-based, ancho/alto, líneas, enlaces absolutos explícitos PDF, número de imágenes.
- `PdfTextLine`: número de página, texto derivado de las palabras seleccionables, bbox en puntos del sistema de coordenadas de la biblioteca.
- `PdfTable` / `PdfTableCell`: tablas identificadas mediante líneas explícitas del PDF, con fila, columna y coordenadas por celda. `PdfBlock` conserva bloques de texto y tablas en orden de página. Tablas sin estructura comprobable y columnas paralelas ambiguas se rechazan con `pdf_layout_ambiguous` en lugar de mezclar su contenido.
- La estructura PDF es **derivada**: ni las líneas ni su orden son un DOM ni son necesariamente el orden de lectura original. No se promete recuperación visual perfecta o fidelidad exacta de los espacios/tablas.
- Conservación textual significa recuperar texto digital **detectable** en las páginas, no verificar objetos visuales o texto dentro de imágenes. `integrity_status` distingue `text_extracted_not_visually_verified` y `unverified_visual_content` cuando hay imágenes. Ningún estado afirma integridad documental visual verificada.

## Límites y errores controlados

- 2 MiB por documento (mismo límite del fetcher), 50 páginas, 200.000 caracteres y 20.000 glifos por página. El procesamiento de PDF no confiable ocurre en **subproceso aislado** con límite de **15 s de tiempo real, 10 s de CPU y 768 MiB de memoria virtual** mediante `resource.setrlimit` en Linux. Los límites de tiempo/recursos incluyen extracción de caracteres comprimidos, antes del chequeo funcional de cantidad; cualquier exceso retorna `pdf_processing_timeout`, `pdf_resource_limit` o `pdf_worker_failed` sin salida parcial. Este límite no es un sandbox de seguridad completo; el acceso a archivos/red del subproceso debe ser evaluado separadamente.
- Una página sin palabras extraíbles: `pdf_page_without_text`. PDF con páginas mixtas digital/escaneadas también se rechaza completo.
- Documentos dañados, cifrados o no PDF: error `pdf_parse_failed` o `invalid_pdf`.
- No OCR ni reconstrucción con IA.
- **Limitación consciente:** páginas con texto digital junto a imágenes pueden ocultar información textual. `image_count`, `extraction_status=digital_text_with_images` e `integrity_status=unverified_visual_content` advierten inequívocamente. No se afirma lectura íntegra solo porque haya texto seleccionable. Colores, columnas sin estructura delimitada y tablas sin bordes siguen siendo causas potenciales de ambigüedad.

## QA

Tests deterministas con PDF generado en memoria, dos páginas, orden, hashes, posiciones, enlaces, páginas sin texto, documento mixto, límites, archivo inválido, columnas paralelas, tabla con relaciones fila-columna, imagen con texto no extraíble, documento comprimido complejo, timeout simulado, fake fetcher y seguridad de retorno cerrado. Pipeline CI exclusivo PDF Reader y tests enfocados de seguridad en la descarga, además de regresión HTML. El conjunto general de tests heredados del fetcher no forma parte de este workflow; presentó un fallo de telemetría de red existente fuera del alcance PDF que debe revisarse por separado.

QA público de humo ejecutado automáticamente en PR: política PDF del sitio web de Clínica Santa María (3 páginas), comprobación de título, derechos, fecha y texto seleccionable en todas las páginas, sin extraer datos personales a los logs. **Este QA no demuestra integridad visual total** ni calidad de reconstrucción de tablas/columnas. La validación visual independiente del orden de lectura y tablas sigue pendiente antes de recomendar merge.

## Regresión de columnas - Segunda revisión

Se sustituyó la heurística de filas alineadas por una detección conservadora de **corredores verticales de separación entre bloques de palabras**, evaluados sobre ventanas de líneas, después de excluir las palabras de tablas con estructura comprobada. Se rechazan tanto columnas con desfase vertical como columnas de etiquetas cortas con `pdf_layout_ambiguous`, sin interpolar orden. Dos tests deterministas reproducen los contraejemplos del Reviewer. La detección es conservadora, no afirma resolver automáticamente todo diseño multicolumna; los diseños no determinables deben rechazarse antes de que el consumidor infiera relaciones inexistentes.

## Regresión de columnas - Tercera revisión

La detección de corredores paralelos admite separaciones persistentes desde `max(8 puntos, 1,2 % del ancho de página)` y ya no depende exclusivamente del umbral anterior de 3,5 %. Para reducir falsos positivos, las listas con marcadores numéricos explícitos (`1.`, `2)`, `(3)`) alineados con su texto se tratan como una secuencia de lectura, no como dos columnas. No se aplican estas excepciones a etiquetas genéricas como `A0`/`B0`. Se agregaron pruebas end-to-end de columnas independientes separadas 16 puntos y listas numeradas de cinco elementos, conservando las pruebas previas de columnas desfasadas, etiquetas cortas y tablas. La geometría PDF no garantiza por sí sola interpretación visual correcta de todos los diseños; el lector mantiene el rechazo conservador `pdf_layout_ambiguous` ante ambigüedad detectada.

## Regresión de columnas - Cuarta revisión

La detección de corredores usa un umbral dependiente de la altura de palabra (`max(3,5 puntos; 45 % de altura típica)`) en vez del ancho total de la página, permitiendo identificar columnas separadas por 7 puntos en las muestras adversariales. Una región estrecha con marcadores de lista explícitos alineados a la misma altura (`-`, letras seguidas de `)`, números o viñetas) se trata como una secuencia. Se agregan tres casos de regresión end-to-end: guiones, letras y columnas de 7 puntos. No existe garantía universal de interpretar correctamente cualquier diseño PDF; se mantiene la política de rechazo explícito ante ambigüedad detectada.

## Quinta revisión independiente - Resolución focalizada

Se agregaron tests completos de listas Unicode/romanas (◦, ▪, (a), IV.) y dos campos independientes repetidos con separación de 3 y 4 puntos, junto a una prueba de una oración corta legítima. El detector de corredores mantiene el umbral calibrado anterior para evitar rechazar páginas normales: **no se redujo globalmente el umbral geométrico**. Se agregó una verificación acotada de dos campos de texto repetidos en al menos tres líneas, con una separación estrecha entre glifos y mismas etiquetas/posición. Así se detectan ejemplos repetitivos adversariales sin confundir una oración corriente aislada con dos columnas. Limitación: no es una garantía general para todos los campos arbitrarios pegados ni para PDFs complejos; cuando la estructura no es distinguible mediante indicios del propio documento, el resultado no equivale a integridad visual verificada.

## Integración estructural - Etapa inicial (PR #321)

El lector comienza a conservar la evidencia estructural de **pdfminer.six + pdfplumber** sin inventar orden semántico:
- `PdfPage.layout_regions`: candidatos de regiones `LTTextBoxHorizontal`, con texto, página y coordenadas; la fuente se identifica explícitamente como `pdfminer_lttextbox_candidate`.
- `PdfPage.structure_tags` y `structure_tag_error`: tipos de etiquetas presentes cuando `structure_tree` puede leerse; errores de etiquetas no se presentan como evidencia válida.
- `PdfTextLine.source_char_indices`: índices a `page.chars` originales, obtenidos con `extract_text_lines(return_chars=True)` de pdfplumber, excluyendo caracteres que ya pertenecen a tablas identificadas. El texto y los espacios reconstruidos continúan siendo derivados.
- `PdfTableCell.source_char_indices`: índices originales asociados a cada celda de tabla detectada mediante líneas. Permiten comprobar la procedencia y evitar doble asignación entre celdas y líneas narrativas.
- Extracción de líneas realizada por la biblioteca, en lugar de reagrupar palabras manualmente por `top/bottom` redondeado.
- Las tablas respaldadas por bordes mantienen su representación por filas y celdas. No se activa `find_tables(text)` indiscriminadamente: en las pruebas reales confundió listas y párrafos con tablas.
- `PdfPage.source_coverage_status=all_nonwhitespace_glyphs_assigned_once`: validación determinista de que cada glifo digital no blanco tenga una sola asignación entre líneas y celdas; si falla, se rechaza el documento como `pdf_layout_ambiguous`. **No verifica orden de lectura ni asociaciones semánticas.**

**Pendiente antes del merge:** reemplazar los detectores históricos de columnas/espacios con una validación general basada en estos candidatos y en procedencia de caracteres; comprobar sus asociaciones y orden con QA independiente. Esta etapa no acredita el problema de fidelidad estructural como resuelto. No se habilita consumo semántico directo sin esa validación.

**Prueba Claro Chile:** sobre el PDF original adjuntado, con pdfplumber 0.11.4 + pdfminer.six 20231228, se identificó una tabla 3×2 (página 3) con una fila vacía y una 5×2 (página 4). Las seis asociaciones no vacías se conservan. La prueba se ejecutó con Python 3.13 en análisis local; las mismas dependencias se comprobaron también con Python 3.11 en GitHub para otras muestras. El PDF original no se publicó en el repositorio.
