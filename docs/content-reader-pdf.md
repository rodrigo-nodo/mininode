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
- La estructura PDF es **derivada**: ni las líneas ni su orden son un DOM ni son necesariamente el orden de lectura original. No se promete recuperación visual perfecta o fidelidad exacta de los espacios/tablas.
- Conservación textual significa recuperar texto digital **detectable** en las páginas, no verificar objetos visuales o texto dentro de imágenes.

## Límites y errores controlados

- 2 MiB por documento (mismo límite del fetcher), 50 páginas, 200.000 caracteres y 20.000 glifos por página. Excesos generan error explícito sin salida parcial.
- Una página sin palabras extraíbles: `pdf_page_without_text`. PDF con páginas mixtas digital/escaneadas también se rechaza completo.
- Documentos dañados, cifrados o no PDF: error `pdf_parse_failed` o `invalid_pdf`.
- No OCR ni reconstrucción con IA.
- **Limitación consciente:** una página con texto digital e imágenes que contienen texto no puede verificarse íntegramente sin capacidades visuales adicionales. `image_count` se conserva para alertar a consumidores; una página con texto extraído no implica que las imágenes carezcan de información relevante.

## QA

Tests deterministas con PDF generado en memoria, dos páginas, orden, hashes, posiciones, enlaces, páginas sin texto, documento mixto, límites, archivo inválido, fake fetcher y seguridad de retorno cerrado. Pipeline CI exclusivo PDF Reader y tests enfocados de seguridad en la descarga, además de regresión HTML. El conjunto general de tests heredados del fetcher no forma parte de este workflow; presentó un fallo de telemetría de red existente fuera del alcance PDF que debe revisarse por separado.

QA público de humo ejecutado automáticamente en PR: política PDF del sitio web de Clínica Santa María (3 páginas), comprobación de título, derechos, fecha y texto seleccionable en todas las páginas, sin extraer datos personales a los logs. **Este QA no demuestra integridad visual total** ni calidad de reconstrucción de tablas/columnas. La validación visual independiente del orden de lectura y tablas sigue pendiente antes de recomendar merge.
