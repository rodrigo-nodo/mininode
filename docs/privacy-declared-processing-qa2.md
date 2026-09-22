# Privacy Web - QA2 extractor declared_processing/v1

## Estado

**Plan congelado — no ejecutado.**

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

Antes de llamar al modelo se capturará cada documento mediante GET público y pasivo. Se guardarán case_id, URL solicitada/final, fecha UTC, SHA-256, tipo, título y tamaño del texto.

No se envían formularios, no hay login, no se aceptan consentimientos, no se crean cuentas y no se eluden protecciones.

## Referencia independiente

La referencia se construirá y congelará **antes de habilitar cualquier inferencia** usando exclusivamente el texto capturado.

Se anotarán únicamente hechos representables por las ocho familias V1:
- technology;
- provider;
- data_categories;
- purposes;
- recipients;
- legal_basis;
- retention;
- international_transfers.

Cada hecho esperado tendrá evidencia textual atribuible al documento. La referencia no usará salidas del modelo ni reglas PRV.

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

El runner reservará un techo conservador usando **8192 output tokens**, consistente con la implementación vigente, y además registrará tokens/costo reales mediante `usage`.

Presupuesto máximo QA2: **USD 10**. Si el techo previo a una llamada supera el saldo, se detiene antes de gastar. Errores de infraestructura producen fail-fast.

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
