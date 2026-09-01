# W2.2b.2-QA - calibración de evidencia estructurada por formulario

## Estado

**CALIBRATION BLOCKED**

La calibración no se ejecutó. El entorno de trabajo no tenía un remoto Git
configurado ni una sesión autenticada de GitHub CLI, por lo que no fue posible
publicar una rama temporal ni iniciar el workflow de GitHub Actions requerido por
esta QA. La comprobación previa `gh auth status` devolvió `You are not logged into
any GitHub hosts`.

De acuerdo con la regla de no inventar resultados, este documento no presenta
observaciones, revisiones manuales ni métricas como si se hubieran obtenido de
sitios reales. No se sustituyó la calibración por fixtures sintéticos ni por una
ejecución local.

## Línea base

| Campo | Valor |
|---|---|
| Fecha | 2026-09-01 |
| Main SHA previsto | `194fc5662154b4d6342314bb332043f907a17ea8` |
| Evidence Contract interno | `v0.2` |
| `framework_version` | `0.2` |
| `scoring_version` | `0.1` |
| `actions_version` | `2` |
| Producción modificada | No |
| PRV-103 implementado | No |

## Metodología prevista

La ejecución debía usar exclusivamente un workflow temporal de GitHub Actions y
el pipeline actual del Web Inspector. Para cada página pública, el runner debía
obtener HTML sin interactuar con formularios y ejecutar `extract_page(...)` y/o
`build_evidence(...)` sin modificar el extractor.

El artifact debía contener únicamente información sanitizada por formulario:

- identificador del caso, sector, hostname y URL sin query string;
- índice del formulario;
- `heading`, `legend`, `introductory_text` y `submit_text`;
- método, cantidad y tipos de campos, nombres minimizados y cantidad de
  checkboxes;
- como máximo, una muestra limitada de texto cercano para resolver una revisión
  ambigua.

No debía contener HTML, actions completas, query strings, cookies, headers,
credenciales, tokens, bodies ni valores de usuario. No se debía enviar ningún
formulario ni acceder a zonas autenticadas.

Una revisión manual independiente debía responder, para cada valor, si el texto
pertenecía realmente al formulario, sin evaluar todavía la claridad de su
finalidad y sin clasificarlo como `concrete`, `generic` o `none`.

## Ejecución de GitHub Actions

| Elemento | Resultado |
|---|---|
| Workflow ejecutado | No |
| Run URL | No disponible |
| Artifact | No generado |
| Causa del bloqueo | Sin remoto Git configurado y GitHub CLI sin autenticar |

El bloqueo ocurrió antes de publicar el workflow temporal. Por ello no se creó un
run y no hubo artifact que descargar o revisar. Tampoco se creó un runner temporal
en la versión final.

## Sitios

Los candidatos previstos cubrían e-commerce, servicios profesionales, educación,
salud, SaaS/tecnología y microempresa/sitio simple. Beardbrand, Benesch y Wicked
Grounds se consideraban candidatos conocidos, con reemplazos a seleccionar en el
run si algún sitio no aportaba evidencia suficiente.

| Métrica | Resultado |
|---|---:|
| Sitios previstos | Aproximadamente 6 |
| Sitios intentados por el workflow | 0 |
| Sitios diagnosticados | 0 |
| Formularios revisados | 0 |

Ningún candidato se marca como intentado: sin ejecución del workflow no existe
una respuesta pública observada por el pipeline que permita atribuir éxito, 403,
robots, TLS, WAF o timeout a un sitio.

## Formularios y matriz de resultados

No existen filas de resultados porque no se obtuvo evidencia real mediante el
entorno requerido.

| Case | Sector | Site | Form | heading | heading review | legend | legend review | intro | intro review | submit | submit review | Observation |
|---|---|---|---:|---|---|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — | — | — | — | — | — | Calibración bloqueada antes del run |

## Resumen de revisiones

