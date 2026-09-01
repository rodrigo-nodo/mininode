# W2.2b.2-QA - calibración de evidencia estructurada por formulario

## Resultado

**PASS WITH OBSERVATIONS**

La calibración real de `heading`, `legend`, `introductory_text` y `submit_text` se ejecutó mediante GitHub Actions sobre ocho sitios públicos y 19 formularios observados.

El objetivo fue validar asociación estructural, no clasificar finalidad.

Resultado principal:

- 0 asociaciones falsas críticas;
- 0 `cross_form_bleed`;
- 0 texto de privacidad usado como contexto;
- 0 texto posterior asociado incorrectamente;
- 100% de precisión sobre asociaciones no nulas revisadas en los cuatro campos;
- 1 caso claro de `missed_valid_context`, aceptable bajo la política precisión > recall.

La clasificación es **PASS WITH OBSERVATIONS** porque el extractor omitió al menos un contexto manualmente válido por diseño conservador y algunos sitios no aportaron todos los fenómenos objetivo de forma natural.

## Línea base

| Campo | Valor |
|---|---|
| Fecha | 2026-09-01 |
| Main SHA evaluado | `194fc5662154b4d6342314bb332043f907a17ea8` |
| Evidence Contract interno | `v0.2` |
| `framework_version` | `0.2` |
| `scoring_version` | `0.1` |
| `actions_version` | `2` |
| Controles | 20 |
| PRV-103 implementado | No |
| Producción modificada | No |

## Ejecución

La ejecución local del entorno Codex no tenía autenticación suficiente para publicar y ejecutar el workflow. Por ello la calibración se ejecutó directamente mediante un workflow temporal en la rama del PR.

Run:

https://github.com/rodrigo-nodo/mininode/actions/runs/33529438209

Artifact:

- nombre: `privacy-form-evidence-calibration`
- artifact id: `9809098315`
- retención: 7 días

El workflow temporal fue eliminado después de documentar los resultados.

## Metodología

El runner temporal utilizó el Web Inspector actual para obtener HTML público y ejecutó `extract_page(...)` sin modificar el extractor ni sus límites.

No se enviaron formularios ni se introdujeron datos personales.

Por formulario se almacenó de forma sanitizada:

- URL de origen sin query string;
- hostname;
- índice;
- `heading`;
- `legend`;
- `introductory_text`;
- `submit_text`;
- método;
- tipos/nombres/labels minimizados de campos;
- cantidad de checkboxes;
- scheme/hostname del action;
- una muestra limitada de estructura DOM para revisión independiente.

No se almacenaron cookies, headers, bodies enviados, valores de usuarios, credenciales, tokens ni actions completas.

La revisión manual respondió únicamente:

> ¿El texto extraído pertenece realmente a este formulario?

No evaluó todavía si el texto constituye una finalidad concreta o genérica.

## Sitios

| Caso | Sector | Sitio | Páginas observadas | Formularios |
|---|---|---|---:|---:|
| C01 | E-commerce | `beardbrand.com` | 1 | 3 |
| C02 | Servicios profesionales | `beneschlaw.com` | 2 | 5 |
| C03 | Educación | `harvard.edu` | 2 | 0 |
| C04 | Salud | `nhs.uk` | 1 | 1 |
| C05 | SaaS/tecnología | `about.gitlab.com` | 3 | 3 |
| C06 | Microempresa/sitio simple | `wickedgrounds.com` | 2 | 1 |
| C07 | Servicios web | `djangoproject.com` / `djangoproject.com` | 2 | 3 |
| C08 | Tecnología | `mozilla.org` | 2 | 3 |

Resumen:

| Métrica | Resultado |
|---|---:|
| Sitios intentados | 8 |
| Sitios con páginas observadas | 8 |
| Formularios revisados | 19 |
| Errores de fetch en casos finales | 0 |

## Asociaciones revisadas

| Campo | Asociaciones no nulas | Correctas | Incorrectas | Precisión |
|---|---:|---:|---:|---:|
| `heading` | 1 | 1 | 0 | 100% |
| `legend` | 3 | 3 | 0 | 100% |
| `introductory_text` | 2 | 2 | 0 | 100% |
| `submit_text` | 12 | 12 | 0 | 100% |

La precisión se calcula solo sobre asociaciones no nulas revisadas.

Los valores `None` no se consideran fallos salvo cuando existe contexto manualmente claro que el extractor omitió.

## Casos representativos

### Mozilla - heading interno

Formulario newsletter:

- `heading = "Recibe noticias de Firefox"`;
- el heading aparece como `h3` dentro del mismo formulario;
- asociación manual: correcta.

No existe contaminación con el bloque posterior de confirmación.

### Benesch - legend interno

Se observaron formularios con:

- `legend = "Contact us Form"`;
- `legend = "Footer - Get In Touch"`.

Los legends pertenecen al mismo formulario y fueron asociados correctamente.

### GitLab - introductory_text externo

Dos formularios estructurales mostraron:

- `introductory_text = "All fields required"`.

