# Privacy Web - Contrato semántico `declared_processing/v1`

## Objetivo

Definir el contrato mínimo y reutilizable con el que la capa semántica común representa declaraciones públicas sobre tratamiento de datos.

El contrato es agnóstico de los controles. No conoce PRV-202 ni decide resultados de Privacy Web.

Principio:

> **El extractor interpreta lenguaje y entrega hechos con evidencia. Los controles determinan estados mediante reglas trazables y versionables.**

## Unidad de salida

La salida contiene uno o más `records`. Cada record representa una unidad semántica cuyos hechos están relacionados entre sí.

Esto evita perder relaciones. Por ejemplo, si una política declara Google Analytics para estadísticas y HubSpot para formularios, deben producirse records distintos en lugar de listas globales que permitan asociar incorrectamente una finalidad a otra tecnología.

```json
{
  "schema_version": "declared_processing/v1",
  "records": []
}
```

## DeclaredProcessingRecord

```json
{
  "record_id": "dp_001",
  "technology": [],
  "provider": [],
  "data_categories": [],
  "purposes": [],
  "recipients": [],
  "legal_basis": [],
  "retention": [],
  "international_transfers": [],
  "source": {
    "url": "https://example.com/privacy",
    "document_type": "privacy_policy",
    "page_title": "Política de privacidad"
  }
}
```

### Hechos V1

| Campo | Representa |
|---|---|
| `technology` | Tecnología, servicio o mecanismo declarado |
| `provider` | Proveedor o tercero asociado al tratamiento |
| `data_categories` | Datos o categorías de datos declaradas |
| `purposes` | Finalidades declaradas |
| `recipients` | Destinatarios o categorías de destinatarios declarados |
| `legal_basis` | Base o fundamento declarado para el tratamiento |
| `retention` | Plazo, evento o criterio de conservación declarado |
| `international_transfers` | Transferencia internacional declarada y, cuando esté expresada en la misma unidad semántica, destino o garantía asociada |

V1 no agrega conclusiones de cumplimiento, riesgo o suficiencia jurídica.

## Fact

Cada hecho conserva el valor expresado por la fuente y, cuando corresponda, una normalización separada.

```json
{
  "value": "medición estadística del tráfico",
  "normalized_value": "analytics",
  "status": "supported",
  "evidence": {
    "text": "Utilizamos esta herramienta para la medición estadística del tráfico.",
    "source_url": "https://example.com/privacy"
  }
}
```

### `value`

Representación fiel del hecho declarado por el documento. No debe sustituirse por una conclusión del extractor.

### `normalized_value`

Representación canónica opcional para comparación determinista. Debe ser `null` cuando no exista una normalización suficientemente respaldada.

La normalización no reemplaza `value` ni su evidencia.

### `status`

V1 admite únicamente:

- `supported`: la evidencia respalda suficientemente el hecho extraído;
- `ambiguous`: existe evidencia relacionada, pero no permite estructurar el hecho de manera inequívoca.

`not_found` no se serializa como un `Fact`. Una colección vacía significa que el extractor no produjo un hecho de ese tipo dentro del alcance analizado.

La ausencia de un hecho no demuestra que la práctica correspondiente no exista.

### `evidence`

Todo hecho debe conservar:

- `text`: fragmento mínimo suficiente que respalda el hecho;
- `source_url`: URL pública de donde proviene el fragmento.

Un hecho sin evidencia atribuible no puede tener estado `supported`.

## Source

Cada record conserva la procedencia documental:

- `url`: URL pública inspeccionada;
- `document_type`: tipo documental identificado, por ejemplo `privacy_policy`, `cookie_policy` u `other_public_document`;
- `page_title`: título observable, cuando exista.

La fuente describe procedencia. No implica que el documento sea jurídicamente suficiente.

## Ejemplo

Fuente pública:

> Utilizamos Google Analytics para obtener estadísticas sobre el uso de nuestro sitio. La información puede ser tratada por Google.

Salida conceptual:

```json
{
  "schema_version": "declared_processing/v1",
  "records": [
    {
      "record_id": "dp_001",
      "technology": [
        {
          "value": "Google Analytics",
          "normalized_value": "google_analytics",
          "status": "supported",
          "evidence": {
            "text": "Utilizamos Google Analytics para obtener estadísticas sobre el uso de nuestro sitio.",
            "source_url": "https://example.com/privacy"
          }
        }
      ],
      "provider": [
        {
          "value": "Google",
          "normalized_value": "google",
          "status": "supported",
          "evidence": {
            "text": "La información puede ser tratada por Google.",
            "source_url": "https://example.com/privacy"
          }
        }
      ],
      "data_categories": [],
      "purposes": [
        {
          "value": "obtener estadísticas sobre el uso de nuestro sitio",
          "normalized_value": "analytics",
          "status": "supported",
          "evidence": {
            "text": "Utilizamos Google Analytics para obtener estadísticas sobre el uso de nuestro sitio.",
            "source_url": "https://example.com/privacy"
          }
        }
      ],
      "recipients": [],
      "legal_basis": [],
      "retention": [],
      "international_transfers": [],
      "source": {
        "url": "https://example.com/privacy",
        "document_type": "privacy_policy",
        "page_title": "Política de privacidad"
      }
    }
  ]
}
```

## Separación respecto de observación técnica

Este contrato representa únicamente declaraciones públicas.

La observación técnica debe conservar un contrato separado, por ejemplo:

```json
{
  "kind": "cookie",
  "identifier": "_ga",
  "source": "http_set_cookie",
  "page_url": "https://example.com/",
  "evidence": "..."
}
```

La asociación de un identificador técnico con una tecnología o proveedor conocido pertenece a una capa determinista de normalización tecnológica. No debe inventarse dentro del extractor semántico.

PRV-202 podrá comparar posteriormente:

**hecho técnico observado → normalización tecnológica → declaración pública estructurada**

## Invariantes

El extractor no debe producir campos como:

- `compliant`;
- `risk` o `severity`;
- `score`;
- `recommendation`;
- `requires_consent`;
- `requires_banner`;
- `necessary_cookie`;
- `tracking_cookie` como conclusión jurídica;
- `legal_basis_correct`;
- `policy_complete`;
- estados de controles PRV.

Tampoco debe crear un clasificador semántico específico por control cuando el hecho pueda representarse mediante este contrato común.

## Reutilización prevista

El contrato puede alimentar, entre otros, hechos requeridos por:

- PRV-007: categorías de datos;
- PRV-008: finalidades;
- PRV-009: bases declaradas;
- PRV-010: destinatarios o terceros;
- PRV-012: conservación;
- PRV-202: correspondencia entre tecnologías observadas e información pública;
- futuros controles documentales de transferencias internacionales.

Que un control consuma estos hechos no implica que deba cambiar inmediatamente su implementación actual.

## Gate previo a implementación

Antes de implementar el extractor se debe probar el contrato con un conjunto pequeño de fragmentos públicos difíciles, orientado exclusivamente a validar representación.

El gate no mide todavía accuracy del extractor. Debe comprobar que:

1. pueden preservarse relaciones entre tecnología, proveedor, finalidad y demás hechos;
2. la evidencia puede atribuirse a cada hecho sin perder trazabilidad;
3. la ambigüedad puede representarse sin forzar una conclusión;
4. una ausencia puede mantenerse como colección vacía sin convertirla en una conclusión negativa;
5. los casos reales no exigen introducir excepciones específicas de PRV-202.

Si el contrato necesita cambios estructurales para representar esos casos, se ajusta antes de congelar `declared_processing/v1`.