| Métrica | Resultado |
|---|---:|
| Formularios revisados | 0 |
| Asociaciones `heading` revisadas | 0 |
| Asociaciones `legend` revisadas | 0 |
| Asociaciones `introductory_text` revisadas | 0 |
| Asociaciones `submit_text` revisadas | 0 |
| Headings correctos | 0 |
| Legends correctas | 0 |
| Intros correctas | 0 |
| Submits correctos | 0 |
| `missed_valid_context` | 0 observados |
| Casos inciertos | 0 observados |

Los ceros indican ausencia de observaciones, no validación satisfactoria.

## Fenómenos estructurales

No fue posible confirmar naturalmente ninguno de los fenómenos objetivo, incluidos
dos formularios cercanos, privacy link, wrapper complejo, texto posterior,
variantes de submit o legend dentro de fieldset. La cobertura permanece pendiente
de una ejecución real y no se infiere de tests sintéticos.

## Discrepancias

No hay discrepancias clasificables porque no hubo formularios observados. En
particular, los siguientes valores no pueden interpretarse como una comprobación
de ausencia:

| Tipo | Observados |
|---|---:|
| `cross_form_bleed` | 0 |
| `wrong_heading` | 0 |
| `wrong_intro` | 0 |
| `privacy_text_as_context` | 0 |
| `distant_text_association` | 0 |
| `following_text_association` | 0 |
| `nested_wrapper_ambiguity` | 0 |
| `submit_misclassification` | 0 |
| `legend_misclassification` | 0 |
| `missed_valid_context` | 0 |
| `technical_limitation` | 1 (entorno de ejecución) |
| `manual_uncertain` | 0 |

## Precisión por campo

`association_precision` se define como asociaciones correctas divididas por todas
las asociaciones no nulas revisadas. Al no existir asociaciones revisadas, el
denominador es cero y ninguna precisión es calculable.

| Campo | Correctas | No nulas revisadas | `association_precision` |
|---|---:|---:|---|
| `heading` | 0 | 0 | N/A |
| `legend` | 0 | 0 | N/A |
| `introductory_text` | 0 | 0 | N/A |
| `submit_text` | 0 | 0 | N/A |

## Contamination review

La contamination review no se ejecutó. En consecuencia,
`critical_false_associations`, `cross_form_bleed`,
`privacy_text_as_context` y `following_text_association` quedan **no evaluados**;
no se reportan como cero validado.

## Missing evidence

No se puede distinguir entre una omisión conservadora del extractor y contexto
válido no capturado sin evidencia real y revisión manual. Por eso no se atribuyen
casos `missed_valid_context` a ningún sitio o formulario.

## No tuning y alcance

No se modificaron el extractor, modelos, adapter, evaluator, catálogos, frontend,
API, base de datos ni producción. Tampoco se modificaron límites o heurísticas, se
implementó PRV-103 o se inició W2.2b.3. Las versiones de Evidence Contract,
framework, scoring y actions permanecen sin cambios.

## Limpieza

| Elemento temporal | Estado final |
|---|---|
| `.github/workflows/privacy-form-evidence-calibration.yml` | Ausente |
| Runner temporal | Ausente |

## Conclusión

**CALIBRATION BLOCKED**

No corresponde clasificar esta QA como **PASS**, **PASS WITH OBSERVATIONS** ni
**NEEDS FIX**: no se ejecutó el método requerido y, por tanto, no existe una muestra
con la que aplicar esos criterios. En particular, no puede afirmarse que
`critical_false_associations` sea cero.

## Recomendación

Reanudar W2.2b.2-QA en un entorno con un remoto de `rodrigo-nodo/mininode` y
credenciales que permitan publicar una rama y ejecutar GitHub Actions. Ejecutar
entonces el workflow temporal, revisar independientemente entre 10 y 15 formularios
de aproximadamente seis sitios, descargar el artifact sanitizado, completar esta
matriz con resultados reales y eliminar el workflow y runner antes de cerrar el PR.

No modificar heurísticas ni implementar PRV-103 durante esa reanudación.
