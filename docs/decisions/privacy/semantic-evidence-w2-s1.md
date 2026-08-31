# W2.S.1 — Semantic Evidence

**Estado:** propuesta de investigación; no es una decisión de producción
**Alcance:** PRV-008, PRV-010 y PRV-012
**Fuera de alcance:** cambios de controles, adapter, evaluator, score, API, frontend,
persistencia, dependencias o uso de servicios/modelos en producción.

## Resumen ejecutivo y decisión provisional

El problema no es encontrar más palabras, sino decidir si un fragmento afirma una
relación concreta y con el alcance correcto. «Enlaces a terceros» y «comunicamos
datos a proveedores» comparten vocabulario, pero sólo la segunda frase evidencia
destinatarios. Del mismo modo, eliminar estadísticas de cookies no establece una
regla general de conservación.

La recomendación para **Mininode Privacy hoy es la opción 5: arquitectura híbrida**,
entendida de forma deliberadamente limitada: conservar las reglas como línea base y
evaluador autoritativo, construir primero el golden set y experimentar fuera de
producción con **retrieval por embeddings seguido de NLI o un cross-encoder**. No se
recomienda poner ahora un LLM en el camino crítico ni usar embeddings como
clasificador. «Híbrida» no significa desplegar toda la cascada: en W2.S.1 sólo se
comparan sus piezas.

La hipótesis a validar es:

1. embeddings recuperan con buen recall pocos fragmentos candidatos;
2. NLI/cross-encoder distingue mejor relación, negación y alcance;
3. código determinista valida el esquema, aplica umbrales conservadores y produce el
   estado final;
4. ante duda o desacuerdo, se conserva el resultado determinista conservador.

Ninguna capa semántica debe entrar a producción antes de superar el benchmark,
revisión humana de errores y una fase shadow sin alterar diagnósticos. Con sólo
30–45 casos, el benchmark permite comparar prototipos, **no** demostrar precisión
general ni entrenar un modelo propio.

## A. Problema que resolvemos

W2.E mejoró la fuente documental: los controles documentales usan una muestra
`content_text` limpia, efímera y limitada. El límite restante está en la
interpretación:

- **paráfrasis:** finalidades concretas que no coinciden con el léxico existente;
- **relación:** no toda aparición de «tercero» implica comunicación de datos;
- **alcance:** una eliminación específica de cookies no implica conservación general;
- **negación y modalidad:** «no compartimos», «podemos compartir» y «enlaces de
  terceros» requieren tratamientos diferentes;
- **atribución:** la afirmación debe pertenecer a la política y al objeto evaluado.

El objetivo no es resolver cumplimiento legal. Es producir evidencia documental
estructurada, citable y prudente que el evaluator actual pueda consumir. La capa
semántica no debe responder «Bien», «Puede mejorar» o «Necesita atención».

## B–D. Alternativas: capacidades, límites y adecuación

