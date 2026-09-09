# PRV-103 Intent QA6 - holdout nuevo

**Estado inicial:** protocolo congelado antes de observar resultados del holdout.

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

Los candidatos de QA6 se fijan antes de inspeccionar sus formularios y se filtran contra evidencia histórica disponible de QA1-QA5, W2.2b.2, QA4/extension y tuning documentado. Además se excluyen explícitamente los 100 candidatos preseleccionados de QA5.

No se sustituirán sitios en función de la clase obtenida. Si la cobertura es insuficiente, cualquier extensión deberá congelarse antes de inspeccionar sus resultados.

Solo se permiten inspecciones públicas y pasivas mediante GET. No formularios enviados, POST, login, creación de cuentas ni bypass.

## Muestra

Objetivo mínimo para cerrar QA6: **30 formularios personales HIGH deduplicados**.

Se adjudican todos los HIGH deduplicados recuperados hasta cerrar la muestra; no hay subsampling por resultado.

## Referencia ciega

Primero se genera un paquete ciego que contiene exclusivamente:

- `blind_id`;
- `heading`;
- `legend`;
- `introductory_text`;
- `submit_text`.

La etiqueta de referencia se congela **antes de abrir cualquier salida del LLM evaluado**. Clases permitidas: `concrete`, `generic`, `none`, `unknown`.

Regla de adjudicación:

- `concrete`: existe una finalidad/resultado específico y reconocible más allá de solo contactar, enviar o registrarse;
- `generic`: existe intención general de contacto, envío, registro, suscripción o progresión sin resultado suficientemente específico;
- `none`: existe texto estructurado pero es técnico/no humano y no expresa finalidad;
- `unknown`: evidencia vacía, ambigua o insuficiente para determinar finalidad.

No se usan fields, action URL, page title, nearby_text ni conocimiento externo del sitio.

## Ejecución del modelo

Una vez congeladas las etiquetas de referencia se ejecutan dos pasadas idénticas:

- run 1: calidad oficial;
- run 2: estabilidad.

No existe tuning entre runs ni después de observar run 1.

## Métricas

Por cada run:

- exact accuracy;
- coverage (`prediction != unknown`);
- emitted precision;
- concrete precision;
- concrete recall;
- generic precision;
- false concrete promotions;
- false adverse `none`;
- invalid outputs;
- unknown rate.

Entre runs:

- class stability;
- intent stability;
- uncertain stability;
- evidence stability.

## Criterio congelado

### PASS

Debe cumplir **en ambos runs**:

- `false_concrete_promotions = 0`;
- `false_adverse_none = 0`;
- `invalid_outputs = 0`;
- `emitted_precision >= 90%`;
- `coverage >= 70%`;
- `accuracy >= 80%`;
- `concrete_recall >= 75%`;

y además:

- `class_stability >= 95%`.

### PASS WITH OBSERVATIONS

Debe preservar en ambos runs:

- 0 false concrete promotions;
- 0 false adverse none;
- 0 invalid outputs;

Y alcanzar en ambos runs al menos:

- emitted precision >= 90%;
- coverage >= 60%;
- accuracy >= 70%;
- concrete recall >= 65%;

con class stability >= 90%.

### NEEDS FIX

Cualquiera de estas condiciones basta:

- alguna falsa promoción a `concrete` en cualquiera de los dos runs;
- algún falso `none` adverso;
- salida inválida;
- métricas por debajo de PASS WITH OBSERVATIONS;
- patrón sistemático generalizable de error aunque un promedio quede sobre umbral.

## Regla posterior

QA6 no autoriza por sí solo integrar el LLM en producción.

- Si termina PASS/PASS WITH OBSERVATIONS, el siguiente paso es diseñar integración/shadow mode en un PR productivo separado.
- Si termina NEEDS FIX, no se ajusta el modelo sobre este holdout dentro del PR de QA; cualquier corrección es posterior y un nuevo QA requiere otro holdout.