La frase aparece como hermano inmediato anterior del formulario, sin link, heading ni controles anidados.

La asociación estructural es correcta.

Este QA no decide si "All fields required" expresa finalidad; esa clasificación pertenece a PRV-103.

### Django - omisión conservadora válida

El formulario de contacto tiene un párrafo manualmente claro:

> "This contact form is for the Django Software Foundation..."

Sin embargo, entre ese párrafo y el formulario existen varios párrafos con enlaces.

El extractor devuelve:

- `introductory_text = None`.

Clasificación:

- `missed_valid_context`.

Esto es coherente con la regla de precisión > recall: el extractor corta la búsqueda frente a bloques con links y evita asociar texto más lejano.

No se recomienda ampliar la heurística a partir de este caso.

### Beardbrand - múltiples submits

El selector de país/región contiene múltiples botones submit.

`submit_text` conserva el orden DOM, elimina duplicados y trunca al límite configurado.

La asociación al formulario es correcta.

Observación: este caso demuestra que `submit_text` puede ser técnicamente correcto pero semánticamente ruidoso en formularios utilitarios. PRV-103 deberá depender de PRV-101 y no interpretar cualquier submit aislado como finalidad.

### Mozilla - submit con estado visual

El newsletter devuelve:

`submit_text = "Suscríbete ya Enviando"`.

Ambos textos están dentro del botón submit observado.

La asociación es correcta, aunque el texto incluye un estado visual adicional. Se registra como observación de calidad semántica futura, no como error de asociación.

## Contamination review

| Tipo | Observados |
|---|---:|
| `critical_false_associations` | 0 |
| `cross_form_bleed` | 0 |
| `wrong_heading` | 0 |
| `wrong_intro` | 0 |
| `privacy_text_as_context` | 0 |
| `distant_text_association` | 0 |
| `following_text_association` | 0 |
| `nested_wrapper_ambiguity` con falsa asociación | 0 |
| `submit_misclassification` | 0 |
| `legend_misclassification` | 0 |
| `missed_valid_context` | 1 |
| `manual_uncertain` | 0 |

## Fenómenos observados

Se observaron naturalmente:

- heading dentro del formulario;
- legend dentro del formulario;
- introductory text inmediatamente anterior;
- button submit;
- múltiples submit;
- formularios sin contexto estructurado;
- formularios cercanos en una misma página;
- formularios con estructura compleja;
- texto posterior que no fue asociado;
- formulario con contexto válido omitido por presencia de links intermedios.

No se observó evidencia de contaminación entre formularios.

No todos los fenómenos previstos aparecieron con una muestra positiva independiente; en particular, la muestra real fue limitada para wrappers externos complejos con heading y para `input type=submit` claramente aislado.

Los tests sintéticos continúan cubriendo esos casos.

## Missing evidence

Se registró un caso claro de `missed_valid_context` en Django.

Esto no invalida la calibración porque:

- no genera una asociación falsa;
- no introduce texto de otro formulario;
- no puede empeorar un resultado mediante evidencia incorrecta;
- PRV-103 será contextual y de peso cero;
- el diseño aprobado privilegia precisión sobre recall.

No se recomienda ampliar la ventana estructural ni cruzar bloques con links únicamente para capturar este caso.

## No tuning

No se modificaron durante la calibración:

- `extractor.py`;
- `models.py`;
- adapter;
- evaluator;
- catálogos;
- límites;
- scoring;
- frontend;
- API;
- BD.

No se implementó PRV-103.

Los resultados se documentaron después de la ejecución sin ajustar heurísticas sobre la misma muestra.

## Versionado

Se mantiene:

- Evidence Contract interno = `v0.2`;
- `framework_version = 0.2`;
- `scoring_version = 0.1`;
- `actions_version = 2`;
- controles = 20.

La QA no cambia comportamiento productivo.

## Conclusión

**PASS WITH OBSERVATIONS**

La evidencia estructurada por formulario es suficientemente confiable para servir como entrada a la siguiente etapa.

En 19 formularios reales y 8 sitios:

- 0 asociaciones falsas críticas;
- 0 contaminación entre formularios;
- 0 privacidad usada como contexto;
- 100% de precisión sobre asociaciones no nulas revisadas;
- 1 omisión conservadora claramente identificada.

La observación principal es de recall, no de precisión.

No existe evidencia que justifique modificar W2.2b.2 antes de avanzar.

## Recomendación

Cerrar W2.2b.2-QA con **PASS WITH OBSERVATIONS**.

El siguiente paso puede avanzar a W2.2b.3 - PRV-103 "Finalidad visible del formulario".

Mantener para PRV-103 los principios ya aprobados:

- dependencia PRV-101;
- control contextual;
- `score_weight = 0`;
- no inferir finalidad desde campos;
- clasificar `concrete / generic / none` solo desde evidencia estructurada asociada;
- tratar evidencia ausente o ambigua de forma conservadora;
- no convertir submit utilitario o texto técnico en una finalidad positiva por sí solo.
