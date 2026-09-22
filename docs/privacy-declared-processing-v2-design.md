# declared_processing/v2 - diseño de contrato

## Estado

**Diseño manual. No implementado. No ejecuta LLM.**

Esta propuesta nace del resultado QA2 de `declared_processing/v1`. Mantiene el extractor semántico desacoplado de los controles Privacy Web: extrae declaraciones públicas y no decide PRV, cumplimiento, riesgo ni score.

## Problema observado en v1

V1 modela el documento como hasta 100 `records`, cada uno con ocho familias y hasta 30 hechos por familia. En QA2, documentos con 8-10 hechos de referencia produjeron entre 37 y 64 hechos en outputs válidos, y documentos ricos agotaron el límite de 8192 tokens.

El problema de diseño no es la existencia de las ocho familias, sino exigir al modelo reconstruir unidades relacionales exhaustivas del documento.

## Objetivo v2

Responder una consulta semántica acotada sobre un documento público y devolver solo los hechos explícitos necesarios para esa consulta, con evidencia literal.

V2 no intenta reconstruir exhaustivamente toda la política.

## Familias

Se conservan las ocho familias de v1:

- `technology`
- `provider`
- `data_categories`
- `purposes`
- `recipients`
- `legal_basis`
- `retention`
- `international_transfers`

## Entrada propuesta

```json
{
  "source": {
    "url": "...",
    "document_type": "privacy_policy | cookie_policy | other_public_document",
    "page_title": null
  },
  "query": {
    "families": ["data_categories", "purposes"],
    "question": "opcional"
  },
  "text": "..."
}
```

`families` es obligatorio y limita qué tipos de hechos se solicitan. `question` es opcional y solo acota la búsqueda; no autoriza conocimiento externo ni conclusiones jurídicas.

## Salida propuesta

```json
{
  "schema_version": "declared_processing/v2",
  "facts": [
    {
      "family": "data_categories",
      "value": "datos de identificación y contacto",
      "status": "supported",
      "evidence": "nombre completo, RUT, correo electrónico y teléfono"
    }
  ]
}
```

### Reglas

1. Un hecho pertenece a una sola familia.
2. Solo se devuelven familias solicitadas.
3. `supported` exige evidencia literal presente en el texto recibido.
4. Si existe texto relacionado pero no permite sostener inequívocamente el hecho, puede usarse `ambiguous`.
5. Si no existe evidencia suficiente, no se inventa un hecho ni se emite `not_found`: la familia simplemente no aparece.
6. `value` resume fielmente lo declarado; `evidence` conserva una cita literal breve.
7. No se crean `records`, relaciones ni agrupaciones salvo que una futura consulta las solicite explícitamente.
8. No se usa conocimiento externo.
9. No se concluye cumplimiento, riesgo, score, consentimiento válido, necesidad de banner ni estados PRV.
10. La salida debe ser mínima: no fragmentar una misma declaración en múltiples hechos equivalentes.

## Límites propuestos

Los límites definitivos se fijarán antes de implementar. Como hipótesis de diseño:

- máximo 8 familias solicitadas;
- máximo 10 hechos por familia;
- `value` máximo 300 caracteres;
- `evidence` máximo 500 caracteres.

Estos límites no se consideran calibrados todavía.

## Relación con v1

V2 no reemplaza ni modifica v1 todavía. Es un contrato candidato.

Se conserva de v1:

- fuente pública como entrada;
- ocho familias;
- evidencia literal;
- estados conservadores;
- ausencia de conocimiento externo;
- separación respecto de controles Privacy Web.

Se elimina de v1:

- `record_id`;
- hasta 100 unidades relacionales;
- repetición de `source` por record;
- obligación de reconstruir relaciones exhaustivas entre hechos;
- `normalized_value` en la primera propuesta v2.

## Validación manual previa a implementación

Antes de implementar LLM:

1. usar las seis capturas consumidas de QA2 como material de diseño, no como nuevo holdout;
2. formular consultas por familias;
3. construir manualmente la salida mínima esperada;
4. comprobar que cubra los hechos útiles de la referencia QA2 sin reconstruir todo el documento;
5. fijar límites y reglas solo después de esa revisión.

QA2 permanece `NEEDS FIX` y consumido. Una implementación futura de v2 deberá validarse con un holdout nuevo (QA3).
