# PRV-103 Semantic V1 - experimento offline

**Estado:** experimento de investigación. No integra un modelo en producción y no cambia framework, scoring, API, frontend, extractor, adapter ni evaluator.

## Pregunta

PRV-103 ha mostrado un techo con reglas crecientes: los últimos holdouts mantienen errores sistemáticos entre `concrete`, `generic` y `unknown`, y al aumentar recall aparecen falsas promociones a `concrete`.

Este experimento prueba si una representación semántica por **intenciones conocidas** puede mejorar esa frontera sin convertir el modelo en autoridad del control.

La arquitectura evaluada es:

```text
4 campos estructurados del formulario
    -> embedding multilingüe
    -> intención más cercana
    -> mapeo determinista intención -> clase
    -> abstención por score/margen
```

El modelo nunca decide qué clase de producto significa una intención: esa traducción está congelada en `intent_taxonomy.json`.

## Corpus

Se reutilizan únicamente holdouts ya consumidos:

- desarrollo: QA4, 37 formularios HIGH deduplicados;
- evaluación: QA5, 32 formularios HIGH deduplicados.

QA5 queda separado de QA4 y no se usa para elegir umbrales. Los casos contienen solo `heading`, `legend`, `introductory_text` y `submit_text`.

No se guardan URL, hostname, organización, fields, action URL, page title, `nearby_text` ni conocimiento externo.

`corpus.json` preserva además la predicción congelada de v0.7 en QA5 para comparar contra el último candidato rechazado, sin requerir que v0.7 exista en `main`.

## Modelo

Primer candidato semántico:

`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`

Se usa solo durante el experimento mediante dependencia temporal. No se agrega a `backend/requirements.txt` ni al runtime productivo.

## Taxonomía

La taxonomía separa intenciones como login, recuperación de contraseña, seguimiento, pago, cotización, cita, feedback, contacto, registro y suscripción. Cada intención mapea por código a una de las clases `concrete`, `generic`, `none` o `unknown`.

Las reglas actuales no se expanden dentro de este experimento.

## Abstención

El clasificador forzado siempre toma la intención con mayor similitud.

La variante selectiva puede devolver `unknown` si el score superior no alcanza `min_score` o la diferencia con la segunda intención no alcanza `min_margin`.

Los umbrales se eligen **solo con QA4** mediante una grilla congelada. Orden:

1. `false_concrete_promotions = 0`;
2. `false_adverse_none = 0`;
3. precisión de predicciones emitidas >= 90%;
4. maximizar cobertura;
5. desempatar por exact agreement.

QA5 no participa en esa elección.

## Métricas

Se reportan por separado: exact accuracy, coverage (`prediction != unknown`), emitted precision, concrete precision, concrete recall, generic precision, false concrete promotions, false adverse `none` y unknown rate.

La métrica principal deja de ser solo exact agreement: PRV-103 puede abstenerse.

## Criterio congelado antes de QA5

### A - PROMISING

La variante selectiva debe cumplir simultáneamente en QA5:

- `false_concrete_promotions = 0`;
- `false_adverse_none = 0`;
- `emitted_precision >= 90%`;
- `coverage >= 50%`;
- `accuracy >= 65%`;
- `concrete_recall >= 50%`.

Esto solo autoriza investigación/shadow; **no producción**.

### B - EXPLORATORY

Preserva seguridad y alcanza al menos `emitted_precision >= 85%` y `coverage >= 40%`, pero no todos los criterios A.

### C - NO MATERIAL VALUE

No alcanza una mejora útil con seguridad.

### D - RISKY

Cualquier falsa promoción a `concrete` o falsa conclusión adversa `none`.

## Ejecución

Tests sin modelo/red:

```bash
pytest -q backend/tests/domain_packs/privacy/prv103_semantic_benchmark/test_runner.py
```

Experimento con dependencia temporal:

```bash
pip install sentence-transformers
python backend/tests/domain_packs/privacy/prv103_semantic_benchmark/runner.py --output artifacts/prv103-semantic-v1.json
```

El workflow de medición es temporal y se elimina después de congelar el resultado.