| Alternativa | Qué puede resolver | Qué no resuelve por sí sola | Papel razonable |
|---|---|---|---|
| Reglas/regex | Frases conocidas, negaciones explícitas, trazabilidad exacta, coste y latencia mínimos | Paráfrasis no previstas, relaciones y alcance distantes; crece el mantenimiento combinatorio | Baseline, fast path y guardrails |
| Ontología/diccionario | Normaliza conceptos y sinónimos; ofrece etiquetas explicables y compartibles | Una lista no entiende quién comunica qué a quién ni el alcance de la frase | Esquema conceptual y expansión controlada de reglas |
| Embeddings | Recuperación semántica de paráfrasis y reducción de texto candidato | Similitud no equivale a entailment; puede confundir enlaces y transferencias | Retrieval, no decisión final |
| Embeddings + similitud | Ranking barato y reutilizable de fragmentos frente a descripciones/prototipos | El umbral no corrige negación, sujeto, objeto o alcance; un vecino cercano puede ser falso positivo | Top-k con umbral de recall y opción «sin candidato» |
| Cross-encoder/reranker | Compara conjuntamente control y fragmento; suele ordenar mejor que vectores independientes | Un relevance score no necesariamente representa una clase ni prueba entailment; explicabilidad limitada | Reranking o clasificador por pares |
| NLI/textual entailment | Pregunta explícitamente si el texto implica una hipótesis; representa entailment/neutral/contradiction | Modelos genéricos pueden fallar en español, dominio legal, textos largos o hipótesis mal redactadas | Clasificación conservadora de fragmentos recuperados |
| Embeddings + NLI | Separa recall (retrieval) de precisión (entailment) y limita cómputo | Acumula errores de segmentación, retrieval y NLI; exige calibración por control | Mejor candidato experimental |
| Small language model local | Clasificación/extracción privada, sin proveedor por request; eventualmente ajustable | Operación de pesos, memoria, cuantización, serving y calidad variable; generación no garantiza evidencia fiel | Experimento posterior si un modelo NLI no alcanza |
| LLM general + salida estructurada | Maneja paráfrasis y extracción relacional flexible; útil para analizar errores ambiguos | JSON válido no implica verdad; coste, latencia, drift, privacidad y reproducibilidad; puede inventar citas | Árbitro experimental o fallback tardío, nunca juez legal |
| Clasificador propio | Optimiza clases y idioma del producto; despliegue local y estable | Requiere mucho más dato diverso y etiquetado que 30–45 casos; riesgo de sobreajuste | Ruta de 12+ meses si crece el corpus |

La ontología y los modelos no son opciones mutuamente excluyentes: la primera define
qué significa la salida y los segundos pueden ayudar a detectarla. Tampoco «NLI» y
«cross-encoder» son categorías técnicas totalmente separadas: NLI suele implementarse
con un encoder que procesa el par premisa–hipótesis; un reranker también procesa el
par, pero optimiza relevancia en vez de entailment.

### Ontología mínima propuesta

No crear aún un motor ontológico. Usar un vocabulario versionado como taxonomía de
anotación:

- `purpose`: `service_provision`, `order_management`, `account_management`,
  `marketing`, `security`, `personalization`, `analytics`, `product_improvement`;
- `recipient`: `service_provider`, `processor`, `payment_provider`, `hosting`,
  `marketing_provider`, `authority`, `related_company`;
- `retention`: `fixed_period`, `relationship_duration`, `legal_requirement`,
  `necessity_based`, `deletion_after_event`.

Cada etiqueta requiere además relación y alcance, por ejemplo
`data -> disclosed_to -> service_provider` y no sólo `service_provider`. Para
conservación debe anotarse el objeto (`personal_data`, `cookies`, `analytics_record`)
y si el criterio es general o específico. Esta representación puede reutilizarse en
Privacy Data porque el núcleo `datos → finalidad → responsable → tercero →
conservación → derechos` no depende de HTML. Debe separarse `source_type`
(`public_policy` o, a futuro, `internal_statement`) del concepto semántico.

## E. Arquitectura recomendada hoy

### Arquitectura 1 — reglas solamente

`content_text → regex → adapter`

Es la línea base de producción. Es simple, rápida y auditable, pero ya muestra los
límites que motiva W2.S.1. Debe permanecer intacta durante el experimento.

### Arquitectura 2 — reglas + embeddings

`content_text → segmentación → embeddings → fragmentos relevantes → reglas`

Puede mejorar recall al llevar nuevas paráfrasis a reglas existentes, aunque esas
reglas aún pueden no comprender la frase. Es útil como ablación para medir cuánto
aporta sólo retrieval. No debe promover una clase basándose únicamente en similitud.

### Arquitectura 3 — reglas + embeddings + NLI/cross-encoder

`content_text → segmentación → retrieval top-k → entailment/clasificación → evidencia
estructurada → evaluator`

