# Privacy Web - Formularios V1

## Estado

Decisión de producto posterior a los QA independientes de PRV-103 y PRV-104 sobre `framework_version = 0.9` y `scoring_version = 0.1`.

### PRV-101 - Formularios que recopilan datos personales

**Estado V1: implementado como contexto.**

- Detecta puntos públicos de recopilación de datos potencialmente personales.
- `type = context` y `score_weight = 0`.
- Activa los controles posteriores de Formularios.
- No constituye por sí mismo una brecha y no determina adversamente el estado del área.

### PRV-102 - Envío seguro del formulario

**Estado V1: implementado y validado con observaciones.**

- Control determinístico y puntuable (`score_weight = 1`).
- La calibración pública real documentada cerró `PASS WITH OBSERVATIONS`, con acuerdo producto/manual 6/6 y sin false adverse observados.
- Las observaciones pendientes corresponden a cobertura del benchmark, no a un fallo observado que justifique cambiar la regla.

Referencia: `docs/privacy-prv102-real-calibration.md`.

### PRV-103 - Finalidad visible del formulario

**Estado V1: experimental / informativo.**

- Se mantiene únicamente como contexto (`type = context`, `score_weight = 0`).
- No participa en Privacy Score, prioridades ni Plan de corrección.
- La UI lo mantiene como control informativo y neutral; por tanto, su resultado no determina el estado del área Formularios.
- El QA09 independiente de framework 0.9 terminó `NEEDS FIX`: 56 casos, 52 adjudicables, exact accuracy 42,31 %, coverage 65,38 %, emitted precision 64,71 %, concrete precision 100 %, concrete recall 44,44 %, 0 false concrete y 0 false adverse `none`.
- El patrón principal fue subdetección sistemática de finalidades concretas, principalmente degradadas a `generic` o `unknown`.
- No se continúa tuning en esta línea para V1.

PRV-103 no debe presentarse como una capacidad estable o validada.

### PRV-104 - Información de privacidad asociada al formulario

**Estado V1: limitado / informativo.**

- El QA focalizado V2 independiente terminó `NEEDS FIX`: 10 casos comparables, exact accuracy 80 %, 2 discrepancias y 0 falsos `detected`.
- Se detiene el tuning para V1.
- PRV-104 continúa mostrando evidencia observable, pero su resultado es neutral en V1: no participa en Privacy Score ni cobertura, no determina adversamente el estado de Formularios y no genera prioridades ni acciones del Plan de corrección.
- La UI lo presenta como informativo y neutral.
- Se conserva la interpretación determinística conservadora: `detected` requiere información de privacidad reconocida asociada al formulario; una señal de consentimiento o aceptación por sí sola permanece como `partial` y no se interpreta como cumplimiento.
- Ausencia o ambigüedad de la señal no se utiliza para penalizar al sitio en V1.

Esta limitación es deliberada: conserva una señal útil para el usuario sin presentar como estable una capacidad que el QA independiente no validó.

## Decisión de cierre del área

**Formularios queda cerrado funcionalmente para V1 con limitaciones documentadas.**

PRV-102 es el control decisorio estable del área. PRV-101 aporta contexto de aplicabilidad; PRV-103 y PRV-104 permanecen informativos y neutrales para V1.

No se abre otro ciclo de tuning o QA para PRV-103/PRV-104 dentro de V1. Una futura mejora de estas capacidades debe tratarse como trabajo posterior, con su propia decisión de versión y validación independiente.
