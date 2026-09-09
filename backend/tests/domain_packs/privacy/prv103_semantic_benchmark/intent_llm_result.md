# PRV-103 Intent LLM V2 - resultado

**Clasificación final: A - PROMISING**

El experimento muestra una mejora material de comprensión semántica frente a las reglas v0.7 y frente al nearest-intent por embeddings de Semantic V1. La arquitectura merece una validación independiente nueva, pero **no se integra en producción en este PR**.

## Ejecución oficial

| Campo | Valor |
|---|---|
| GitHub Actions run oficial | `34298293457` |
| Estado | SUCCESS |
| Modelo | `gpt-5.6-sol` |
| Prompt | `prv103-intent-v2-01` |
| Reasoning | `medium` |
| Corpus | `prv103-semantic-v1-2026-09-08` |
| Taxonomía | `prv103-intents-v1` |
| Casos | 69 |
| Run 1 | calidad oficial |
| Run 2 | estabilidad |
| Producción modificada | No |

Un intento técnico anterior (`34298241465`) falló en la colección de tests por falta de `PYTHONPATH` antes de iniciar cualquier inferencia. Se corrigió únicamente el path de importación del workflow; no cambió prompt, taxonomía, corpus, modelo, mapeo ni criterio. Ese intento no produjo predicciones y queda excluido.

## Resultado global - run 1

| Métrica | Resultado |
|---|---:|
| Exact accuracy | **66/69 = 95,7%** |
| Coverage | **55/69 = 79,7%** |
| Emitted precision | **98,2%** |
| Concrete precision | **100%** |
| Concrete recall | **96,6%** |
| Generic precision | **96,0%** |
| False concrete promotions | **0** |
| False adverse `none` | **0** |
| Invalid outputs | **0** |
| Unknown rate | 20,3% |

Distribución producto: concrete 28, generic 25, unknown 14, none 2.

Distribución gold: concrete 29, generic 26, unknown 12, none 2.

## Resultado por ciclo consumido

### QA4 - 37 casos

| Métrica | Resultado |
|---|---:|
| Exact accuracy | **91,9%** |
| Coverage | **73,0%** |
| Emitted precision | **96,3%** |
| Concrete precision | **100%** |
| Concrete recall | **93,3%** |
| False concrete promotions | **0** |
| False adverse `none` | **0** |

### QA5 - 32 casos

| Métrica | Resultado |
|---|---:|
| Exact accuracy | **100%** |
| Coverage | **87,5%** |
| Emitted precision | **100%** |
| Concrete recall | **100%** |
| False concrete promotions | **0** |
| False adverse `none` | **0** |

QA5 **no es un holdout independiente para este experimento**. Sus etiquetas y patrones ya habían sido consumidos en investigación previa, por lo que el 100% se interpreta solo como consistencia con el corpus conocido y no como estimación de generalización.

En esa misma muestra QA5, la baseline congelada v0.7 tenía 50,0% de exactitud, 50,0% de concrete recall y 2 falsas promociones a `concrete`.

## Tres discrepancias de run 1

| Caso | Gold | Resultado | Lectura |
|---|---|---|---|
| CHILE-005 | generic | unknown | abstención conservadora ante formulario genérico |
| LATAM-005 | concrete | generic | omisión de una finalidad específica de expansión/pagos |
| EXTENSION-007 | generic | unknown | abstención conservadora ante sugerencias/consultas |

No hubo promoción peligrosa a `concrete` ni conclusión adversa `none` incorrecta en el run oficial de calidad.

## Estabilidad - run 1 vs run 2

| Métrica | Resultado |
|---|---:|
| Class stability | **95,7%** |
| Intent stability | **98,6%** |
| Uncertain stability | **95,7%** |
| Evidence stability | **92,8%** |

Hubo tres cambios de clase entre ejecuciones:

- EXTENSION-007: `unknown -> generic`;
- EXTENSION-012: `generic -> unknown`;
- QA5-029: `generic -> concrete`.

El último es una observación de seguridad importante: en run 2, `Solicitar contato` fue interpretado como `specific_service_request` y promovido a `concrete`, mientras el gold es `generic`.

El protocolo congelado definió run 1 como calidad oficial y run 2 únicamente como estabilidad; A exige class stability >=95%, que se cumple. Por ello la clasificación formal permanece **A - PROMISING**. No obstante, esta variación demuestra que la seguridad de una única ejecución todavía debe validarse en datos nuevos antes de considerar integración.

## Uso observado

| Métrica | Run 1 | Run 2 |
|---|---:|---:|
| Llamadas | 69 | 69 |
| Input tokens | 86.064 | 86.064 |
| Output tokens | 5.802 | 6.004 |
| Reasoning tokens | 1.389 | 1.590 |
| Latencia total | 181,0 s | 160,0 s |
| Latencia media/caso | 2,62 s | 2,32 s |

El modelo resuelto informado por ambas ejecuciones fue `gpt-5.6-sol`.

Estas cifras corresponden al runner experimental secuencial y no son una estimación de arquitectura productiva optimizada.

## Aplicación del criterio congelado

A - PROMISING requería en run 1:

- 0 false concrete promotions -> **cumple**;
- 0 false adverse none -> **cumple**;
- 0 invalid outputs -> **cumple**;
- emitted precision >=90% -> **98,2%**;
- coverage >=70% -> **79,7%**;
- accuracy >=75% -> **95,7%**;
- concrete recall >=70% -> **96,6%**;
- class stability >=95% -> **95,7%**.

Resultado formal: **A - PROMISING**.

## Qué aprendimos

La separación propuesta funciona mejor que los caminos anteriores:

```text
texto visible
  -> LLM identifica intención
  -> evidencia literal validada
  -> uncertain opcional
  -> Mininode mapea intención -> clase
```

El modelo no necesita decidir directamente `concrete/generic/none/unknown`, y el contrato de evidencia evitó salidas inventadas en los 138 casos ejecutados entre ambas pasadas.

La principal limitación restante ya no parece ser comprensión semántica general. Es **estabilidad en bordes entre intención genérica y específica**, especialmente solicitudes de contacto/servicio.

## Decisión

**No integrar todavía.**

El siguiente paso recomendado es un QA independiente nuevo sobre sitios/casos no usados en QA1-QA5, Semantic V1 ni este experimento. Debe congelar antes del resultado criterios que traten cualquier falsa promoción a `concrete` en la ejecución evaluada como fallo de seguridad.

Solo si ese nuevo holdout confirma una frontera segura corresponde diseñar un shadow mode productivo o evaluar costo/latencia de integración.

No se realiza tuning posterior sobre QA4/QA5 en este PR.