Es la candidata principal. Ejecutar reglas primero; reutilizar una única segmentación
y embeddings para los tres controles; aplicar NLI a pocos candidatos; aceptar sólo
clases y citas provenientes literalmente de los fragmentos de entrada. La ausencia de
entailment no prueba `none`: significa evidencia semántica insuficiente.

### Arquitectura 4 — reglas + LLM fallback

`reglas → incertidumbre explícita → LLM → evidencia estructurada → evaluator`

Es flexible, pero «incertidumbre» debe definirse por código (señales contradictorias,
scores en banda gris o candidatos sin decisión), no por intuición del modelo. Antes de
considerarla se requieren contrato estricto, lista cerrada de clases, citas por offsets,
validación de que cada cita existe, timeout, presupuesto, política de proveedor y
fallback conservador.

### Arquitectura 5 — embeddings → NLI → LLM residual

Es técnicamente coherente, pero hoy innecesariamente compleja. Añade tres umbrales,
dos familias de modelos, observabilidad, fallos y costes para sólo tres controles. Sólo
se justificaría si el benchmark ampliado muestra: retrieval con alto recall, NLI con
pocos falsos positivos pero una banda ambigua relevante, y mejora material del LLM en
esa banda sin romper estabilidad, privacidad ni latencia.

## F. Arquitectura posible a 12 meses

Si la evidencia experimental lo respalda:

1. extractor y segmentador agnósticos al producto;
2. catálogo versionado de conceptos, hipótesis y clases por control;
3. retrieval local o por servicio encapsulado;
4. clasificador por pares local, calibrado por control;
5. `SemanticEvidence` interno con fuente, offsets, clase, scores técnicos y versión;
6. policy gate determinista que puede abstenerse;
7. evaluator y score actuales como única autoridad de estados;
8. shadow evaluation, métricas de drift y suite de regresión sintética;
9. LLM opcional sólo para una banda residual, si aporta valor medido;
10. corpus más grande que eventualmente permita entrenar o ajustar un clasificador.

La interfaz del clasificador debería recibir texto y conceptos, no objetos del crawler,
para que Privacy Data pueda usar la misma semántica con otra procedencia y reglas de
acceso.

## G. Diseño del benchmark W2.S.1

### Corpus y muestreo

Construir 12 políticas (36 casos control–política): SIP, Emol y EduSmart, más nueve
candidatas: Mercado Libre Chile, BancoEstado, LATAM Chile, Falabella, Universidad de
Chile, Clínica Alemana, WOM Chile, GitHub y Mozilla. Son **candidatas de muestreo**, no
afirmaciones sobre su calidad. Antes de incorporarlas hay que confirmar acceso y
permiso de conservación del extracto necesario.

La selección debe buscar variedad, no conveniencia:

- educación, medios, comercio, banca, viajes, salud y telecomunicaciones;
- políticas chilenas y textos internacionales en español;
- políticas detalladas, genéricas y casos sin evidencia;
- positivos claros, negativos difíciles, negaciones y alcance específico;
- paráfrasis distintas y documentos de longitudes variadas.

Si una candidata no es accesible o su licencia/uso plantea dudas, reemplazarla por otra
del mismo estrato y documentar el cambio. El corpus congelado se identifica por
`corpus_version`; CI jamás descarga esas páginas.

### Unidad de evaluación

La unidad primaria es `(policy_id, control)`, pero se guardan segmentos para evaluar
por separado:

1. **retrieval:** ¿aparece al menos un fragmento gold en top-k?;
2. **clasificación:** dado el fragmento gold, ¿produce la clase correcta?;
3. **end-to-end:** desde los fragmentos congelados, ¿produce clase y cita correctas?;
4. **abstención:** ¿evita promover evidencia ante neutralidad o baja confianza?

