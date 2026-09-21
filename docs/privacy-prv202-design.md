# Privacy Web - PRV-202 diseño de transparencia tecnológica

## Objetivo

Definir PRV-202 antes de incorporarlo al catálogo productivo de Privacy Web.

PRV-202 complementa a PRV-201 sin reinterpretarlo:

- **PRV-201 - Cookies observadas** registra una señal técnica obtenida mediante `Set-Cookie`.
- **PRV-202 - Información pública sobre tecnologías observadas** contrasta señales técnicas observadas con información pública atribuible al sitio.

PRV-202 no concluye cumplimiento legal. Su objetivo es aportar una señal de transparencia y coherencia entre lo técnicamente observable y lo públicamente declarado.

## Alcance V1

Pregunta del control:

> **¿Existe información pública que describa el tratamiento asociado a las tecnologías observadas?**

El control debe permanecer inicialmente **contextual/informativo**, con **peso cero**, fuera del Privacy Score, cobertura, prioridades y Plan de corrección, hasta validar que la correspondencia entre tecnología observada e información pública puede evaluarse con confiabilidad suficiente.

PRV-202 no se incorpora todavía al catálogo canónico de controles. Por ello esta definición no cambia las versiones vigentes del framework ni del scoring.

## Evidencia de entrada

PRV-202 necesita dos clases de hechos:

1. **Evidencia técnica observable**
   - tecnología o cookie observada;
   - fuente y alcance técnico de la observación;
   - evidencia producida por PRV-201 u otros detectores técnicos futuros.

2. **Información pública atribuible al sitio**
   - declaración pública relacionada con la tecnología o tratamiento;
   - evidencia textual;
   - URL o fuente pública;
   - hechos estructurados extraídos desde esa evidencia.

La mera presencia o ausencia de un banner no determina el resultado de PRV-202.

## Estados propuestos

### detected

Existe evidencia suficiente para relacionar de forma respaldada una tecnología observada con información pública que describe su tratamiento.

### partial

Existe información pública relacionada, pero la correspondencia con lo observado es incompleta o solo cubre parte de las señales técnicas relevantes.

### not_detected

Existen tecnologías observadas dentro del alcance técnico y, dentro del alcance documental inspeccionado, no se encontró información pública relacionada suficiente.

Este estado describe ausencia de evidencia pública encontrada. No equivale por sí mismo a una conclusión de incumplimiento legal.

### not_evaluable

La evidencia técnica o documental disponible no permite establecer de forma suficientemente confiable la correspondencia entre lo observado y lo declarado.

Si PRV-201 no observa cookies, PRV-202 no debe convertir esa ausencia de observación en una conclusión adversa. Mientras no exista otra tecnología observable que permita evaluarlo, el resultado debe quedar fuera de una conclusión negativa.

## Qué no evalúa

PRV-202 V1 no evalúa:

- si un banner de cookies es jurídicamente obligatorio;
- si el consentimiento es la base de licitud correcta;
- si un consentimiento es válido, libre, informado o específico;
- funcionamiento de un CMP o de controles de preferencias;
- bloqueo previo o posterior de cookies;
- efectividad real de revocación o retiro del consentimiento;
- suficiencia jurídica integral de una política;
- prácticas internas no observables;
- si una cookie es necesaria o no necesaria como conclusión jurídica.

Estas materias requieren otros controles, evidencia activa o revisión jurídica/técnica adicional.

## Dependencia semántica

PRV-202 debe respetar la arquitectura común definida en `docs/privacy.md`:

**Página → evidencia textual → extractor semántico común → hechos estructurados → controles deterministas.**

PRV-202 no debe implementar un clasificador semántico propio ni cerrar la brecha mediante listas particulares de palabras clave.

La capa semántica común debe producir hechos estructurados, evidencia textual y fuente. PRV-202 consume esos hechos y aplica una regla determinista, trazable y versionable.

Mientras esa capa no esté disponible o suficientemente validada, PRV-202 permanece como diseño pendiente y no debe incorporarse como control productivo puntuable.

## Relación con la matriz legal observable

PRV-202 desarrolla la línea ya definida en `docs/privacy-web-legal-coverage.md`:

- Privacy Web observa lo declarado y técnicamente visible.
- Las cookies o tecnologías observadas son señales que pueden contrastarse con información pública.
- Observar una cookie no determina por sí mismo una obligación incumplida ni exige automáticamente un banner.
- La existencia y efectividad real del tratamiento pertenece a Privacy Data o a una revisión interna.

## Criterios para pasar a implementación productiva

Antes de incorporar PRV-202 al catálogo canónico se debe definir y validar:

1. qué tecnologías son observables con evidencia técnica confiable;
2. cuál es la evidencia pública mínima que permite establecer correspondencia;
3. qué hechos debe entregar la capa semántica común;
4. reglas deterministas exactas para `detected`, `partial`, `not_detected` y `not_evaluable`;
5. un conjunto de validación independiente que mida falsos positivos y falsos negativos;
6. si, después de esa validación, el control sigue siendo informativo o existe fundamento suficiente para revisar su participación en scoring.

Cualquier cambio posterior que incorpore PRV-202 al diagnóstico productivo deberá revisar framework, scoring, tests, frontend y esta documentación.
