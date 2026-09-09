# Privacy Web - PRV-103 semantic shadow mode

## Objetivo

Observar en tráfico real la arquitectura `PRV-103 Intent LLM V2` validada en QA6 sin darle autoridad sobre el diagnóstico público.

El flujo productivo sigue siendo determinístico. El shadow mode calcula en paralelo una segunda clasificación y registra únicamente telemetría interna para comparar resultados.

```text
EvidenceContract final
  -> formularios personales HIGH
  -> deduplicación por evidencia estructurada
  -> shadow asíncrono
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

## Ejecución

El observer:

- está deshabilitado por defecto;
- se ejecuta después de cerrar la inspección adaptativa, usando el `EvidenceContract` final;
- solo considera formularios personales de confianza HIGH;
- deduplica por los cuatro campos permitidos;
- limita la observación a un máximo de 10 formularios deduplicados por diagnóstico;
- se encola fuera del camino de respuesta pública;
- es fail-open: un error del proveedor, una salida inválida o la ausencia de configuración nunca cambia ni bloquea el diagnóstico.

## Activación

La integración queda disponible pero **no activada por este PR**.

Variables:

- `PRIVACY_PRV103_SHADOW_ENABLED=true` habilita el observer;
- `PRIVACY_PRV103_SHADOW_SAMPLE_RATE` define una fracción entre `0` y `1` y usa muestreo determinístico por hostname;
- `OPENAI_API_KEY` usa la credencial ya existente del backend.

Rollback operativo: definir `PRIVACY_PRV103_SHADOW_ENABLED=false` o retirar la variable. No requiere rollback de datos porque el shadow mode no persiste resultados.

## Telemetría y privacidad

Los logs del shadow mode contienen únicamente información compacta de operación:

- hostname;
- versiones de modelo, prompt y taxonomía;
- cantidades de formularios observados;
- distribuciones de clases;
- acuerdo/desacuerdo entre baseline determinístico y shadow;
- `intent_id`, clase, `uncertain` y nombres de campos de evidencia en discrepancias.

No se registran textos de formularios, citas de evidencia, URLs de formularios, datos ingresados por personas ni mensajes de error del proveedor que puedan contener contenido sensible.

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