Separar estas tareas evita culpar al NLI cuando retrieval omitió la evidencia. La
segmentación inicial debe preservar párrafos, títulos y listas; unir título + párrafo o
ítem y usar ventanas vecinas sólo cuando una referencia anafórica lo requiera. Guardar
offsets sobre el fixture normalizado.

### Etiquetado humano

- dos revisores etiquetan independientemente;
- las instrucciones definen clases, alcance y ejemplos límite antes de anotar;
- desacuerdos se resuelven por adjudicación y se conservan como metadata;
- medir acuerdo (porcentaje y Cohen's kappa; kappa se interpreta con cautela por el
  tamaño pequeño y desbalance);
- el revisor no ve la predicción del sistema durante la primera anotación;
- una política puede tener múltiples evidencias y contraejemplos.

No usar el conjunto completo para ajustar umbrales y después informar el mismo
resultado. Con 12 políticas, usar por ejemplo 4 de desarrollo y 8 de evaluación
congelada, separadas por política; reportar intervalos bootstrap y conteos crudos. Los
resultados son exploratorios por el tamaño reducido. Cuando el corpus crezca, añadir
un test oculto y cortes por dominio/idioma.

### Alternativas a ejecutar

1. adapter actual, sin cambios;
2. ontología/reglas expandidas como baseline opcional;
3. embeddings: retrieval top-k y, como ablación, clasificación por similitud;
4. embeddings + NLI y embeddings + cross-encoder de relevancia/clase;
5. LLM con structured output, sólo si hay acceso aprobado y con los mismos fragmentos;
6. humano gold.

Todos reciben el mismo texto congelado y presupuesto de candidatos. Registrar modelo,
revisión, prompt/hipótesis, parámetros, hardware, fecha, repeticiones y latencias. No
llamar APIs pagadas en W2.S.1 sin una decisión posterior explícita.

### Casos sintéticos de regresión

Los fixtures futuros deben ser paráfrasis creadas para el test, no copias extensas de
políticas. Como mínimo:

- propósito concreto: registros de usuarios/pedidos para prestar y mejorar servicios;
- propósito genérico: «tratamos sus datos para nuestras finalidades»;
- destinatario explícito: datos comunicados a proveedor de pagos;
- no comunicación explícita: «no compartimos datos con terceros»;
- negativo difícil: enlaces a sitios de terceros;
- conservación explícita: durante la relación y obligaciones legales;
- conservación genérica: se conserva «por un tiempo» sin criterio;
- negativo difícil: eliminación posterior de estadísticas de cookies;
- pares con negación, posibilidad, sujeto distinto y oraciones divididas.

## H. Formato del golden set

Se recomienda **YAML versionado en Git** para esta fase: admite comentarios, listas y
razones multilínea y ya existe PyYAML en el entorno. JSON es más rígido y carece de
comentarios; CSV se vuelve frágil para múltiples evidencias, offsets y adjudicación.
Un validador futuro puede cargar YAML y validarlo con modelos Pydantic ya disponibles,
sin base de datos. Si el corpus crece, JSONL sería mejor para tooling y streaming.

Ejemplo de diseño (no se añade aún un corpus real):

```yaml
schema_version: 1
corpus_version: w2s1-2026-01
policies:
  - policy_id: edusmart
    source:
      kind: public_policy
      captured_at: "YYYY-MM-DD"
      source_url_hash: "..."       # URL en manifest privado si fuera necesario
      language: es
    cases:
      - control: PRV-008
        expected: concrete
        concepts: [account_management, order_management, product_improvement]
        reason: Declara acciones y objetivos específicos.
        evidence:
          - fixture_id: edusmart-purpose-01
            start: 0
            end: 72
        hard_negatives: []
        annotation:
          reviewers: [r1, r2]
          agreement: true
          adjudicated_by: null
      - control: PRV-012
        expected: none
        concepts: []
        reason: La eliminación se limita a estadísticas de cookies.
        evidence: []
        hard_negatives:
          - fixture_id: edusmart-cookie-deletion-01
            reason: Objeto y alcance específicos, no conservación general.
        annotation:
          reviewers: [r1, r2]
          agreement: true
          adjudicated_by: null
```

