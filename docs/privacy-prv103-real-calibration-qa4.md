# W2.2b.3-QA4 - holdout final independiente de PRV-103 v0.6

## Estado

**EN EJECUCIÓN**

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

## Holdout congelado antes de ejecutar

Se definieron 100 organizaciones nuevas antes de observar resultados:

- Chile: 60;
- Latinoamérica: 20;
- internacional: 20.

La lista exacta está congelada en `.github/scripts/privacy_prv103_qa4.py` antes de la primera ejecución.

Se excluyeron organizaciones utilizadas en:

- W2.2b.2-QA;
- PRV-103 QA1;
- PRV-103 QA2;
- PRV-103 QA3;
- regression/tuning derivados de esos ciclos.

No se reemplazará una organización por entregar un resultado inconveniente. Los fallos de acceso, bloqueos o ausencia de formularios se registran como parte natural del holdout.

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

Los 100 sitios se ejecutan en tres lotes regionales paralelos.

## Deduplicación

Para la muestra principal se consideran formularios personales `HIGH`.

Se deduplican únicamente formularios de la misma organización con evidencia estructurada idéntica en:

- `heading`;
- `legend`;
- `introductory_text`;
- `submit_text`.

Objetivo práctico: al menos 30 formularios HIGH deduplicados entre los tres lotes.

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
