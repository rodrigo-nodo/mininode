# Privacy Web y Privacy Data - Contexto de producto

Usar este documento para Issues cuyo alcance sea Privacy Web, Privacy Data o Privacy Web Inspector.

## Alcance del producto

Privacy Web y Privacy Data son dos productos complementarios de Mininode.

- **Privacy Web** revisa señales públicas del sitio web y ayuda a identificar temas de privacidad visibles hacia afuera.
- **Privacy Data** ayuda a ordenar cómo el negocio maneja datos personales por dentro.

## Privacy Data

Cada mapa puede persistir actividades categóricas ordenadas en
`privacy_data.activities`; su creación, consulta, edición y eliminación siempre se
autorizan a través del token del mapa padre. Las respuestas se validan contra el
catálogo versionado, sin almacenar datos identificatorios de personas concretas.
Privacy Data construye primero un mapa de **Datos, Usos y Terceros**. Esta Fase 1
incluye personas, tipos de información, posible presencia de menores, finalidades,
origen, lugares y participación de terceros, con sugerencias contextuales y acceso al
catálogo completo bajo demanda. Al terminar entrega un primer resultado sin exigir
Accesos ni Conservación; esos campos existentes, junto con `data_channels`, se
conservan de forma compatible para la posterior Fase 2 y su enriquecimiento.
Las actividades nuevas pueden usar internamente `data_context=unconfirmed` hasta que la
persona confirme si maneja la información para su operación, para prestar un servicio
a un cliente o en ambos contextos. Ese estado no representa una respuesta confirmada.
El resultado inmediato de Fase 1 muestra únicamente señales originadas en respuestas
recogidas durante esta fase. Observaciones sobre Accesos o Conservación se reservan
para su profundización posterior y no se presentan como hallazgos de una pregunta que
aún no se realizó.
La revisión inicial de Privacy Data se calcula al solicitarla, sin persistir el
resultado. Sus reglas determinísticas D01-D08 presentan únicamente señales objetivas
como aspectos que conviene revisar o tener presentes; no producen scoring ni una
certificación de cumplimiento.