Los fixtures de evaluación deben residir separados del manifest si su acceso requiere
controles. El repositorio público sólo debe contener fragmentos sintéticos autorizados.
No guardar HTML ni políticas completas.

## I. Métricas y prioridad de falsos positivos

Reportar por control, clase y total; nunca sólo accuracy agregada:

1. exactitud exacta multicategoría;
2. precision, recall y F1 macro por clase;
3. matriz de confusión y conteos de falsos positivos/negativos;
4. **false-positive rate de promoción:** casos donde el sistema afirma evidencia más
   fuerte que el gold;
5. coste ponderado conservador: por ejemplo, peso 3 para promoción falsa, 1 para
   omisión y 1 para confusión entre clases no promocionales. Los pesos deben aprobarse
   antes de ver resultados;
6. retrieval recall@1, @3 y @5, MRR opcional y tasa sin candidato;
7. evidencia: exact match de `fixture_id`, solapamiento de offsets y precision de citas;
8. groundedness: toda cita existe literalmente en el input;
9. cobertura y tasa de abstención; accuracy selectiva sobre casos respondidos;
10. estabilidad: coincidencia de clase/cita en 10 repeticiones y entre versiones;
11. latencia p50/p95 por control y diagnóstico, separando segmentación, retrieval y
    clasificación;
12. ejecución/costo estimado por diagnóstico;
13. rúbrica ordinal de explicabilidad, dependencia externa, complejidad operativa y
    ejecución local.

Accuracy puede ocultar el riesgo si domina `none`. La decisión debe priorizar cero o
casi cero promociones falsas en el test congelado y revisar cada error cualitativamente.
Con 30–45 casos, una sola equivocación cambia mucho el porcentaje: publicar numerador,
denominador e intervalos, no decimales de falsa precisión.

## J. Riesgos y mitigaciones

| Riesgo | Ejemplo | Mitigación |
|---|---|---|
| Similitud superficial | enlaces vs datos compartidos con terceros | hard negatives; embeddings sólo para retrieval |
| Error de alcance | borrar cookies implica retención general | objeto/alcance anotados; hipótesis específicas |
| Negación/modalidad | «no», «podría», «excepto» | NLI por hipótesis positiva y negativa; abstención |
| Segmentación | sujeto en párrafo anterior | títulos/listas/contexto vecino acotado |
| Sesgo del corpus | pocos sitios educacionales | muestreo por sector y estilo; ampliar antes de producción |
| Leakage | ajustar y evaluar sobre las mismas políticas | split por política y test congelado |
| Modelo multilingüe débil | español chileno/legal | benchmark en idioma real; no inferir calidad desde inglés |
| Drift | proveedor/modelo cambia | fijar versión cuando sea posible y suite de repetición |
| Alucinación/cita inventada | LLM devuelve texto ausente | offsets validados; rechazo total ante cita inválida |
| Automation bias | score semántico tratado como verdad | evaluator determinista; revisión de errores y shadow mode |
| Complejidad prematura | tres servicios para tres controles | introducir una capa por vez y exigir ganancia incremental |

## K. Privacidad y minimización

- partir exclusivamente de `content_text`, nunca enviar HTML completo;
- segmentar localmente y enviar, si se aprueba una API, sólo top-k fragmentos
  necesarios, su control e hipótesis; eliminar URL, dominio y metadatos no necesarios;
- limitar tamaño y número de fragmentos; no incluir otros formularios o páginas;
- no persistir políticas completas, embeddings de contenido ni prompts/respuestas por
  defecto; definir TTL si una caché futura resulta necesaria;
- no exponer `content_text`, fragmentos, vectores o scores técnicos en EvidenceContract,
  snapshots o respuestas públicas;
