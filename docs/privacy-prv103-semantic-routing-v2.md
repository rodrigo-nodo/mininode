# Privacy Web - PRV-103 semantic routing v2

## Estado

Investigación de arquitectura. **No cambia producción.**

Punto de partida: `main` SHA `36039985817eb996a41a33e3254c610a635c9143`, framework `0.7`, scoring `0.1`.

QA8 cerró como `NEEDS FIX` porque el fallback `baseline=unknown -> LLM` dejó fuera falsos `generic` relevantes. QA6 y QA7, en cambio, mostraron señal fuerte a favor del clasificador semántico. Antes de gastar un último holdout fresco se congela un contrato semántico más claro y se comparan arquitecturas solo sobre QA6-QA8 ya consumidos.

Este trabajo es **desarrollo/tuning**, no QA independiente.

## Frontera semántica v2

Solo se usan los cuatro textos del mismo formulario:

- `heading`;
- `legend`;
- `introductory_text`;
- `submit_text`.

Principios congelados:

1. El destinatario no es la finalidad: una empresa, equipo o departamento de ventas nombrado no convierte por sí solo el contacto en `concrete`.
2. `concrete` exige un resultado o servicio específico observable en el mismo formulario.
3. Contacto, registro, suscripción o envío sin resultado adicional permanecen `generic`.
4. `Try for free` aislado, sin objeto o resultado de creación visible, permanece `unknown`.
5. Ruido puramente técnico/estructural puede ser `none`; texto semántico no resoluble permanece `unknown`.
6. El router determinístico nunca promueve a `concrete`.

Ejemplos de borde:

| Texto visible | Clase v2 |
|---|---|
| `Enviar` / `Submit` | `generic` |
| `Subscribe` | `generic` |
| `Get expert tips delivered to your inbox` | `concrete` |
| `Sub-processor updates` | `concrete` |
| `Escríbenos` | `generic` |
| `Talk to Vercel` | `generic` |
| `Contact sales / Send my question` | `generic` |
| `Request a demo` | `concrete` |
| `Book a demo` | `concrete` |
| `Try for free` sin más contexto | `unknown` |
| sin texto | `unknown` |
| texto técnico/estructural puro | `none` |

La taxonomía experimental queda congelada como `prv103-intents-v2`; el prompt como `prv103-intent-v2-02`; modelo `gpt-5.6-sol`, reasoning `medium`.

## Referencia de desarrollo

Se reutilizan exclusivamente casos ya consumidos:

- QA6: 46;
- QA7: 30;
- QA8: 28;
- total: 104.

QA7 incorpora los textos exactos del artifact ciego del run `34542281119`.

Como el contrato v2 corrige fronteras que fueron adjudicadas de otra forma históricamente, se congelan cuatro overrides de **desarrollo** y se registran explícitamente en `semantic_contract_v2.json`:

- `QA6_CHILE-009`: `concrete -> generic`;
- `QA8-007`: `concrete -> unknown`;
- `QA8-016`: `concrete -> generic`;
- `QA8-021`: `concrete -> generic`.

Estos overrides no reescriben los QA históricos ni convierten esta comparación en una nueva validación independiente.

## Arquitecturas comparadas

### A - LLM-all

Todo formulario personal `HIGH` pasa por el clasificador semántico v2 y luego por el mapping determinístico intento -> clase.

### B - Semantic Residual Router

El router resuelve solo casos seguros y baratos:

```text
Formulario personal HIGH
        |
        v
¿vacío? --------------------------> unknown
        |
        no
        v
¿solo técnico/estructural? -------> none
        |
        no
        v
¿acción genérica trivial
 sin contexto semántico? ---------> generic
        |
        no
        v
LLM intención v2
        |
        v
mapping determinístico -> clase
```

No usa la clase del baseline como señal de confianza y nunca produce `concrete` por fast path.

## Gates de selección de desarrollo

Una candidata debe preservar en ambos runs:

- 0 false concrete promotions;
- 0 false adverse `none`;
- 0 outputs inválidos;
- accuracy >= 90%;
- emitted precision >= 90%;
- concrete recall >= 80%;
- class stability >= 95%.

Para preferir Residual sobre LLM-all además se exige:

- al menos 35% menos llamadas LLM;
- pérdida de accuracy no superior a 2 puntos porcentuales frente a LLM-all.

Si Residual no cumple pero LLM-all sí, la selección es LLM-all. Si ninguno cumple, **no se consume QA9**.

## Regla de salida

Solo si esta comparación de desarrollo selecciona una arquitectura se prepara **QA9**, con sitios completamente nuevos, referencia ciega independiente y rúbrica v2 congelada antes de ver resultados.

QA9 será el último holdout de esta línea. Si termina con un patrón estructural relevante `NEEDS FIX`, PRV-103 permanece en framework `0.7` y la capa semántica vuelve al roadmap. No se abre QA10.
