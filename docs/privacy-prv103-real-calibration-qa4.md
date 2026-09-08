# W2.2b.3-QA4 - holdout final independiente de PRV-103 v0.6

## Estado

**NEEDS FIX**

QA4 valida PRV-103 sobre framework `0.6` con un holdout nuevo, sin modificar producción ni ajustar reglas durante la medición.

## Línea base congelada

| Campo | Valor |
|---|---|
| Product base SHA | `af45be30224a196b153b50c11edfd2dcc9072bd9` |
| `framework_version` | `0.6` |
| `scoring_version` | `0.1` |
| Controles | 21 |
| Producción modificada durante QA4 | No |
| Tuning durante QA4 | Prohibido |

## Holdout y cobertura

La muestra se seleccionó antes de observar las clasificaciones productivas.

Primera muestra congelada:
- Chile: 60 organizaciones;
- Latinoamérica: 20;
- internacional: 20.

Run `34239972865`: **SUCCESS**.

| Lote | Sitios intentados | Sitios con páginas | HIGH raw | MEDIUM raw | HIGH deduplicados |
|---|---:|---:|---:|---:|---:|
| Chile | 60 | 42 | 13 | 4 | 12 |
| Latinoamérica | 20 | 13 | 7 | 0 | 7 |
| Internacional | 20 | 16 | 3 | 0 | 1 |
| **Total** | **100** | **71** | **23** | **4** | **20** |

Como el objetivo predefinido era al menos 30 formularios HIGH deduplicados, antes de abrir los artifacts internos se congeló una extensión de 50 organizaciones nuevas:
- Chile: 30;
- Latinoamérica: 10;
- internacional: 10.

Run `34240888724`: **SUCCESS**.

| Métrica extensión | Resultado |
|---|---:|
| Sitios intentados | 50 |
| Sitios con páginas | 38 |
| Formularios personales raw | 32 |
| HIGH raw | 30 |
| MEDIUM raw | 2 |
| HIGH deduplicados | 17 |

Muestra final:

| Métrica | Resultado |
|---|---:|
| Sitios intentados | **150** |
| Sitios con páginas | **109** |
| HIGH deduplicados adjudicados | **37** |

La búsqueda de casos se detuvo al superar el objetivo práctico de 30 HIGH deduplicados.

Las listas exactas de organizaciones usadas quedan registradas en los scripts QA4 de este PR para impedir su reutilización como futuro holdout independiente.

## Ejecución

Se utilizó el pipeline productivo real:
- `WebFetcher`;
- extracción productiva;
- `build_evidence`;
- `run_privacy_diagnostic`;
- `_personal_form`;
- `_form_purpose_signal`.

Solo se realizó inspección pública y pasiva mediante GET.

No se enviaron formularios, introdujeron datos, ejecutaron POST, autenticaron sesiones, crearon cuentas ni eludieron protecciones.

## Deduplicación

La muestra principal considera formularios personales `HIGH`.

Se deduplicaron únicamente formularios de la misma organización con evidencia estructurada idéntica en:
- `heading`;
- `legend`;
- `introductory_text`;
- `submit_text`.

## Referencia independiente

El Reviewer recibió únicamente un paquete ciego con los 37 casos y estos cuatro campos:
- `heading`;
- `legend`;
- `introductory_text`;
- `submit_text`.

No recibió nombre del sitio, URL, campos del formulario, resultado de PRV-103 ni clasificación automática. No revisó el PR ni el repositorio antes de adjudicar.

Clases permitidas:
- `concrete`;
- `generic`;
- `none`;
- `unknown`.

Solo después de recibir las 37 etiquetas del Reviewer se abrieron los artifacts internos y se compararon con PRV-103.

## Criterios congelados antes del resultado

### PASS
- `exact_class_agreement >= 80%`;
- `concrete_recall >= 60%`;
- `false_concrete_promotions = 0`;
- `false_adverse_none = 0`;
- sin errores críticos de asociación o consolidación.

### PASS WITH OBSERVATIONS
- `exact_class_agreement >= 65%`;
- `concrete_recall >= 45%`;
- mantener las condiciones de seguridad;
- errores restantes conservadores y no sistemáticos.

### NEEDS FIX
Aplica, entre otros, si:
- `exact_class_agreement < 65%` con patrón sistemático;
- `concrete_recall < 45%` con omisiones generalizables;
- existe falsa promoción a `concrete`;
- existe falsa conclusión adversa `none` relevante;
- existe error crítico de asociación o consolidación.

## Resultado de la adjudicación ciega

Distribución:

| Clase | Reviewer | Producto |
|---|---:|---:|
| concrete | 15 | 2 |
| generic | 14 | 14 |
| none | 0 | 0 |
| unknown | 8 | 21 |
| **Total** | **37** | **37** |

Matriz Reviewer vs producto:

| Reviewer \\ Producto | concrete | generic | unknown | Total |
|---|---:|---:|---:|---:|
| concrete | 1 | 2 | 12 | 15 |
| generic | 1 | 11 | 2 | 14 |
| unknown | 0 | 1 | 7 | 8 |
| **Total** | **2** | **14** | **21** | **37** |

Métricas:

| Métrica | Resultado |
|---|---:|
| Exact class agreement | **19/37 = 51,4%** |
| Concrete recall | **1/15 = 6,7%** |
| False concrete promotions | **1** |
| False adverse none | **0** |
| Missed concrete | **14** |
| Producto `unknown` con Reviewer `concrete/generic` | **14** |

Discrepancias principales:

| Tipo | Casos |
|---|---|
| Producto `unknown`, Reviewer `concrete` | CHILE-002, CHILE-003, CHILE-007, CHILE-008, CHILE-009, CHILE-010, LATAM-003, LATAM-004, EXTENSION-004, EXTENSION-008, EXTENSION-009, EXTENSION-015 |
| Producto `generic`, Reviewer `concrete` | CHILE-006, LATAM-005 |
| Producto `concrete`, Reviewer `generic` | EXTENSION-002 |
| Producto `unknown`, Reviewer `generic` | EXTENSION-006, EXTENSION-017 |
| Producto `generic`, Reviewer `unknown` | INTL-001 |

## Interpretación

La versión 0.6 mejora una dimensión importante respecto de ciclos anteriores: en esta muestra no aparece ninguna falsa conclusión adversa `none`.

Sin embargo, el comportamiento quedó excesivamente conservador hacia `unknown`:
- 21 de 37 casos fueron clasificados por el producto como `unknown`;
- 14 de esos 21 fueron considerados `concrete` o `generic` por el Reviewer;
- 14 de los 15 casos `concrete` del Reviewer no fueron reconocidos como `concrete` por el producto.

Además existe una falsa promoción a `concrete` en EXTENSION-002.

Por tanto, QA4 falla simultáneamente los umbrales de acuerdo exacto, concrete recall y una condición de seguridad.

## Decisión

**NEEDS FIX**.

PRV-103 no se considera cerrado en framework `0.6`.

No corresponde cerrar todavía Formularios como V1 estable.

## No tuning

Durante QA4 no se modificaron:
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

## Siguiente paso

Mergear este PR únicamente como registro de QA4 con resultado **NEEDS FIX**.

La corrección debe realizarse después en un PR separado y pequeño, usando estas discrepancias para diagnóstico/tuning. Si se ejecuta nuevamente QA independiente después de la corrección, debe utilizarse un holdout nuevo que excluya todos los sitios de QA4.
