# Privacy Web - PRV-103 QA8

## Objetivo

Validar en un holdout fresco e independiente la arquitectura candidata de PRV-103 después de corregir QA7-019 en framework `0.7`.

La arquitectura que se evaluará después de la adjudicación ciega es:

1. baseline determinístico de framework `0.7`;
2. solo cuando baseline entregue `unknown`, consultar el clasificador semántico LLM de intentos ya congelado;
3. mapear el intento a `concrete`, `generic`, `none` o `unknown` de forma determinística;
4. cualquier salida incierta o inválida permanece `unknown`.

QA8 no activa esta arquitectura en producción.

## Versión congelada

- `main`: `2fcf1c093023d6761cce5460a0a85779f5b0d180`;
- framework: `0.7`;
- scoring: `0.1`;
- modelo/prompt/taxonomía LLM: los ya congelados para PRV-103 (`gpt-5.6-sol`, `prv103-intent-v2-01`, `prv103-intents-v1`, reasoning `medium`).

No se ajustarán reglas, prompt, taxonomía, modelo ni criterios durante QA8.

## Holdout fresco

Se congelan 100 sitios candidatos antes de inspeccionar sus resultados.

Reglas:

- los hostnames deben estar ausentes del corpus histórico registrado de QA1-QA7 y del desarrollo semántico;
- inspección pública y pasiva solamente;
- máximo 100 sitios intentados;
- objetivo de 30 sitios distintos con al menos un formulario personal `HIGH` deduplicado;
- se detiene al alcanzar 30 sitios o al agotar los 100 candidatos;
- para cada sitio elegible se selecciona determinísticamente el primer formulario `HIGH` deduplicado en el orden del inspector;
- la deduplicación usa exclusivamente `heading`, `legend`, `introductory_text` y `submit_text`.

La lista y orden de candidatos no se reemplazan si algún sitio falla o no produce `HIGH`.

## Paquete ciego

Antes de ejecutar baseline o LLM contra la referencia, el Reviewer recibe solamente:

- `blind_id`;
- `heading`;
- `legend`;
- `introductory_text`;
- `submit_text`.

No recibe URL, hostname, sector, campos, action URL, resultado baseline ni resultado LLM.

Clases permitidas: `concrete`, `generic`, `none`, `unknown`.

El artifact interno con URLs y trazabilidad queda separado del artifact del Reviewer y no debe abrirse para adjudicar.

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

## Orden de ejecución

1. congelar candidatos, versión, arquitectura y gates;
2. capturar el holdout sin llamadas LLM;
3. adjudicación ciega independiente;
4. congelar la referencia;
5. ejecutar baseline `0.7` y fallback LLM solo sobre `unknown`;
6. comparar con la referencia y emitir PASS / PASS WITH OBSERVATIONS / NEEDS FIX.

Si QA8 termina NEEDS FIX, cualquier corrección ocurre después y una nueva validación deberá usar otro holdout fresco.
