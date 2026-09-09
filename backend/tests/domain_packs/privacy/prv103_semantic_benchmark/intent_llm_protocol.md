# PRV-103 Intent LLM V2 - protocolo experimental

**Estado:** protocolo congelado antes de ejecutar inferencia.

Este experimento no cambia producción. Evalúa si un LLM puede identificar la intención observable de un formulario mejor que reglas o nearest-intent por embeddings, manteniendo el mapeo final intención -> clase bajo control determinista de Mininode.

## Hipótesis

La arquitectura evaluada es:

```text
heading + legend + introductory_text + submit_text
    -> LLM elige una intención cerrada
    -> evidencia literal del input
    -> uncertain opcional
    -> mapeo determinista intención -> concrete/generic/none/unknown
```

El LLM **no devuelve directamente** `concrete`, `generic`, `none` ni `unknown` como decisión de producto. Solo selecciona una intención de `intent_taxonomy.json` y evidencia observable. Si marca `uncertain=true`, Mininode fuerza `unknown`.

## Datos

Se reutiliza el corpus ya consumido de PRV-103 Semantic V1:

- QA4: 37 casos;
- QA5: 32 casos;
- total: 69 casos.

Estos datos **no constituyen un nuevo holdout independiente**. QA4 y QA5 ya fueron usados en investigación previa; aquí sirven para comparar arquitectura y decidir si vale la pena avanzar a un holdout nuevo.

El modelo recibe únicamente:

- `heading`;
- `legend`;
- `introductory_text`;
- `submit_text`;
- catálogo cerrado de intenciones sin las clases de producto.

No recibe gold label, baseline v0.7, sitio, URL, campos del formulario, action URL, page title, nearby text ni conocimiento de la organización.

## Modelo y prompt

- Modelo: `gpt-5.6-sol`.
- Reasoning: `medium`.
- Prompt version: `prv103-intent-v2-01`.
- Structured Outputs estricto.
- `store=false`.

Reglas centrales del prompt:

1. elegir solo una intención del catálogo;
2. usar únicamente evidencia visible en los cuatro campos;
3. no inferir finalidad desde conocimiento externo;
4. contacto, registro o suscripción genéricos no se transforman en finalidad concreta sin un resultado explícito;
5. acciones ambiguas como `Buscar`, `Next`, `Start now` o equivalentes sin objeto reconocible deben permanecer ambiguas;
6. placeholders técnicos sin significado humano se consideran `technical_placeholder`;
7. ante insuficiencia o conflicto, `uncertain=true`.

## Evidencia

La salida incluye hasta cuatro pares `field + quote`.

El runner rechaza una salida si:

- la intención no existe en la taxonomía;
- el campo citado no pertenece a los cuatro permitidos;
- el campo citado está vacío;
- la cita no es un substring normalizado del campo original;
- existe evidencia duplicada por campo;
- la salida no respeta el esquema estricto.

Una salida inválida se trata como `unknown` y cuenta en estabilidad/operación como error de contrato.

## Mapeo determinista

`intent_taxonomy.json` sigue siendo la autoridad de `intent_id -> class`.

Regla adicional:

```text
uncertain = true -> unknown
```

Por tanto, el modelo puede comprender la intención, pero no controla directamente el estado semántico final de PRV-103.

## Ejecución y estabilidad

Se realizan dos ejecuciones idénticas:

- run 1: resultado oficial de calidad;
- run 2: solo estabilidad.

No se modifica prompt, taxonomía, corpus, modelo ni reglas entre ambas.

Se registra:

- estabilidad de intención;
- estabilidad de clase final;
- estabilidad de `uncertain`;
- estabilidad exacta de evidencia;
- tokens y latencia por ejecución.

## Métricas

Para run 1 se calculan:

- exact accuracy;
- coverage (`prediction != unknown`);
- emitted precision;
- concrete precision;
- concrete recall;
- generic precision;
- false concrete promotions;
- false adverse `none`;
- unknown rate;
- invalid outputs.

En QA5 se reporta además la baseline congelada v0.7 disponible en `corpus.json`.

## Criterio congelado antes de ejecutar

### A - PROMISING

Debe cumplir simultáneamente en los 69 casos:

- `false_concrete_promotions = 0`;
- `false_adverse_none = 0`;
- `invalid_outputs = 0`;
- `emitted_precision >= 90%`;
- `coverage >= 70%`;
- `accuracy >= 75%`;
- `concrete_recall >= 70%`.

Además, estabilidad de clase entre run 1 y run 2 >= 95%.

Un resultado A autoriza únicamente un siguiente experimento/holdout nuevo o shadow mode. No autoriza producción.

### B - EXPLORATORY

Mantiene las tres condiciones de seguridad/contrato (`0` false concrete, `0` false none, `0` invalid outputs), alcanza:

- `emitted_precision >= 85%`;
- `coverage >= 50%`;
- `accuracy >= 65%`;
- estabilidad de clase >= 90%;

pero no todos los criterios A.

### C - NO MATERIAL VALUE

No logra una frontera útil de calidad/cobertura aun preservando seguridad.

### D - RISKY

Aplica si existe cualquiera de:

- falsa promoción a `concrete`;
- falsa conclusión adversa `none`;
- salida inválida del contrato.

## No tuning

Después de comenzar run 1 quedan congelados:

- prompt;
- modelo;
- reasoning effort;
- taxonomía;
- corpus;
- mapeo determinista;
- criterio A/B/C/D.

Si el resultado no alcanza A/B, el siguiente experimento debe hacerse por separado. Si alcanza A/B, cualquier validación independiente posterior debe usar un holdout nuevo.