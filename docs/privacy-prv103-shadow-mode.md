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

Se envían al modelo exclusivamente los cuatro campos estructurados del mismo formulario ya aprobados y validados en QA6:

- `heading`;
- `legend`;
- `introductory_text`;
- `submit_text`.

No se envían fields, `nearby_text`, action URL, page title, URL del sitio ni conocimiento externo. La llamada usa `store=False`.

El modelo identifica únicamente un `intent_id`. No recibe las clases de producto. Mininode mantiene el mapeo determinístico intención -> `concrete/generic/none/unknown`, y `uncertain=true` fuerza `unknown`.

`store=False` no se considera por sí solo una garantía de Zero Data Retention. Antes de activar tráfico real se debe confirmar que los controles de retención del proveedor y del proyecto OpenAI son aceptables para Privacy Web.

## Ejecución y límites

El observer:

- está deshabilitado por defecto;
- se ejecuta después de cerrar la inspección adaptativa, usando el `EvidenceContract` final;
- solo considera formularios personales de confianza HIGH;
- deduplica por los cuatro campos permitidos;
- limita la observación a un máximo de 10 formularios deduplicados por diagnóstico;
- rechaza un formulario si el payload de los cuatro campos supera 8.192 bytes;
- fija `max_output_tokens = 256`, incluyendo el presupuesto de razonamiento y salida de la Responses API;
- usa timeout de 12 segundos por llamada y cero retries;
- mantiene un único worker y como máximo 2 trabajos outstanding por proceso, por lo que no puede crecer un backlog ilimitado;
- limita por defecto a 250 llamadas LLM por vida del proceso y aplica un techo duro de 1.000 aunque la variable de entorno solicite más;
- se ejecuta fuera del camino de respuesta pública;
- es fail-open: un error del proveedor, una salida inválida, saturación de cola o falta de configuración nunca cambia ni bloquea el diagnóstico.

El límite de llamadas por proceso es un circuit breaker de shadow mode, no un sistema de billing. No sustituye monitoreo de gasto del proveedor ni un límite financiero persistente entre reinicios o múltiples réplicas.

## Activación

La integración queda disponible pero **no activada por este PR**.

Variables:

- `PRIVACY_PRV103_SHADOW_ENABLED=true` habilita el observer;
- `PRIVACY_PRV103_SHADOW_SAMPLE_RATE` define una fracción entre `0` y `1` y usa muestreo determinístico por hostname; si no se configura, el valor efectivo es **0**;
- `PRIVACY_PRV103_SHADOW_MAX_CALLS_PER_PROCESS` define el presupuesto de llamadas del proceso; default 250 y techo duro 1.000;
- `OPENAI_API_KEY` usa la credencial ya existente del backend.

Por seguridad operacional, habilitar `PRIVACY_PRV103_SHADOW_ENABLED=true` sin definir un sample rate positivo no produce llamadas al LLM.

Para una primera activación real se recomienda un sample rate pequeño, por ejemplo 5%-10%, y revisar volumen, errores y costo antes de ampliarlo.

## Rollback

Definir `PRIVACY_PRV103_SHADOW_ENABLED=false` o retirar la variable impide nuevos enqueues.

Además:

- cada trabajo pendiente vuelve a comprobar la bandera antes de ejecutarse y se descarta con `disabled_before_execution` si ya está deshabilitado;
- un trabajo activo vuelve a comprobar la bandera antes de cada formulario y deja de iniciar llamadas nuevas si el shadow fue deshabilitado;
- una llamada al proveedor que ya está en vuelo no se puede cancelar de forma segura desde este observer y puede terminar dentro de su timeout de 12 segundos;
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

QA6 observó aproximadamente 1.242 tokens de entrada y 80 tokens de salida por formulario. Con la tarifa de referencia de GPT-5.6 Sol usada durante la revisión de septiembre de 2026, el costo observado fue aproximadamente **US$0,0066 por formulario**.

Ese promedio sirve para planificación, no es un techo contractual. Los límites de este shadow reducen el riesgo de outliers mediante:

- máximo 10 formularios por diagnóstico;
- payload máximo de 8.192 bytes por formulario;
- `max_output_tokens = 256`;
- cola acotada;
- sample rate explícito con default 0;
- 250 llamadas por proceso por defecto y máximo duro de 1.000.

Al promedio observado, 250 llamadas representan cerca de US$1,64 y 1.000 llamadas cerca de US$6,57 por vida del proceso. El gasto real puede variar por tokenización, razonamiento, distribución de formularios, reinicios y cantidad de réplicas. Antes de activar o ampliar el sample rate se deben volver a verificar los precios vigentes del proveedor.

## Base validada

La arquitectura usa la configuración congelada y validada en QA6:

- modelo `gpt-5.6-sol`;
- reasoning `medium`;
- prompt `prv103-intent-v2-01`;
- taxonomía `prv103-intents-v1`.

QA6 terminó PASS sobre 46 formularios HIGH deduplicados de un holdout nuevo, con 100% de exactitud de clase en dos runs, 100% de concrete recall, 0 falsas promociones a `concrete`, 0 falsos `none` adversos y 100% de estabilidad de clase.

Ese resultado habilita observación en shadow mode, no reemplazo automático de la decisión productiva.

## Paso posterior

Antes de promover la clasificación semántica desde shadow a autoridad productiva se debe revisar evidencia real del shadow mode, definir criterios de promoción y ejecutar una revisión independiente del cambio de decisión. Ese trabajo corresponde a un PR separado.