- logs con IDs, versión, timings y códigos de error, no texto ni vectores;
- validar citas mediante offsets y conservar en el contrato interno sólo el mínimo que
  el evaluator necesita;
- antes de usar un proveedor, revisar retención, entrenamiento, región, subprocessors,
  eliminación y términos vigentes; una clave y «no training» no sustituyen esa revisión;
- tratar cualquier fragmento web como input no confiable y como posible prompt
  injection. El contenido nunca puede modificar instrucciones, clases o esquema.

## L. Costos relativos

Escala cualitativa para el tamaño actual; no representa precios contractuales:

| Alternativa | Infraestructura | Ejecución | Desarrollo | Mantenimiento |
|---|---:|---:|---:|---:|
| Reglas | muy bajo | muy bajo | bajo | medio |
| Ontología + reglas | muy bajo | muy bajo | medio | medio |
| Embeddings API | muy bajo | bajo | bajo | bajo/medio |
| Embeddings locales | medio | muy bajo | medio | medio |
| Cross-encoder/NLI local | medio | bajo/medio | medio | medio/alto |
| Embeddings + NLI local | medio | bajo/medio | medio/alto | alto |
| Small LM local generativo | alto | medio/alto | alto | alto |
| LLM API | muy bajo | medio | medio | medio/alto |
| Clasificador propio | medio | bajo | alto | alto |

Una API desplaza infraestructura a ejecución y dependencia externa. Un modelo local
evita coste marginal por llamada, pero no es «gratis»: consume RAM/CPU, aumenta imagen,
arranque, parches y observabilidad. Los precios API cambian; sólo deben cotizarse al
momento de un experimento aprobado usando tokens reales p50/p95.

## M. Latencia y presupuesto UX

El objetivo «normalmente en menos de un minuto» es viable si la semántica opera sobre
pocos fragmentos, no sobre el documento completo:

- segmentar una vez y reutilizar embeddings para PRV-008/010/012;
- recuperar top-3 (comparar top-1/3/5) y no clasificar todas las combinaciones;
- agrupar inferencias locales o requests, con límites y timeout global;
- paralelizar controles sólo cuando no multiplique contención del mismo modelo;
- cargar un modelo local una vez por proceso; medir cold start por separado;
- cachear por hash de fragmento/modelo sólo en una fase posterior, con TTL y análisis
  de privacidad;
- reservar presupuesto global. Un timeout o fallo semántico vuelve a reglas y nunca
  impide completar el diagnóstico.

Objetivo experimental inicial, no SLO: overhead semántico p95 menor a 10 segundos por
diagnóstico caliente y nunca más de 20 segundos dentro del presupuesto total. Estos
límites se revisan con medición real en el entorno objetivo.

## N–O. Reutilización y dependencias futuras

### Ya existe y se puede reutilizar

- `content_text` limpio y acotado y su exclusión del payload serializado;
- adapter y evaluator deterministas, clases conceptuales y pruebas existentes;
- `re`, Pydantic y PyYAML para baseline, esquema y golden set;
- OpenAI SDK para otras áreas del repositorio, aunque su presencia **no** constituye
  una decisión de usarlo en Privacy;
- BeautifulSoup/lxml y trafilatura para extracción. Trafilatura no es infraestructura
  de embeddings ni clasificación semántica.

### No existe

No se observa infraestructura de vector store, sentence embeddings, tokenizer/model
runtime, PyTorch/ONNX, NLI, cross-encoder, serving o caché semántica. Tampoco existe un
contrato interno semántico, un corpus gold ni calibración por control.

### Dependencias que cada opción podría requerir

