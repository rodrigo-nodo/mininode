# Privacy Web - PRV-103 semantic routing v2

## Estado

Investigación de arquitectura **cerrada**. No cambia producción.

Punto de partida y estado productivo preservado:

- `main` de referencia: `36039985817eb996a41a33e3254c610a635c9143`;
- framework productivo: `0.7`;
- scoring: `0.1`;
- PRV-103 productivo permanece determinístico;
- shadow permanece fuera de esta decisión.

QA8 cerró como `NEEDS FIX` porque `baseline=unknown -> LLM` no alcanzaba los falsos `generic`. Con QA6-QA8 ya consumidos se investigó una arquitectura residual antes de gastar un último holdout fresco.

Este trabajo es desarrollo/tuning, no QA independiente.

## Frontera semántica final v2.1

Solo se usan los cuatro textos del mismo formulario:

- `heading`;
- `legend`;
- `introductory_text`;
- `submit_text`.

Principios congelados:

1. El destinatario no es la finalidad: una empresa, equipo o ventas nombrados no convierten por sí solos el contacto en `concrete`.
2. `concrete` exige un resultado, contenido, beneficio, transacción o servicio específico observable en el mismo formulario.
3. Contacto, ayuda o pregunta general permanecen `generic` si no nombran un servicio o resultado específico.
4. Registro, suscripción o envío sin resultado adicional permanecen `generic`.
5. `Try for free` aislado, sin objeto o resultado visible, permanece `unknown`.
6. Descuento, cupón, beneficio u oferta explícita son un resultado `concrete`.
7. Ruido técnico/estructural puro puede ser `none`; texto semántico no resoluble permanece `unknown`.
8. El router determinístico nunca emite `concrete`.

Ejemplos de borde:

| Texto visible | Clase v2.1 |
|---|---|
| `Enviar` / `Submit` | `generic` |
| `Subscribe` | `generic` |
| `Get expert tips delivered to your inbox` | `concrete` |
| `Sub-processor updates` | `concrete` |
| `Escríbenos` | `generic` |
| `How can we help? / Post Question` | `generic` |
| `Talk to Vercel` | `generic` |
| `Contact sales / Send my question` | `generic` |
| `Request a demo` | `concrete` |
| `Book a demo` | `concrete` |
| `Garantir Desconto` | `concrete` |
| `Try for free` sin más contexto | `unknown` |
| sin texto | `unknown` |
| texto técnico/estructural puro | `none` |

Configuración final de desarrollo:

- taxonomía: `prv103-intents-v2.1`;
- contrato: `prv103-semantic-v2.1`;
- prompt: `prv103-intent-v2-03`;
- modelo: `gpt-5.6-sol`;
- reasoning: `medium`.

## Referencia de desarrollo

Se reutilizaron exclusivamente casos ya consumidos:

- QA6: 46;
- QA7: 30;
- QA8: 28;
- total: 104.

QA7 incorpora los textos exactos de su artifact ciego congelado.

El contrato v2.1 registra seis armonizaciones de desarrollo sin reescribir los QA históricos:

- `QA6_CHILE-009`: `concrete -> generic`;
- `QA6_INTL-014`: `concrete -> generic`;
- `QA7-007`: `concrete -> generic`;
- `QA8-007`: `concrete -> unknown`;
- `QA8-016`: `concrete -> generic`;
- `QA8-021`: `concrete -> generic`.

## Arquitectura investigada - Semantic Residual Router

El router no usa la clase del baseline como señal de confianza.

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
LLM de intención
        |
        v
mapping determinístico -> clase
```

Sobre los 104 casos consumidos, el router resolvió sin IA:

- 58 `trivial_generic`;
- 3 `technical_only`;
- 9 `empty_case`.

Solo 34 casos pasaron al LLM, una reducción de **67.31%** frente a LLM-all.

## Benchmark v2 inicial

La primera versión del contrato v2 obtuvo aproximadamente 95-96% de accuracy y confirmó que Residual igualaba a LLM-all usando 34 llamadas en vez de 104. Sin embargo produjo 2 falsas promociones a `concrete`, por lo que se marcó `not_ready_for_qa9` y no se consumió un holdout fresco.

Ese resultado llevó a congelar v2.1 como **último candidato de desarrollo**. No se autorizó una cadena abierta de nuevas versiones.

## Benchmark final v2.1

Run GitHub Actions: `34593077474`.

SHA ejecutado: `2f825314fbfd86e19e334d9dd168749606caf7eb`.

Tests focalizados: `7 passed`.

Resultado del workflow: `SUCCESS`.

| Métrica | Run 1 | Run 2 |
|---|---:|---:|
| Accuracy | 98.08% | 98.08% |
| Coverage | 87.50% | 89.42% |
| Emitted precision | 100.00% | 97.85% |
| Concrete precision | 100.00% | 100.00% |
| Concrete recall | 91.30% | 91.30% |
| False concrete promotions | 0 | 0 |
| False adverse `none` | 0 | 0 |
| Invalid outputs | **2** | 0 |
| LLM calls | 34 | 34 |

Estabilidad de clase: **98.08%**.

Reducción de llamadas LLM: **67.31%**.

Los dos errores de cada run corresponden al mismo formulario duplicado entre QA6 y QA7:

- `QA6_CHILE-012`;
- `QA7-020`.

Texto visible:

- `Contrata un plan`;
- `Ingresa tus datos y un ejecutivo se contactará contigo muy pronto.`

Referencia v2.1: `concrete`.

En run 1 ambos outputs fueron inválidos y fallaron de forma conservadora a `unknown`. El artifact no conserva detalle de error del proveedor, por lo que no se atribuye una causa más específica.

En run 2 ambos outputs fueron válidos pero clasificados como `subscription_generic`, por lo que quedaron `generic`.

El detalle reproducible está en `routing_v21_result.md`.

## Gates finales y decisión

Los gates v2.1 se congelaron antes de ejecutar:

- 0 false concrete promotions;
- 0 false adverse `none`;
- 0 outputs inválidos en ambos runs;
- accuracy >= 90%;
- emitted precision >= 90%;
- concrete recall >= 80%;
- class stability >= 95%;
- al menos 35% menos llamadas LLM.

Todos los gates de calidad, seguridad, estabilidad y ahorro se cumplieron salvo uno: **run 1 tuvo 2 outputs inválidos**.

Decisión formal: **`stop_semantic_line`**.

Se respeta la regla de salida congelada:

- no crear v2.2;
- no consumir QA9;
- no crear QA10;
- mantener PRV-103 productivo en framework `0.7`;
- conservar esta arquitectura como investigación documentada / posible trabajo futuro.

El resultado es técnicamente prometedor, pero no se activa ni se sigue afinando dentro de esta línea de QA.