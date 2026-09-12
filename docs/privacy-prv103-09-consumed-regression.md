# PRV-103 — regresión diagnóstica 0.8 → 0.9

## Estado

La medición está **bloqueada por ausencia del artefacto consumido de la Issue
#223 en el checkout entregado**. No se sustituyeron casos, no se recapturaron
sitios y no se fabricaron resultados para completar la comparación.

## Configuración comprobada

- `main`: `6fbe6f94887114f4a5459af861f1fcaa0c4b7bd7`;
- `framework_version`: `0.9`;
- `scoring_version`: `0.1`;
- referencia 0.8 informada en #223: 63 elegibles, 58 adjudicables y 5 con
  gold `unknown` excluidos de las métricas adjudicables.

## Comparación

| Métrica | Framework 0.8 | Framework 0.9 | Diferencia |
| --- | ---: | ---: | ---: |
| eligible forms | 63 | pendiente | pendiente |
| adjudicable forms | 58 | pendiente | pendiente |
| exact accuracy | 53,45% | pendiente | pendiente |
| coverage | 74,14% | pendiente | pendiente |
| emitted precision | 72,09% | pendiente | pendiente |
| concrete precision | 86,36% | pendiente | pendiente |
| concrete recall | 52,78% | pendiente | pendiente |
| false concrete | 3 | pendiente | pendiente |
| false adverse `none` | 0 | pendiente | pendiente |

No corresponde asignar un veredicto hipotético a 0.9 ni concluir que existe
una mejora material sin ejecutar los 63 casos y el gold congelado. El holdout
sigue consumido: incluso una ejecución completa sería regresión diagnóstica y
no podría otorgar PASS final.

## Tooling preparado

`automation/privacy/run_prv103_09_consumed_regression.py` acepta el bundle JSON
congelado, exige exactamente 63 IDs únicos, 58 casos adjudicables y 5 gold
`unknown`, y aplica a estos últimos el tratamiento original. También fija el
SHA y las versiones, clasifica solamente los cuatro campos estructurados y
calcula la tabla, diferencias y veredicto bajo los umbrales de #223.

No se modificó producto, extractor, adapter, reglas PRV-103, scoring, tests ni
workflows.