| Opción futura | Posibles dependencias (sujetas al benchmark) |
|---|---|
| Ontología/reglas | ninguna; YAML/Pydantic actuales bastan |
| Embeddings API | SDK HTTP/proveedor ya disponible o `httpx`; sin vector DB para 12 políticas |
| Embeddings local | runtime como ONNX Runtime o `sentence-transformers` + backend tensorial; tokenizer y pesos versionados |
| Cross-encoder/NLI local | tokenizer/runtime y pesos; típicamente Transformers + PyTorch u ONNX |
| Small LM local | runtime generativo/servidor, cuantización y pesos; posiblemente GPU |
| LLM API | SDK existente si se eligiera OpenAI, o SDK/HTTP del proveedor; schema validator existente |
| Clasificador propio | stack de entrenamiento separado; producción podría usar sólo artefacto ONNX/tokenizer |

W2.S.1 no debe añadir ninguna. Para ejecución local futura conviene comparar primero
ONNX CPU contra PyTorch en un prototipo aislado: imágenes y recursos del backend actual
pueden hacer inviable incorporar directamente un stack de entrenamiento.

### Tamaño/modelos a estudiar, no adoptar

Para embeddings, comenzar con un encoder multilingüe pequeño/base (aproximadamente
100–300 millones de parámetros) y comparar una opción mayor sólo si la mejora justifica
recursos. Para NLI, buscar un encoder multilingüe base entrenado/evaluado en XNLI y
validarlo obligatoriamente en el corpus español. Los nombres concretos deben fijarse en
el protocolo del experimento con licencia, tamaño, revisión inmutable y model card; no
elegir por leaderboard ni descargar pesos en esta tarea.

## P. Recomendación por control

### PRV-008 — finalidades

- Retrieval con una hipótesis por concepto de finalidad y ejemplos de paráfrasis.
- Clasificar `concrete` sólo si el fragmento vincula una acción/uso de datos con una
  finalidad específica; una lista de propósitos puede aportar varias evidencias.
- `generic` requiere referencia al tratamiento/uso sin finalidad concreta; ausencia de
  match es `none`, no `generic`.
- Es el caso donde ontología y embeddings probablemente aporten más recall.

### PRV-010 — destinatarios

- Prioridad máxima de precisión: exigir relación entre datos/comunicación y receptor.
- Hipótesis separadas para comunicación explícita, categoría genérica y no comunicación;
  `explicit_none` necesita negación inequívoca cuyo objeto sean datos.
- «Enlaces», contenido, cookies o servicios «de terceros» son hard negatives salvo que
  otra oración declare transferencia/comunicación.
- Embeddings solos son especialmente inadecuados; NLI o clasificador relacional y
  guardrails léxicos son necesarios.

### PRV-012 — conservación

- Exigir objeto, evento/plazo/criterio y alcance. Etiquetar `retention_scope` como
  general o específico.
- `explicit` requiere periodo o criterio observable; `generic` sólo una declaración
  general de conservación sin criterio; una eliminación específica no se generaliza.
- Incluir hard negatives de cookies, logs y estadísticas, además de referencias a
  almacenamiento técnico sin duración.
- NLI debe usar hipótesis distintas para criterio general y evento específico; no basta
  preguntar por la palabra conservación.

## Q. Conclusión por familia

- **Embeddings solos:** sí para retrieval; no para clasificación ni promoción de
  evidencia. La cercanía superficial produce exactamente los falsos positivos que más
  preocupan.
- **Embeddings + NLI/cross-encoder:** mejor candidato al benchmark porque separa recall
  y decisión. NLI encaja conceptualmente mejor; un cross-encoder de relevancia sirve
  para reranking y uno entrenado para clases podría competir. Hay que medir ambos.
- **LLM:** no es la primera opción. Evaluarlo después, con fragmentos mínimos y salida
  validada, para saber si resuelve casos residuales; no asumir que temperatura cero lo
  vuelve determinista.
- **Cascada híbrida:** arquitectura objetivo razonable, pero desplegar ahora retrieval,
  NLI y LLM sería sobreingeniería. Debe crecer por evidencia incremental.

## R. Orden de experimentación

