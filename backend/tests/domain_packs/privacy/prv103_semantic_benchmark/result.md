# PRV-103 Semantic V1 - resultado

**Clasificación final: C - NO MATERIAL VALUE**

El experimento offline probó una taxonomía cerrada de intenciones con embeddings multilingües y abstención explícita. La representación semántica mejoró claramente la clasificación forzada frente a PRV-103 v0.7, pero el mecanismo de abstención necesario para preservar seguridad redujo la cobertura a un nivel no útil.

No se integra este enfoque en producción.

## Ejecución oficial

| Campo | Valor |
|---|---|
| Run oficial | `34285543773` |
| Estado | SUCCESS |
| Corpus | `prv103-semantic-v1-2026-09-08` |
| Taxonomía | `prv103-intents-v1` |
| Modelo | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |
| Model revision | `e8f8c211226b894fcb81acc59f3b34ba3efd5f42` |
| Desarrollo | QA4 - 37 HIGH deduplicados |
| Evaluación | QA5 - 32 HIGH deduplicados |
| Producción modificada | No |

Dos ejecuciones técnicas anteriores (`34284730291` y `34285356375`) fallaron antes de producir predicciones por un error de compatibilidad del runner con arrays NumPy. No generaron artifact de resultado y se excluyen completamente de la medición. El ajuste fue únicamente técnico (`if not vectors` -> `len(vectors) == 0`); corpus, taxonomía, modelo, grillas, criterios y etiquetas permanecieron congelados.

El run `34285543773` es la primera ejecución exitosa y constituye el resultado oficial. No se repite para buscar un resultado mejor.

## Umbrales elegidos solo con QA4

La búsqueda congelada seleccionó:

- `min_score = 0.20`;
- `min_margin = 0.225`;
- modo `safety_precision_then_coverage`.

Resultado en QA4 con abstención:

| Métrica | Resultado |
|---|---:|
| Exact accuracy | 29,7% |
| Coverage | 8,1% |
| Emitted precision | 100% |
| Concrete recall | 0% |
| False concrete promotions | 0 |
| False adverse `none` | 0 |
| Unknown rate | 91,9% |

La combinación que preserva seguridad y precisión en desarrollo ya exige una abstención muy alta.

## QA5 - comparación congelada

| Métrica | v0.7 reglas | Semántico forzado | Semántico + abstención |
|---|---:|---:|---:|
| Exact accuracy | 50,0% | **65,6%** | 15,6% |
| Coverage | 56,3% | 100% | **3,1%** |
| Emitted precision | 72,2% | 65,6% | **100%** |
| Concrete precision | 77,8% | 81,8% | 100%* |
| Concrete recall | 50,0% | **64,3%** | **0%** |
| Generic precision | 66,7% | 57,1% | 100% |
| False concrete promotions | 2 | 2 | **0** |
| False adverse `none` | 0 | 0 | 0 |
| Unknown rate | 43,8% | 0% | **96,9%** |

`*` La precisión concrete selectiva es formalmente 100% porque no emitió ningún `concrete`; por eso concrete recall = 0% y esa cifra no representa utilidad real.

## Qué sí aprendimos

La taxonomía de intenciones tiene señal semántica real. Sin abstención, el experimento corrigió 11 casos que v0.7 clasificaba mal, entre ellos:

- promociones/comunicaciones explícitas -> `specific_subscription_content`;
- stock/disponibilidad por zona -> `availability_delivery`;
- recuperación de contraseña -> `password_recovery`;
- `Registrarse` y `Escríbenos + Enviar Mensaje` dejaron de promocionarse a `concrete`;
- preguntas de feedback como `¿Encontraste lo que estabas buscando?` -> `feedback`;
- contacto y registro genéricos adicionales.

La exactitud forzada subió de 50,0% a 65,6% y concrete recall de 50,0% a 64,3%.

## Por qué no alcanza

El clasificador forzado todavía produjo dos falsas promociones a `concrete`: dos textos informativos sobre reducción de papel/residuos fueron asociados erróneamente a `quote_request`.

Además degradó seis casos que v0.7 resolvía correctamente, incluyendo login, contacto con resultado prometido, feedback explícito y acciones ambiguas.

Al aplicar el umbral necesario para eliminar las falsas promociones, el sistema se abstuvo en 31 de 32 casos de QA5. Solo emitió una clasificación `generic` y ninguna `concrete`.

Por tanto, el nearest-intent por embeddings **no ofrece una frontera riesgo/cobertura utilizable** en esta muestra. Mejorar score o recall relajando el margen reintroduciría precisamente el riesgo que el protocolo prohibió.

## Aplicación del criterio congelado

### A - PROMISING

Requería simultáneamente:

- 0 false concrete promotions;
- 0 false adverse `none`;
- emitted precision >= 90%;
- coverage >= 50%;
- accuracy >= 65%;
- concrete recall >= 50%.

La variante selectiva conserva seguridad, pero coverage = 3,1%, accuracy = 15,6% y concrete recall = 0%. No cumple.

### B - EXPLORATORY

Requería, entre otros, coverage >= 40%. No cumple.

### Resultado

**C - NO MATERIAL VALUE.**

El enfoque de embeddings por intención no se integra ni se calibra nuevamente sobre QA5. QA5 queda consumido para este experimento.

## Decisión técnica

Se mantienen como aprendizajes reutilizables:

1. separar comprensión de intención del mapeo determinista intención -> clase;
2. permitir abstención explícita;
3. medir riesgo y cobertura, no solo exact agreement;
4. tratar embeddings como representación/retrieval, no como autoridad final.

Si se continúa la investigación semántica de PRV-103, debe hacerse en otro experimento y con una arquitectura distinta; este resultado no justifica un PR productivo ni un QA6 sobre este clasificador.
