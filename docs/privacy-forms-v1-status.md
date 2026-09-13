# Privacy Web - Formularios V1

## Estado

Decisión de producto posterior al QA09 independiente de PRV-103 sobre `framework_version = 0.9` y `scoring_version = 0.1`.

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

**Estado V1: experimental / no estable.**

- Se mantiene únicamente como contexto (`type = context`, `score_weight = 0`).
- No participa en Privacy Score, prioridades ni Plan de corrección.
- La UI lo mantiene como control informativo y neutral; por tanto, su resultado no determina el estado del área Formularios.
- El QA09 independiente de framework 0.9 terminó `NEEDS FIX`: 56 casos, 52 adjudicables, exact accuracy 42,31 %, coverage 65,38 %, emitted precision 64,71 %, concrete precision 100 %, concrete recall 44,44 %, 0 false concrete y 0 false adverse `none`.
- El patrón principal fue subdetección sistemática de finalidades concretas, principalmente degradadas a `generic` o `unknown`.
- Por la regla de cierre congelada antes del QA, no se crea framework 0.10 ni se continúa tuning en esta línea para V1.

PRV-103 no bloquea el cierre funcional de Formularios V1, pero tampoco debe presentarse como una capacidad estable o validada.

### PRV-104 - Información de privacidad asociada al formulario

**Estado V1: implementado; validación independiente pendiente.**

- Es un control condicional dependiente de PRV-101.
- Sí puede determinar el estado del área Formularios.
- La revisión de `main` confirma implementación, contrato y tests existentes, pero no se encontró una calibración independiente equivalente a la realizada para PRV-102 que permita declararlo validado para cierre V1.

## Decisión de cierre del área

PRV-103 deja de bloquear Formularios porque es informativo, de peso cero y experimental para V1.

Sin embargo, **Formularios todavía no se declara cerrado para V1**: falta una validación focalizada de PRV-104. No se reabre PRV-103 para completar esa validación.

El siguiente gate del área es exclusivamente PRV-104. Si su validación resulta aceptable, Formularios puede cerrarse para V1 manteniendo PRV-103 como limitación documentada.
