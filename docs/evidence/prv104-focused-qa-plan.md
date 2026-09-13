# PRV-104 - QA focalizado V1

## Producto congelado

- `main` SHA: `cb7c219f6b3e26bba4fd73a2905305a3a78003a1`
- `framework_version`: `0.9`
- `scoring_version`: `0.1`
- Control: `PRV-104 - Información de privacidad asociada al formulario`
- Sin cambios de reglas durante este QA.

## Objetivo

Validar de forma focalizada si PRV-104 distingue correctamente, en formularios personales públicos observables:

- `detected`: información visible de privacidad asociada al formulario;
- `partial`: señal visible de consentimiento/aceptación, pero sin información de privacidad reconocida;
- `not_detected`: no hay información de privacidad ni señal de consentimiento/aceptación asociada;
- `not_applicable`: PRV-101 no detecta formulario personal;
- `not_evaluable`: evidencia insuficiente o limitación técnica.

No se evalúa suficiencia jurídica, licitud ni si un consentimiento es obligatorio.

## Protocolo

1. Inspección exclusivamente pública y pasiva: GET/navegación pública. No enviar formularios, no introducir datos, no login, no POST y no ejecutar acciones de usuario.
2. Usar sitios nuevos para este QA focalizado y no modificar PRV-104 después de observar resultados.
3. Ejecutar el pipeline productivo desde el SHA congelado.
4. Para cada caso diagnosticable conservar evidencia mínima sanitizada suficiente para revisión manual: formulario personal observado, texto/checkbox asociado y presencia de enlace o información de privacidad. No conservar valores de usuarios ni secretos.
5. La referencia manual se decide desde la evidencia observable del formulario y según la definición del catálogo, no desde el resultado PRV-104 producido.
6. Comparar referencia manual vs producto solo después de fijar la referencia.
7. Si aparece una limitación técnica del sitio, se registra; no se cambia de sitio solo para mejorar métricas. El QA puede ampliar el pool inicial únicamente antes de revisar resultados, para asegurar casos evaluables.

## Pool inicial congelado

Doce sitios públicos, elegidos antes de ejecutar PRV-104:

1. `hubspot.com`
2. `mailchimp.com`
3. `typeform.com`
4. `surveymonkey.com`
5. `zendesk.com`
6. `freshworks.com`
7. `intercom.com`
8. `pipedrive.com`
9. `clickup.com`
10. `monday.com`
11. `airtable.com`
12. `webflow.com`

## Gates congelados

El QA requiere al menos **6 casos adjudicables con PRV-101 = detected**. Los `not_applicable` sirven para comprobar dependencia, pero no cuentan para el mínimo principal.

### PASS

- >= 6 formularios/casos adjudicables con PRV-101 = detected;
- exact accuracy PRV-104 >= 90%;
- 0 falsos `detected` adversos a la referencia;
- 0 casos donde una señal genérica de aceptación se promocione incorrectamente a información de privacidad;
- sin patrón sistemático de error.

### PASS WITH OBSERVATIONS

- >= 6 adjudicables con PRV-101 = detected;
- exact accuracy >= 80%;
- como máximo 1 discrepancia no sistemática;
- 0 falsos `detected` materialmente engañosos.

### NEEDS FIX

Cualquier resultado inferior a lo anterior o un patrón sistemático material.

## Regla de cierre

- `PASS` o `PASS WITH OBSERVATIONS` sin patrón material: PRV-104 puede cerrar Formularios V1 junto con el estado ya acordado de PRV-101/102/103.
- `NEEDS FIX`: no ajustar automáticamente. Se documenta la causa y se decide por separado si corregir PRV-104 o limitarlo para V1.

Este PR es tooling/evidencia de QA y no debe modificar código de producto.