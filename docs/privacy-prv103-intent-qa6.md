# PRV-103 Intent QA6 - holdout nuevo

**Resultado final: PASS**

## Objetivo

Validar en datos completamente nuevos si la arquitectura de `PRV-103 Intent LLM V2` mantiene la mejora observada en el experimento del PR #209 sin promociones inseguras a `concrete`.

La arquitectura evaluada no cambia:

```text
heading + legend + introductory_text + submit_text
  -> LLM identifica intención observable
  -> evidencia literal validada
  -> uncertain opcional
  -> Mininode mapea intención -> concrete/generic/none/unknown
```

## Línea base congelada

- Main SHA: `3db94b7c9775e0c23dfc6f2def1fa6de6e23c26c`.
- Modelo: `gpt-5.6-sol`.
- Prompt: `prv103-intent-v2-01`.
- Reasoning: `medium`.
- Taxonomía: `prv103-intents-v1`.
- Evidence Contract para adjudicación: únicamente `heading`, `legend`, `introductory_text`, `submit_text`.
- No se modifica producción, framework, scoring, extractor, adapter ni evaluator durante QA6.

## Independencia del holdout

Los candidatos de QA6 se fijaron antes de inspeccionar sus formularios y se filtraron contra evidencia histórica disponible de QA1-QA5, W2.2b.2, QA4/extension y tuning documentado. Además se excluyeron explícitamente los 100 candidatos preseleccionados de QA5.

No se sustituyeron sitios en función de la clase obtenida.

Solo se usó inspección pública y pasiva mediante GET. No se enviaron formularios, POST, login, creación de cuentas ni bypass.

## Muestra obtenida

| Métrica | Chile | LatAm | Internacional | Total |
|---|---:|---:|---:|---:|
| Candidatos congelados | 70 | 40 | 54 | 164 |
| Excluidos por histórico | 0 | 0 | 1 | 1 |
| Sitios intentados | 70 | 40 | 53 | 163 |
| Sitios con páginas | 55 | 29 | 44 | 128 |
| Formularios personales raw | 40 | 9 | 30 | 79 |
| HIGH raw | 34 | 6 | 30 | 70 |
| MEDIUM raw | 6 | 3 | 0 | 9 |
| **HIGH deduplicados** | **20** | **5** | **21** | **46** |

El objetivo mínimo era 30 HIGH deduplicados. Se recuperaron 46 y se adjudicaron los 46; no hubo subsampling.

## Referencia ciega

El paquete de referencia contenía exclusivamente:

- `blind_id`;
- `heading`;
- `legend`;
- `introductory_text`;
- `submit_text`.

La etiqueta de referencia se congeló **antes de abrir cualquier salida del LLM evaluado**. No se usaron fields, action URL, page title, nearby_text ni conocimiento externo del sitio.

Distribución congelada:

| Clase | Casos |
|---|---:|
| concrete | 13 |
| generic | 27 |
| none | 1 |
| unknown | 5 |
| **Total** | **46** |

La referencia fue una adjudicación ciega manual realizada en el chat PO. No hubo Reviewer independiente en esta ejecución; esto queda registrado explícitamente en `qa6_gold.json` y debe distinguirse de un QA con segunda parte independiente.

## Criterio congelado antes del modelo

### PASS

Debía cumplir **en ambos runs**:

- `false_concrete_promotions = 0`;
- `false_adverse_none = 0`;
- `invalid_outputs = 0`;
- `emitted_precision >= 90%`;
- `coverage >= 70%`;
- `accuracy >= 80%`;
- `concrete_recall >= 75%`;
- `class_stability >= 95%`.

### PASS WITH OBSERVATIONS

Debía preservar en ambos runs:

- 0 false concrete promotions;
- 0 false adverse none;
- 0 invalid outputs;

Y alcanzar en ambos runs al menos:

- emitted precision >= 90%;
- coverage >= 60%;
- accuracy >= 70%;
- concrete recall >= 65%;
- class stability >= 90%.

### NEEDS FIX

Cualquiera de estas condiciones bastaba:

- alguna falsa promoción a `concrete` en cualquiera de los dos runs;
- algún falso `none` adverso;
- salida inválida;
- métricas por debajo de PASS WITH OBSERVATIONS;
- patrón sistemático generalizable de error aunque un promedio quede sobre umbral.

## Ejecución

- GitHub Actions run oficial: `34302297149`.
- SHA de ejecución: `31036a73c7433486adf378e17163b42f35eb9e48`.
- Run 1: calidad oficial.
- Run 2: estabilidad.
- Workflow: SUCCESS.
- Tests del contrato y QA6: SUCCESS antes de inferencia.
- No hubo tuning entre runs ni después de observar run 1.

## Resultado

| Métrica | Run 1 | Run 2 |
|---|---:|---:|
| Exact accuracy | **100% (46/46)** | **100% (46/46)** |
| Coverage | **89,1%** | **89,1%** |
| Emitted precision | **100%** | **100%** |
| Concrete precision | **100%** | **100%** |
| Concrete recall | **100%** | **100%** |
| Generic precision | **100%** | **100%** |
| False concrete promotions | **0** | **0** |
| False adverse `none` | **0** | **0** |
| Invalid outputs | **0** | **0** |
| Unknown rate | 10,9% | 10,9% |

## Estabilidad

| Métrica | Resultado |
|---|---:|
| **Class stability** | **100%** |
| Intent stability | 93,5% |
| Uncertain stability | 97,8% |
| Evidence stability | **100%** |

No hubo ningún cambio de clase entre run 1 y run 2.

Hubo cuatro variaciones internas sin impacto en la clase final:

- `QA6_CHILE-019`: `specific_service_request` vs `appointment_booking`, ambos `concrete`;
- `QA6_INTL-006`: misma intención ambigua y clase `unknown`, con cambio de `uncertain`;
- `QA6_INTL-010`: dos intenciones de abstención distintas, clase `unknown` en ambos;
- `QA6_INTL-020`: dos intenciones de abstención distintas, clase `unknown` en ambos.

A diferencia del experimento del PR #209, no apareció el borde peligroso `generic -> concrete` al repetir la ejecución.

## Decisión

**PASS.**

Se cumplen todos los criterios congelados en ambos runs, incluido el gate principal de seguridad:

- 0 falsas promociones a `concrete`;
- 0 falsos `none` adversos;
- 0 salidas inválidas;
- class stability 100%.

Esto confirma una mejora material frente al enfoque de reglas y al nearest-intent por embeddings en un conjunto de sitios no utilizado en QA1-QA5 ni en los experimentos semánticos previos.

## Alcance de la conclusión

QA6 valida el enfoque bajo **validación ciega directa**, no bajo un Reviewer humano/ChatGPT independiente. Por tanto:

- el resultado justifica avanzar al diseño de integración o shadow mode en un PR separado;
- no modifica producción por sí mismo;
- si se quiere elevar el estándar antes de activar decisiones productivas, el mismo paquete ciego puede recibir una adjudicación independiente sin mostrarle los outputs de QA6.

No se realiza tuning sobre este holdout.
