# W2.2b.3-calibration-fix4 - PRV-103 v0.7

"
    "## Objetivo

"
    "Corregir el patrón observado en QA4 de framework 0.6 sin reutilizar QA4 como nueva validación independiente.

"
    "## Cambios

"
    "- Reduce `unknown` cuando los cuatro campos estructurados del mismo formulario expresan un resultado concreto y acotado.
"
    "- Reconoce patrones generalizables observados en QA4: acceso a cuenta, seguimiento de pedidos, pagos, búsqueda de direcciones de entrega, creación de tienda, postulación, llamada/cotización y suscripciones con contenido declarado.
"
    "- Corrige la falsa promoción de `Enviar mensaje`: contacto/mensaje sin resultado adicional permanece `generic`.
"
    "- `Next` aislado pasa de `generic` a `unknown`.
"
    "- Mantiene fuera de PRV-103 campos del formulario, `nearby_text`, URLs y conocimiento externo del sitio.

"
    "## Versionado

"
    "- `framework_version`: 0.7.
"
    "- `scoring_version`: 0.1 sin cambios.
"
    "- 21 controles sin cambios.
"
    "- PRV-103 continúa con `score_weight = 0`.

"
    "## Validación

"
    "Los 37 casos de QA4 pasan a ser regresión/tuning y no pueden utilizarse para declarar PASS de 0.7. El siguiente QA independiente debe congelar 0.7 y usar organizaciones completamente nuevas.
"
    