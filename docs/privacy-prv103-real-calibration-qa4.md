# W2.2b.3-QA4 - holdout final independiente de PRV-103 v0.6

## Estado

**PENDIENTE DE ADJUDICACIÓN CIEGA**

Este QA valida PRV-103 sobre framework `0.6` sin modificar producción ni ajustar reglas durante la medición.

## Línea base congelada

| Campo | Valor |
|---|---|
| Product base SHA | `af45be30224a196b153b50c11edfd2dcc9072bd9` |
| `framework_version` | `0.6` |
| `scoring_version` | `0.1` |
| Controles | 21 |
| Producción modificada durante QA4 | No |
| Tuning durante QA4 | Prohibido |

La rama de QA parte exactamente desde ese SHA de `main`. Los únicos cambios permitidos durante QA4 son infraestructura temporal de medición y este registro documental.

## Holdout inicial congelado

Se definieron 100 organizaciones nuevas antes de observar resultados:

- Chile: 60;
- Latinoamérica: 20;
- internacional: 20.

La lista exacta quedó congelada en `.github/scripts/privacy_prv103_qa4.py` antes de la primera ejecución.

Se excluyeron organizaciones utilizadas en:

- W2.2b.2-QA;
- PRV-103 QA1;
- PRV-103 QA2;
- PRV-103 QA3;
- regression/tuning derivados de esos ciclos.

No se reemplaza una organización por entregar un resultado inconveniente. Los fallos de acceso, bloqueos o ausencia de formularios se registran como parte natural del holdout.

## Primera ejecución - cobertura

Run: `34239972865` - **SUCCESS**.

En esta etapa solo se revisaron métricas de cobertura; no se abrió ni examinó la clasificación productiva de PRV-103.

| Lote | Sitios intentados | Sitios con páginas | HIGH raw | MEDIUM raw | HIGH deduplicados |
|---|---:|---:|---:|---:|---:|
| Chile | 60 | 42 | 13 | 4 | 12 |
| Latinoamérica | 20 | 13 | 7 | 0 | 7 |
| Internacional | 20 | 16 | 3 | 0 | 1 |
| **Total** | **100** | **71** | **23** | **4** | **20** |

El objetivo predefinido era al menos 30 formularios HIGH deduplicados. Como los 100 sitios produjeron 20, la muestra no se cerró en ese punto.

## Extensión congelada antes de revisar clasificaciones

Antes de abrir los artifacts internos o revisar cualquier `product_purpose`, se congeló una extensión de **50 organizaciones nuevas**:

- 30 Chile;
- 10 Latinoamérica;
- 10 internacionales.

La extensión priorizó sectores con interacción pública frecuente - inmobiliario, automotriz, seguros, educación y software/servicios - para aumentar la probabilidad de observar formularios. Las organizaciones se fijaron antes de ejecutar y no se sustituyeron según el resultado.

La lista exacta quedó congelada en `.github/scripts/privacy_prv103_qa4_extension.py`.

Run de extensión: `34240888724` - **SUCCESS**.

| Métrica extensión | Resultado |
|---|---:|
| Sitios intentados | 50 |
| Sitios con páginas | 38 |
| Formularios personales raw | 32 |
| HIGH raw | 30 |
| MEDIUM raw | 2 |
| HIGH deduplicados | 17 |

## Cobertura final antes de adjudicación

| Métrica | Resultado |
|---|---:|
| Sitios intentados | **150** |
| Sitios con páginas | **109** |
| HIGH deduplicados | **37** |

El objetivo práctico congelado de al menos 30 HIGH deduplicados quedó superado. La búsqueda de casos se detiene aquí.

Hasta este punto no se inspeccionaron las clases productivas contenidas en los artifacts internos.

## Ejecución

Se usa el pipeline productivo real:

- `WebFetcher`;
- extracción productiva;
- `build_evidence`;
- `run_privacy_diagnostic`;
- `_personal_form`;
- `_form_purpose_signal`.

Solo se permite inspección pública y pasiva mediante GET.

No se:

- envían formularios;
- introducen datos;
- ejecutan POST;
- autentican sesiones;
- crean cuentas;
- eluden protecciones.

## Deduplicación

Para la muestra principal se consideran formularios personales `HIGH`.

Se deduplican únicamente formularios de la misma organización con evidencia estructurada idéntica en:

- `heading`;
- `legend`;
- `introductory_text`;
- `submit_text`.

La muestra final para adjudicación contiene **37 formularios HIGH deduplicados**.

## Referencia independiente

El Reviewer recibe un paquete ciego que contiene únicamente:

- `heading`;
- `legend`;
- `introductory_text`;
- `submit_text`.

No recibe:

- nombre del sitio;
- URL;
- campos del formulario;
- resultado de PRV-103;
- clasificación automática.

Debe clasificar cada caso como:

- `concrete`;
- `generic`;
- `none`;
- `unknown`.

Después se compara esa referencia con la clasificación productiva.

## Criterios congelados

### PASS

Requiere:

- `exact_class_agreement >= 80%`;
- `concrete_recall >= 60%`;
- `false_concrete_promotions = 0`;
- `false_adverse_none = 0`;
- sin errores críticos de asociación o consolidación.

### PASS WITH OBSERVATIONS

Requiere:

- `exact_class_agreement >= 65%`;
- `concrete_recall >= 45%`;
- mantener las condiciones de seguridad;
- errores restantes conservadores y no sistemáticos.

### NEEDS FIX

Aplica si ocurre, entre otros:

- `exact_class_agreement < 65%` con patrón sistemático;
- `concrete_recall < 45%` con omisiones generalizables;
- falsa promoción a `concrete`;
- falsa conclusión adversa `none` relevante;
- error crítico de asociación o consolidación.

## Regla de no tuning

Durante QA4 no se modifican:

- `_FORM_PURPOSE_*`;
- `_form_purpose_signal(...)`;
- `_form_purpose_evidence(...)`;
- regex;
- listas semánticas;
- precedencia;
- confidence;
- extractor;
- evaluator;
- catálogo;
- scoring.

Si QA4 termina `NEEDS FIX`, cualquier corrección se realizará después en un PR separado y requerirá un nuevo holdout si se vuelve a ejecutar QA independiente.
