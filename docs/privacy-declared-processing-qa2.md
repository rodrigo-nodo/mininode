# Privacy Web - QA2 extractor declared_processing/v1

## Estado

**Holdout y referencia congelados — inferencia no ejecutada.**

QA2 valida de forma independiente el extractor semántico común `declared_processing/v1` después de las correcciones derivadas de QA1. No evalúa cumplimiento legal, PRV-202, scoring ni el diagnóstico público.

## SHA base

`c13983df352772c38ceef18c93742f0b5c1407ef`

Incluye el cierre formal de QA1 y las correcciones #248/#249 ya integradas.

## Independencia

- Q01-Q10 de QA1 quedan excluidos.
- Los diez sitios QA2 no aparecen en el material de QA/desarrollo conocido del repositorio al congelar este plan.
- La selección se hizo antes de cualquier inferencia QA2.
- No se sustituirán casos después de observar resultados.
- Si una captura pública falla, el caso queda `capture_failed`; no se reemplaza.

## Holdout

| Caso | Documento | Tipo |
|---|---|---|
| Q2-01 | EmpresaChile | privacy_policy |
| Q2-02 | Banco de Chile | privacy_policy |
| Q2-03 | Gestdat | cookie_policy |
| Q2-04 | ACDATA | privacy_policy |
| Q2-05 | Grupo EC | privacy_policy |
| Q2-06 | MarTech | privacy_policy |
| Q2-07 | Inclu Work Consultores | privacy_policy |
| Q2-08 | NexoCap | privacy_policy |
| Q2-09 | Connectus | privacy_policy |
| Q2-10 | Urban Marketing | privacy_policy |

Las URLs exactas están congeladas en `declared_processing_qa2/cases.json`.

## Captura

Antes de llamar al modelo se capturará cada documento mediante GET público y pasivo. Se guardarán case_id, URL solicitada/final, fecha UTC, SHA-256, tipo, estado HTTP y tamaño del texto. La captura se ejecuta una sola vez tras integrar el workflow de captura y se conserva en la rama de evidencia `privacy/declared-processing-qa2-evidence` antes de construir la referencia independiente.

No se envían formularios, no hay login, no se aceptan consentimientos, no se crean cuentas y no se eluden protecciones.

## Referencia independiente

La referencia quedó construida y congelada **antes de habilitar cualquier inferencia** en `declared_processing_qa2/reference.json`, usando exclusivamente los seis textos capturados. Q2-04, Q2-05, Q2-06 y Q2-10 permanecen `capture_failed` y no tienen hechos esperados.

Se anotarán únicamente hechos representables por las ocho familias V1:
- technology;
- provider;
- data_categories;
- purposes;
- recipients;
- legal_basis;
- retention;
- international_transfers.

Cada hecho esperado tiene evidencia textual literal atribuible al documento. Un test verifica que las 51 evidencias anotadas estén presentes en sus capturas. La referencia no usa salidas del modelo ni reglas PRV.

## Configuración congelada

- schema: `declared_processing/v1`;
- modelo: `gpt-5.6-sol`;
- prompt: `declared-processing-v1-01`;
- reasoning: `medium`;
- Structured Outputs: strict;
- `store=false`;
- `MAX_OUTPUT_TOKENS=8192`;
- 2 ejecuciones idénticas por documento;
- sin retries ocultos.

No se cambia código, prompt, schema, normalización, referencia ni casos entre runs.

## Métricas

1. Unsupported facts.
2. Invalid evidence.
3. Relation errors.
4. Expected fact recall.
5. Fact precision.
6. Class/status stability.
7. Invalid outputs.
8. Tokens reales de entrada/salida y costo real por llamada/global.

## Criterio de PASS

QA2 es **PASS** solo si, en ambas ejecuciones:

- unsupported facts = **0**;
- invalid evidence = **0**;
- relation errors = **0**;
- invalid outputs = **0**;
- fact precision >= **95%**;
- expected fact recall >= **80%**;
- estabilidad de hechos >= **90%**.

Los cuatro primeros son gates duros. Cualquier valor mayor que cero produce `NEEDS FIX`.

## Protección de costo

El runner usa las tarifas vigentes congeladas para QA2 de **USD 4/M tokens de entrada** y **USD 20/M tokens de salida**, junto con un techo conservador de **8192 output tokens**. Para la entrada, el techo considera el request serializado completo (documento + instrucciones + schema), no una estimación basada solo en el texto.

Presupuesto máximo QA2: **USD 2**. Antes de cada llamada se exige que **costo contabilizado acumulado + techo conservador de la siguiente llamada <= USD 2**. Si no se cumple, la llamada no comienza. Si la API devuelve uso pero el resultado falla después en JSON o validación, ese uso igualmente se carga al acumulado. Si una llamada fue intentada y no existe usage confiable, se contabiliza conservadoramente su techo completo. El intento queda marcado antes de la primera llamada para impedir reejecuciones silenciosas después de gasto parcial. Errores de infraestructura producen fail-fast.

## Disciplina

- Este PR congela el plan; **no ejecuta inferencia**.
- La captura y referencia deben quedar committeadas antes de habilitar el workflow de inferencia.
- PRV-202 permanece desconectado.
- No ajustar durante QA.
- QA1 no se reejecuta.
- Si QA2 resulta `NEEDS FIX`, la corrección ocurre después y una futura validación usa otro holdout.

## Resultado permitido

- `PASS`;
- `NEEDS FIX`.
