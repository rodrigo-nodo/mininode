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
entendida como un proceso experimental y no como una cascada predeterminada: conservar
las reglas como línea base y evaluator autoritativo, construir primero el golden set y
hacer que el duelo principal fuera de producción sea **NLI/cross-encoder directo sobre
todos los fragmentos frente a embeddings + NLI/cross-encoder**. Si la calidad es
equivalente, se elige el camino directo por simplicidad. No se recomienda poner ahora
un LLM en el camino crítico ni usar embeddings como clasificador.

La hipótesis a validar es:

1. para una política acotada y decenas de fragmentos, NLI/cross-encoder directo puede
   ser suficientemente barato y simple para evitar embeddings;
2. embeddings pueden reducir candidatos con buen recall cuando la escala lo justifica,
   pero son una optimización de retrieval, no un requisito arquitectónico;
3. NLI/cross-encoder distingue mejor relación, negación y alcance;
4. código determinista valida el esquema, aplica umbrales conservadores y produce el
   estado final;
5. ante duda o desacuerdo, se conserva el resultado determinista conservador.

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
| NLI/cross-encoder directo | Evalúa todos los fragmentos sin pérdida previa por retrieval y elimina un componente y su umbral | El número de inferencias crece con fragmentos × hipótesis/controles; puede resultar lento al escalar | Primer experimento semántico para el corpus acotado actual |
| Embeddings + NLI | Separa recall (retrieval) de precisión (entailment) y limita cómputo | Acumula errores de segmentación, retrieval y NLI; exige calibración por control | Comparador del camino directo; se adopta sólo con ventaja medida |
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

### Arquitectura 3 — reglas + NLI/cross-encoder directo

`content_text → segmentación → evaluar todos los fragmentos contra hipótesis/control →
evidencia estructurada → evaluator`

Es el primer candidato semántico a probar. No usa embeddings ni top-k previo y evita
que retrieval descarte la única evidencia válida. Permite medir directamente negación,
relación sujeto/objeto y alcance. Su coste es el producto de fragmentos, hipótesis y
controles, por lo que deben registrarse inferencias, memoria y latencia. Con una sola
política acotada y tres controles puede ser más simple y suficientemente rápido.
Esta alternativa es **NLI/cross-encoder directo sobre todos los fragmentos**.

### Arquitectura 4 — reglas + embeddings + NLI/cross-encoder

`content_text → segmentación → retrieval top-k → entailment/clasificación → evidencia
estructurada → evaluator`

Es el segundo candidato del duelo. Ejecutar reglas primero; reutilizar una única
segmentación y embeddings para los tres controles; aplicar NLI a pocos candidatos;
aceptar sólo clases y citas provenientes literalmente de los fragmentos de entrada.
La ausencia de entailment no prueba `none`: significa evidencia semántica insuficiente.
Debe demostrar que reduce latencia/coste sin perder evidencia frente a Arquitectura 3.

### Arquitectura 5 — reglas + LLM fallback

`reglas → incertidumbre explícita → LLM → evidencia estructurada → evaluator`

Es flexible, pero «incertidumbre» debe definirse por código (señales contradictorias,
scores en banda gris o candidatos sin decisión), no por intuición del modelo. Antes de
considerarla se requieren contrato estricto, lista cerrada de clases, citas por offsets,
validación de que cada cita existe, timeout, presupuesto, política de proveedor y
fallback conservador.

### Arquitectura 6 — embeddings → NLI → LLM residual

Es técnicamente coherente, pero hoy innecesariamente compleja. Añade tres umbrales,
dos familias de modelos, observabilidad, fallos y costes para sólo tres controles. Sólo
se justificaría si el benchmark ampliado muestra: retrieval con alto recall, NLI con
pocos falsos positivos pero una banda ambigua relevante, y mejora material del LLM en
esa banda sin romper estabilidad, privacidad ni latencia.

## F. Arquitectura posible a 12 meses

Si la evidencia experimental lo respalda:

1. extractor y segmentador agnósticos al producto;
2. catálogo versionado de conceptos, hipótesis y clases por control;
3. clasificador semántico directo por pares, local y calibrado por control;
4. retrieval local o por servicio encapsulado sólo si el volumen de documentos,
   controles o fragmentos hace necesario reducir candidatos;
5. `SemanticEvidence` interno con fuente, offsets, clase, scores técnicos y versión;
6. policy gate determinista que puede abstenerse;
7. evaluator y score actuales como única autoridad de estados;
8. shadow evaluation, métricas de drift y suite de regresión sintética;
9. LLM opcional sólo para una banda residual, si aporta valor medido;
10. corpus más grande que eventualmente permita entrenar o ajustar un clasificador.

La ruta simple es `segmentación → clasificador semántico directo`; sólo al escalar pasa
a `segmentación → retrieval → clasificador semántico`. La interfaz del clasificador
debería recibir texto y conceptos, no objetos del crawler, para que Privacy Data pueda
usar la misma semántica con otra procedencia y reglas de acceso.

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

1. **segmentación:** ¿el fragmento conserva el contexto necesario y los offsets?;
2. **NLI directo sobre todos los fragmentos:** ¿produce clase y evidencia sin retrieval?;
3. **retrieval:** ¿aparece al menos un fragmento gold en top-k?;
4. **NLI sobre top-k:** dado lo recuperado, ¿produce la clase correcta?;
5. **end-to-end:** ¿cada pipeline produce clase y cita correctas desde el mismo texto?;
6. **abstención:** ¿evita promover evidencia ante neutralidad o baja confianza?

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

1. **A — reglas actuales:** `content_text → regex/reglas → adapter`, sin cambios;
2. ontología/reglas expandidas como baseline opcional;
3. **B — embeddings:** segmentación, similitud y retrieval top-k; medir retrieval y no
   usar similitud como autoridad final;
4. **C — NLI/cross-encoder directo:** evaluar todos los fragmentos contra cada
   hipótesis/control, sin embeddings ni top-k previo;
5. **D — embeddings + NLI/cross-encoder:** ejecutar el mismo clasificador sobre top-k y
   comparar específicamente con C;
6. **E — LLM estructurado:** sólo con fragmentos relevantes, acceso aprobado y el mismo
   contrato de clase/evidencia;
7. **F — humano:** golden truth.

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
11. número de fragmentos por política e inferencias NLI por control/diagnóstico;
12. latencia p50/p95 total y por control, separando segmentación, retrieval y
    clasificación, y ganancia real de velocidad aportada por embeddings;
13. memoria máxima y ejecución/costo estimado por diagnóstico;
14. número de thresholds y riesgo/tasa de pérdida de evidencia por retrieval;
15. rúbrica ordinal de explicabilidad, dependencia externa, complejidad de
    implementación/operación y ejecución local.

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

- segmentar una vez y reutilizar los mismos fragmentos para PRV-008/010/012;
- medir primero el barrido directo de fragmentos × hipótesis y agrupar inferencias
  cuando el runtime lo permita;
- en el pipeline con retrieval, calcular embeddings una vez y reutilizarlos para los
  tres controles;
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

- En el camino directo, comparar cada fragmento —incluido «mantener registros de
  usuarios y pedidos»— con hipótesis como «La política declara una finalidad concreta
  para tratar datos personales» y las hipótesis específicas de la ontología.
- En el camino con retrieval, usar una hipótesis por concepto de finalidad y ejemplos
  de paráfrasis; comprobar que top-k no pierda listas o formulaciones inesperadas.
- Clasificar `concrete` sólo si el fragmento vincula una acción/uso de datos con una
  finalidad específica; una lista de propósitos puede aportar varias evidencias.
- `generic` requiere referencia al tratamiento/uso sin finalidad concreta; ausencia de
  match es `none`, no `generic`.
- Es el caso donde ontología y embeddings probablemente aporten más recall.

### PRV-010 — destinatarios

