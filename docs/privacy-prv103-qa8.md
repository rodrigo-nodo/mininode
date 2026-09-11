# Privacy Web - PRV-103 QA8

## Objetivo

Validar en un holdout fresco e independiente la arquitectura candidata de PRV-103 después de corregir QA7-019 en framework `0.7`.

La arquitectura evaluada fue:

1. baseline determinístico de framework `0.7`;
2. solo cuando baseline entrega `unknown`, consultar el clasificador semántico LLM de intentos ya congelado;
3. mapear el intento a `concrete`, `generic`, `none` o `unknown` de forma determinística;
4. cualquier salida incierta o inválida permanece `unknown`.

QA8 no activa esta arquitectura en producción.

## Versión congelada

- `main`: `2fcf1c093023d6761cce5460a0a85779f5b0d180`;
- framework: `0.7`;
- scoring: `0.1`;
- modelo/prompt/taxonomía LLM: `gpt-5.6-sol`, `prv103-intent-v2-01`, `prv103-intents-v1`, reasoning `medium`.

No se ajustaron reglas, prompt, taxonomía, modelo ni criterios durante QA8.

## Holdout fresco

Se congelaron 100 sitios candidatos antes de inspeccionar sus resultados.

Reglas:

- los hostnames debían estar ausentes del corpus histórico registrado de QA1-QA7 y del desarrollo semántico;
- el chequeo de frescura ocurrió antes de la primera captura;
- inspección pública y pasiva solamente;
- máximo 100 sitios intentados;
- objetivo de hasta 30 sitios distintos con al menos un formulario personal `HIGH` deduplicado;
- para cada sitio elegible se seleccionó determinísticamente el primer formulario `HIGH` deduplicado en el orden del inspector;
- la deduplicación usó exclusivamente `heading`, `legend`, `introductory_text` y `submit_text`.

La captura final obtuvo 28 sitios elegibles al agotar los 100 candidatos. No se agregaron ni reemplazaron sitios después de iniciada la captura.

## Referencia independiente

El Reviewer recibió únicamente:

- `blind_id`;
- `heading`;
- `legend`;
- `introductory_text`;
- `submit_text`.

No recibió URL, hostname, sector, campos, action URL, resultado baseline ni resultado LLM.

La adjudicación independiente de los 28 casos se congeló en `qa8_reference.json` antes de ejecutar el baseline o el LLM.

## Gates congelados

### PASS

- false concrete promotions = 0;
- false adverse `none` = 0;
- invalid LLM outputs = 0;
- emitted precision >= 90%;
- coverage >= 70%;
- accuracy >= 80%;
- concrete recall >= 75%.

### PASS WITH OBSERVATIONS

- false concrete promotions = 0;
- false adverse `none` = 0;
- invalid LLM outputs = 0;
- emitted precision >= 90%;
- coverage >= 60%;
- accuracy >= 70%;
- concrete recall >= 65%.

### NEEDS FIX

Cualquiera de estos casos:

- alguna falsa promoción a `concrete`;
- algún falso `none` adverso;
- salida LLM inválida;
- métricas inferiores a PASS WITH OBSERVATIONS;
- patrón sistemático generalizable de error.

## Resultado

Run de evaluación: `34551227384`.

Resultado formal: **NEEDS FIX**.

Métricas:

- exactitud: 22/28 = 78.57%;
- cobertura: 85.71%;
- precisión sobre emitidos: 83.33%;
- concrete precision: 100%;
- concrete recall: 44.44%;
- false concrete promotions: 0;
- false adverse `none`: 0;
- invalid outputs: 0;
- llamadas LLM: 8.

La arquitectura no supera los gates de QA8 por precisión emitida y, principalmente, por `concrete recall`.

Hallazgo estructural principal: tres casos de referencia `concrete` (`QA8-005`, `QA8-006`, `QA8-016`) fueron clasificados `generic` por el baseline `0.7`. Como el fallback LLM solo se ejecuta cuando el baseline devuelve `unknown`, esos casos nunca llegaron al clasificador semántico. Esto muestra que `unknown-only fallback` deja fuera falsos `generic` relevantes.

Además, entre los casos que sí llegaron al LLM, `QA8-007` quedó `unknown` y `QA8-021` quedó `generic` pese a referencia `concrete`. `QA8-015` quedó `unknown` frente a referencia `none`, de forma conservadora.

No hubo errores de seguridad en el sentido opuesto: no se observó ninguna falsa promoción a `concrete`, ningún `none` adverso ni salida inválida.

## Conclusión

QA8 se cierra como **NEEDS FIX**. No se ajusta esta arquitectura dentro del mismo QA.

Cualquier corrección debe definirse después y validarse en un nuevo holdout fresco. QA8 no cambia producción, scoring, Evidence Contract, extractor, API, DB, Render ni shadow.
