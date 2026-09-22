# Privacy Web - QA1 extractor declared_processing/v1

## Estado

**Cerrado — `NEEDS FIX`.**

El plan fue congelado antes de ejecutar inferencias. QA1 se ejecutó sobre los 10 documentos congelados, con dos ejecuciones por documento.

Este QA evalúa la calidad del extractor semántico común `declared_processing/v1`. No evalúa cumplimiento legal, PRV-202, scoring ni el diagnóstico público.

## SHA base

`49cd8fd6c8b63a921d9d9e85b3e0f392e1937011`

## Holdout

Los siguientes 10 documentos públicos se congelan para QA1. Ninguno pertenece al gate de representación de seis sitios usado para diseñar el contrato.

| Caso | Documento | URL | Tipo |
|---|---|---|---|
| Q01 | Fundación Superación de la Pobreza / Servicio País | https://superacionpobreza.cl/transparencia/politica-de-cookies-y-privacidad/ | privacy_policy |
| Q02 | Trip Global | https://tripglobal.cl/cookies | cookie_policy |
| Q03 | Policlínico Tabancura | https://policlinicotabancura.cl/politica-de-cookies | cookie_policy |
| Q04 | Zurich Chile | https://www.zurich.cl/conocenos/politicas-de-privacidad | privacy_policy |
| Q05 | Fundación Chile | https://fch.cl/politicas-de-privacidad/ | privacy_policy |
| Q06 | Justasa | https://www.justasa.cl/privacidad | privacy_policy |
| Q07 | Anelisa | https://www.anelisa.cl/politica-de-privacidad | privacy_policy |
| Q08 | Alex Brun | https://www.alexbrun.cl/politica-de-cookies | cookie_policy |
| Q09 | ELIZ Atelier | https://elizatelier.cl/cookies | cookie_policy |
| Q10 | IDA | https://www.ida.cl/politicas-de-privacidad | privacy_policy |

## Congelamiento de entrada

Antes de cualquier llamada al modelo, cada documento debe capturarse pasivamente mediante GET y guardarse como texto de QA con:

- case_id;
- URL final;
- fecha/hora UTC de captura;
- SHA-256 del texto enviado al extractor;
- tipo documental;
- título cuando esté disponible.

No se envían formularios, no se hace login, no se ejecutan acciones de consentimiento y no se intenta eludir protecciones.

Si un documento no puede recuperarse de forma pública y pasiva, el caso queda como `capture_failed`: no se reemplaza después de ver resultados del modelo.

## Referencia independiente

La referencia esperada se construye manualmente **antes** de ejecutar el extractor. Para cada caso se anotan únicamente hechos que puedan representarse con las ocho familias V1:

- technology;
- provider;
- data_categories;
- purposes;
- recipients;
- legal_basis;
- retention;
- international_transfers.

Cada hecho esperado debe incluir evidencia textual atribuible al documento. `ambiguous` y colecciones vacías son resultados válidos.

La referencia no debe usar la salida del modelo ni reglas PRV.

## Ejecución

Configuración congelada:

- schema: `declared_processing/v1`;
- implementación: SHA base indicado arriba;
- modelo: `gpt-5.6-sol`;
- prompt: `declared-processing-v1-01`;
- reasoning: `medium`;
- Structured Outputs: strict;
- `store=false`;
- 2 ejecuciones idénticas por documento.

No se modifica prompt, schema, normalización, código ni referencia entre ejecuciones.

## Métricas

Se registran por caso y globalmente:

1. **Unsupported facts**: hechos emitidos cuyo `value` no está respaldado por la evidencia citada o cuya relación semántica no está respaldada por el documento.
2. **Invalid evidence**: evidencia inexistente, alterada o atribuida a una fuente distinta.
3. **Relation errors**: asociaciones incorrectas entre tecnología, proveedor, propósito, retención u otros hechos.
4. **Expected fact recall**: hechos de la referencia recuperados correctamente.
5. **Fact precision**: hechos emitidos que corresponden a la referencia o son equivalentes respaldados.
6. **Class/status stability**: estabilidad de hechos y `supported/ambiguous` entre run 1 y run 2.
7. **Invalid outputs**: respuestas que no pasan `validate_output()`.

## Criterio de PASS congelado

QA1 es **PASS** solo si, en ambas ejecuciones:

- unsupported facts = **0**;
- invalid evidence = **0**;
- relation errors = **0**;
- invalid outputs = **0**;
- fact precision >= **95%**;
- expected fact recall >= **80%**;
- estabilidad de hechos >= **90%**.

Los cuatro primeros criterios son gates duros: cualquier valor mayor que cero produce `NEEDS FIX`, aunque las métricas agregadas superen los umbrales.

## Disciplina

- No ajustar durante QA.
- No sustituir casos después de observar resultados.
- No reutilizar como holdout los seis sitios del gate de representación.
- Si el resultado es `NEEDS FIX`, cualquier corrección ocurre después en un PR separado.
- Si se repite QA tras una corrección, se usa un holdout nuevo.
- PRV-202 permanece desconectado durante todo QA1.

## Resultado permitido

El informe final solo puede concluir:

- `PASS`;
- `NEEDS FIX`.

Las observaciones no cambian los gates congelados.


## Resultado final QA1

**NEEDS FIX**

Se completaron las 20 ejecuciones previstas. Solo **3/20** salidas pasaron la validación y **17/20** fueron inválidas:

- **12** `JSONDecodeError`: respuestas JSON truncadas durante la generación estructurada;
- **5** `ValueError`: evidencia rechazada por no coincidir literalmente con el texto de entrada bajo la normalización vigente;
- **3** salidas válidas: Q03 run 1 y Q09 runs 1 y 2.

El gate congelado exigía **0 invalid outputs** en ambas ejecuciones. Por lo tanto, QA1 falla ese gate duro y el resultado final es `NEEDS FIX`. No es necesario usar precision, recall o estabilidad para alterar esta conclusión.

Las fallas de infraestructura/timeout observadas en intentos previos no forman parte de este resultado final: la ejecución considerada completó las 20 llamadas sin timeout.

## Cierre y continuación

QA1 queda cerrado y sus diez documentos dejan de ser holdout independiente: pueden utilizarse únicamente como evidencia de desarrollo/diagnóstico de esta falla.

La corrección posterior se realizó fuera de QA1 y quedó integrada después del cierre del experimento: aumento del límite de salida estructurada y normalización de diferencias Unicode/presentación para validar evidencia, sin cambiar el contrato `declared_processing/v1`.

Cualquier validación independiente posterior será **QA2**, deberá congelarse antes de inferencia y utilizar un **holdout nuevo**. No se repetirá QA1 sobre estos diez documentos como evidencia independiente.
