# PRV-104 - QA focalizado V2

## Producto congelado

- `main` SHA: `cb7c219f6b3e26bba4fd73a2905305a3a78003a1`
- `framework_version`: `0.9`
- `scoring_version`: `0.1`
- Control: `PRV-104 - Información de privacidad asociada al formulario`
- Sin cambios de producto ni reglas durante este QA.

## Objetivo

Corregir exclusivamente el diseño del QA anterior (#228), no PRV-104.

El QA se divide obligatoriamente en etapas separadas:

1. **Precheck de elegibilidad**: localizar formularios personales públicos observables usando únicamente PRV-101/evidencia estructural. En esta etapa no se consulta ni persiste PRV-104.
2. **Artifact A ciego**: una vez reunidos al menos 6 formularios elegibles, congelar evidencia observable por formulario sin sitio, URL ni predicción PRV-104. Debe incluir únicamente los elementos necesarios para adjudicar PRV-104: texto cercano, checkboxes y enlaces de privacidad asociados.
3. **Gold independiente**: adjudicar cada Artifact A como `detected`, `partial` o `not_detected` y persistir/congelar Gold antes de revelar predicciones.
4. **Artifact B / comparación**: recién entonces ejecutar/revelar PRV-104 del producto congelado y comparar contra Gold.

## Privacidad web

Solo GET y navegación pública. No enviar formularios, introducir datos, hacer login, POST ni ejecutar acciones de usuario.

## Holdout

El pool V2 debe ser nuevo respecto del QA #228 y de los holdouts usados para desarrollar/calibrar PRV-103 en la medida recuperable. La selección puede buscar deliberadamente páginas públicas de contacto/demo/newsletter para aumentar la probabilidad de formularios personales, pero la elegibilidad se decide sin mirar PRV-104.

El precheck puede recorrer un pool mayor hasta reunir **entre 6 y 12 formularios personales HIGH deduplicados**. Una vez congelado Artifact A no se reemplazan casos.

## Gates congelados

### PASS

- >= 6 casos adjudicables;
- exact accuracy PRV-104 >= 90%;
- 0 falsos `detected` adversos a Gold;
- 0 promociones de una aceptación genérica a información de privacidad;
- sin patrón sistemático de error.

### PASS WITH OBSERVATIONS

- >= 6 casos adjudicables;
- exact accuracy >= 80%;
- máximo 1 discrepancia no sistemática;
- 0 falsos `detected` materialmente engañosos.

### NEEDS FIX

Cualquier resultado inferior o patrón sistemático material.

## Stop rule

- `PASS` / `PASS WITH OBSERVATIONS`: PRV-104 queda validado para Formularios V1.
- `NEEDS FIX`: documentar y detener; no tuning automático.
- Si el precheck no logra >=6 formularios, el QA queda **INCONCLUSIVE** por cobertura, no como fallo de PRV-104.

Este PR es tooling/evidencia de QA y debe cerrarse sin merge.