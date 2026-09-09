# Privacy Web - PRV-103 semantic shadow mode

## Objetivo

Observar en tráfico real la arquitectura `PRV-103 Intent LLM V2` validada en QA6 sin darle autoridad sobre el diagnóstico público.

El flujo productivo sigue siendo determinístico. El shadow mode calcula en paralelo una segunda clasificación y registra únicamente telemetría interna para comparar resultados.

```text
EvidenceContract final
  -> formularios personales HIGH
  -> deduplicación por evidencia estructurada
  -> shadow asíncrono acotado
  -> LLM identifica intención observable
  -> Mininode mapea intención -> concrete/generic/none/unknown
  -> telemetría interna
```

## Frontera de producto

El shadow mode **no modifica**:

- resultado público de PRV-103;
- Privacy Score;
- prioridades;
- Plan de corrección;
- API;
- frontend;
- base de datos;
- `framework_version = 0.6`;
- `scoring_version = 0.1`.

La clasificación pública continúa usando la lógica determinística vigente de PRV-103. El resultado semántico solo sirve para observación interna.

## Evidencia permitida

Se envían al modelo exclusivamente los cuatro campos estructurados del mismo formulario aprobados y validados en QA6:

- `heading`;
- `legend`;
- `introductory_text`;
- `submit_text`.

No se envían fields, `nearby_text`, action URL, page title, URL del sitio ni conocimiento externo. La llamada usa `store=False`.

El modelo identifica únicamente un `intent_id`. No recibe las clases de producto. Mininode mantiene el mapeo determinístico intención -> `concrete/generic/none/unknown`, y `uncertain=true` fuerza `unknown`.

## Retención del proveedor

Para este alcance se acepta la política estándar de retención del proveedor OpenAI para los cuatro textos públicos anteriores.

La aceptación aplica únicamente a esta evidencia pública estructurada. No habilita el envío de datos ingresados por personas, nombres, emails, teléfonos, contenido de fields, URLs de formularios ni otros datos personales del visitante.

`store=False` se mantiene. Esta decisión no se interpreta como Zero Data Retention y debe revisarse si cambia el payload o el proveedor.

## Ejecución y límites

El observer:

- se ejecuta después de cerrar la inspección adaptativa, usando el `EvidenceContract` final;
- solo considera formularios personales de confianza HIGH;
- deduplica por los cuatro campos permitidos;
- limita la observación a un máximo de 10 formularios deduplicados por diagnóstico;
- rechaza un formulario si el payload de los cuatro campos supera 8.192 bytes;
- fija `max_output_tokens = 256`;
- usa timeout de 12 segundos por llamada y cero retries;
- mantiene un único worker y como máximo 2 trabajos outstanding por proceso;
- limita por defecto a 250 llamadas LLM por vida del proceso y aplica un techo duro de 1.000;
- se ejecuta fuera del camino de respuesta pública;
- es fail-open: un error del proveedor, una salida inválida, saturación de cola o falta de configuración nunca cambia ni bloquea el diagnóstico.

El límite de llamadas por proceso es un circuit breaker de shadow mode, no un sistema de billing. No sustituye monitoreo de gasto del proveedor ni un límite financiero persistente entre reinicios o múltiples réplicas.

## Primera activación controlada

La primera activación productiva queda configurada en el manifiesto de Render con:

- `PRIVACY_PRV103_SHADOW_ENABLED=true`;
- `PRIVACY_PRV103_SHADOW_SAMPLE_RATE=0.05`;
- `PRIVACY_PRV103_SHADOW_MAX_CALLS_PER_PROCESS=250`;
- `OPENAI_API_KEY` continúa como secreto externo y no se almacena en el repositorio.

Esto significa que el shadow queda habilitado para una muestra determinística aproximada del **5% de los hostnames elegibles**. El muestreo es por hostname, no por diagnóstico, por lo que la proporción real de llamadas puede diferir del 5% si el tráfico está concentrado en pocos sitios.

La activación solo tiene efecto cuando la configuración de despliegue correspondiente se sincroniza/aplica en Render. El merge del código no debe interpretarse por sí solo como evidencia de que las variables ya están efectivas en el proceso desplegado.

## Rollback

Definir `PRIVACY_PRV103_SHADOW_ENABLED=false` o retirar la variable impide nuevos enqueues.

Además:

- cada trabajo pendiente vuelve a comprobar la bandera antes de ejecutarse y se descarta con `disabled_before_execution` si ya está deshabilitado;
- un trabajo activo vuelve a comprobar la bandera antes de cada formulario y deja de iniciar llamadas nuevas si el shadow fue deshabilitado;
- una llamada al proveedor que ya está en vuelo puede terminar dentro de su timeout de 12 segundos;
- no requiere rollback de datos porque el shadow mode no persiste resultados.

## Telemetría y privacidad

Los logs del shadow mode contienen únicamente información compacta de operación:

- hostname;
- versiones de modelo, prompt y taxonomía;
- cantidades de formularios seleccionados, evaluados, omitidos y truncados;
- cantidad de llamadas LLM iniciadas;
- motivos agregados de omisión: `oversized_input`, `disabled_during_execution` y `call_budget_exhausted`;
- eventos de control como `queue_full`, `disabled_before_execution`, `missing_openai_key` y `enqueue_failed`;
- distribuciones de clases;
- acuerdo/desacuerdo entre baseline determinístico y shadow;
- `intent_id`, clase, `uncertain` y nombres de campos de evidencia en discrepancias.

No se registran textos de formularios, citas de evidencia, URLs de formularios, datos ingresados por personas ni mensajes de error del proveedor que puedan contener contenido sensible.

## Costo LLM

QA6 observó aproximadamente 1.242 tokens de entrada y 80 tokens de salida por formulario. Con la tarifa de referencia usada durante la revisión de septiembre de 2026, el costo observado fue aproximadamente **US$0,0066 por formulario**.

Ese promedio sirve para planificación, no es un techo contractual. Los límites de este shadow reducen el riesgo de outliers mediante máximo 10 formularios por diagnóstico, payload máximo de 8.192 bytes, `max_output_tokens = 256`, cola acotada, sample rate de 5% y presupuesto de 250 llamadas por proceso.

Al promedio observado, 250 llamadas representan cerca de US$1,64 por vida del proceso. El gasto real puede variar por tokenización, razonamiento, reinicios, réplicas y distribución de tráfico.

## Base validada

La arquitectura usa la configuración congelada y validada en QA6:

- modelo `gpt-5.6-sol`;
- reasoning `medium`;
- prompt `prv103-intent-v2-01`;
- taxonomía `prv103-intents-v1`.

QA6 terminó PASS sobre 46 formularios HIGH deduplicados de un holdout nuevo, con 100% de exactitud de clase en dos runs, 100% de concrete recall, 0 falsas promociones a `concrete`, 0 falsos `none` adversos y 100% de estabilidad de clase.

Ese resultado habilita observación en shadow mode, no reemplazo automático de la decisión productiva.

## Qué medir durante shadow

Antes de ampliar el sample rate o promover la clasificación semántica a autoridad productiva se deben revisar, como mínimo:

- volumen de diagnósticos muestreados;
- formularios evaluados y omitidos;
- acuerdo y desacuerdo con PRV-103 determinístico;
- casos de promoción a `concrete`;
- proporción de `unknown`;
- errores, `queue_full` y agotamiento de presupuesto;
- llamadas LLM y costo real observado.

Cualquier promoción desde shadow a autoridad productiva requiere criterios explícitos y revisión independiente en un PR separado.