- Prioridad máxima de precisión: exigir relación entre datos/comunicación y receptor.
- En NLI directo, «Este sitio contiene enlaces a terceros» frente a «La política
  declara que datos personales pueden comunicarse a terceros» debe resultar neutral/no
  entailment; «Podemos comunicar datos personales a proveedores que prestan servicios»
  debe resultar entailment.
- Hipótesis separadas para comunicación explícita, categoría genérica y no comunicación;
  `explicit_none` necesita negación inequívoca cuyo objeto sean datos.
- «Enlaces», contenido, cookies o servicios «de terceros» son hard negatives salvo que
  otra oración declare transferencia/comunicación.
- Embeddings solos son especialmente inadecuados; NLI o clasificador relacional y
  guardrails léxicos son necesarios.

### PRV-012 — conservación

- Exigir objeto, evento/plazo/criterio y alcance. Etiquetar `retention_scope` como
  general o específico.
- «La información de cookies utilizada para estadísticas se elimina posteriormente»
  frente a una hipótesis de criterio general de conservación debe resultar neutral/no
  entailment; «Los datos se conservarán mientras dure la relación contractual» debe
  resultar entailment.
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
- **NLI/cross-encoder directo:** primer experimento semántico porque el documento está
  acotado y elimina retrieval, su threshold y su posible pérdida de evidencia. Debe
  medirse, no asumirse, que su número de inferencias cumple latencia y memoria.
- **Embeddings + NLI/cross-encoder:** segundo lado del duelo; separa retrieval y
  decisión y puede escalar mejor. NLI encaja conceptualmente con entailment; un
  cross-encoder de relevancia sirve para reranking y uno entrenado para clases puede
  competir. Sólo se prefiere si aporta velocidad/escala real sin degradar evidencia.
- **LLM:** no es la primera opción. Evaluarlo después, con fragmentos mínimos y salida
  validada, para saber si resuelve casos residuales; no asumir que temperatura cero lo
  vuelve determinista.
- **Cascada híbrida:** arquitectura objetivo razonable, pero desplegar ahora retrieval,
  NLI y LLM sería sobreingeniería. Debe crecer por evidencia incremental.

## R. Orden de experimentación

1. aprobar guía de anotación, clases y coste de errores, congelar 12 políticas y crear
   36 casos con doble anotación;
2. ejecutar reglas actuales y analizar errores;
3. probar NLI/cross-encoder directo sobre fragmentos gold para aislar clasificación;
4. probarlo end-to-end sobre todos los fragmentos segmentados;
5. medir retrieval de embeddings con hard negatives;
6. combinar embeddings + NLI/cross-encoder sobre top-k;
7. comparar C frente a D en calidad, falsos positivos, evidencia, inferencias, memoria,
   thresholds, complejidad y latencia;
8. sólo si queda ambigüedad material residual, evaluar un LLM con datos minimizados;
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

1. si se usa retrieval, recall@3 ≥ 95% sobre casos con evidencia; el camino directo no
   queda condicionado a esta métrica;
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

La regla del duelo C frente a D es explícita: si NLI/cross-encoder directo alcanza
precisión igual o superior, mantiene falsos positivos iguales o menores y cumple el
presupuesto de latencia, **no se añaden embeddings inicialmente**. Si el camino directo
es demasiado lento o costoso, embeddings se evalúan como reducción de candidatos y
deben probar una ganancia suficiente sin perder evidencia gold.

Si no cumple precisión conservadora, la conclusión válida es continuar sólo con
reglas y usar el corpus para mejorar diccionario/segmentación. La IA no es un objetivo
en sí misma.

Por tanto, para Mininode Privacy hoy: mantener reglas como baseline productivo; hacer
de NLI/cross-encoder directo el primer experimento semántico; compararlo después con
embeddings + NLI/cross-encoder; incorporar embeddings sólo si demuestran una ventaja
real de latencia o escala; y postergar el LLM para una ambigüedad residual demostrada.
La entrada a producción sólo puede ocurrir después del corpus ampliado, los umbrales
anteriores, revisión humana y shadow mode.

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