1. aprobar guía de anotación, clases y coste de errores;
2. congelar 12 políticas y crear 36 casos con doble anotación;
3. ejecutar reglas actuales y análisis de errores;
4. medir retrieval de un encoder multilingüe pequeño con hard negatives;
5. evaluar NLI sobre fragmentos gold para aislar clasificación;
6. combinar retrieval + NLI y comparar un cross-encoder;
7. repetir, medir latencia/recursos y probar abstención;
8. sólo si queda una banda ambigua material, evaluar un LLM con datos minimizados;
9. ampliar corpus y ejecutar shadow antes de una decisión productiva.

## S. Qué no construir todavía

- vector database, tablas o caché persistente;
- endpoint semántico o cambios de EvidenceContract público;
- integración OpenAI/otro proveedor, prompts productivos o claves;
- descarga/serving de modelos, GPU o stack de entrenamiento;
- ontología formal/RDF o knowledge graph;
- clasificador propio, fine-tuning o LLM árbitro;
- extensión a los otros 16 controles o a Privacy Data;
- cambios de score, estados o thresholds productivos.

## T. Criterio de éxito y puerta a producción

Antes del benchmark se deben fijar umbrales. Propuesta para debatir:

1. retrieval recall@3 ≥ 95% sobre casos con evidencia;
2. **cero promociones falsas** en el test congelado para PRV-010 y PRV-012, y como
   máximo una en el total, siempre que sea corregible con abstención/guardrail;
3. mejora de al menos 10 puntos porcentuales de macro-F1 o reducción de al menos 30%
   de falsos negativos frente a reglas, sin empeorar falsos positivos;
4. citas válidas en 100% de respuestas aceptadas y al menos 95% de selección de
   evidencia gold;
5. 100% de coincidencia de clase en 10 repeticiones para local; para API, ≥99% y ningún
   cambio de promoción, además de versión fijada cuando el proveedor lo permita;
6. overhead p95 dentro del presupuesto acordado y diagnóstico total normalmente bajo
   un minuto;
7. coste, licencia, memoria, cold start, privacidad, fallbacks y operación aceptados;
8. resultado confirmado en un corpus ampliado (recomendado ≥100 casos, con suficientes
   negativos difíciles por control) y luego en shadow mode sin afectar usuarios;
9. revisión humana explícita antes de activar cualquier promoción semántica.

Si no cumple precisión conservadora, la conclusión válida es continuar sólo con
reglas y usar el corpus para mejorar diccionario/segmentación. La IA no es un objetivo
en sí misma.

## Referencias técnicas para el experimento

- Reimers y Gurevych, *Sentence-BERT* (EMNLP 2019), describe bi-encoders para
  similitud y búsqueda semántica: <https://aclanthology.org/D19-1410/>.
- Sentence Transformers documenta el patrón retrieve-and-rerank y la diferencia entre
  bi-encoder y cross-encoder: <https://www.sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html>.
- Conneau et al., *XNLI* (EMNLP 2018), presenta el benchmark multilingüe de inference,
  incluido español: <https://aclanthology.org/D18-1269/>.
- La documentación de Hugging Face distingue las etiquetas entailment, neutral y
  contradiction en NLI: <https://huggingface.co/tasks/zero-shot-classification>.
- OpenAI documenta Structured Outputs y sus límites operativos; una salida conforme al
  esquema no reemplaza validación de evidencia:
  <https://platform.openai.com/docs/guides/structured-outputs>.
- OpenAI publica sus controles de datos de API; cualquier experimento debe volver a
  revisar los términos vigentes y el proyecto concreto:
  <https://platform.openai.com/docs/guides/your-data>.

Estas referencias orientan el diseño, no preseleccionan proveedor ni modelo. Licencias,
revisiones, desempeño en español, precios y políticas de datos deben verificarse de
nuevo cuando se apruebe ejecutar el benchmark.
