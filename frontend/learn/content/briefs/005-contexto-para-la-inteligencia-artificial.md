---
id: 005
type: brief
title: Contexto para la inteligencia artificial
subtitle: La información que ayuda a obtener mejores respuestas
topics:
  - inteligencia artificial
  - negocios
updated: 2026-10
reading_time: 4
---

Una instrucción puede ser clara y, aun así, no contener suficiente información para obtener una respuesta útil.

Por ejemplo:

> Redacta una respuesta para un cliente.

La inteligencia artificial puede realizar la tarea, pero desconoce qué ocurrió, qué necesita el cliente y qué puede ofrecer la empresa. Tendrá que responder con información incompleta o asumir parte de la situación.

Si se agregan algunos antecedentes, el resultado puede cambiar:

> Tenemos una tienda de artículos deportivos. Un cliente recibió un producto diferente del que compró y solicita una solución. Nuestra política permite cambios dentro de los primeros 30 días. Redacta una respuesta cordial explicando que puede solicitar el cambio.

Esa información adicional es **contexto**.

## Qué es el contexto

El contexto es la información que ayuda a la inteligencia artificial a comprender la situación en la que debe realizar una tarea.

Puede incluir antecedentes muy diferentes: qué ocurrió, para quién se prepara una respuesta, características de un producto, condiciones comerciales, información contenida en un documento o restricciones que deben respetarse.

No existe una cantidad de contexto adecuada para todas las tareas.

Una solicitud sencilla puede necesitar muy poco. Una tarea relacionada con una situación particular puede requerir antecedentes adicionales.

La clave no consiste en proporcionar mucha información, sino en proporcionar **información relevante**.

## Lo que la inteligencia artificial no sabe

Una herramienta de inteligencia artificial puede disponer de conocimientos generales, pero eso no significa que conozca automáticamente la realidad particular de una persona u organización.

Por ejemplo:

> Prepara una respuesta según nuestra política de cambios.

La instrucción supone que la herramienta conoce esa política.

Si esa información no se encuentra disponible en la conversación, en un documento proporcionado o mediante alguna fuente a la que la herramienta tenga acceso, no corresponde asumir que utilizará las condiciones correctas.

Una alternativa sería proporcionar la información necesaria:

> Nuestra política permite cambios hasta 30 días después de la compra, presentando el comprobante. Prepara una respuesta para un cliente que recibió un producto equivocado.

Lo mismo ocurre con precios, procedimientos, características de productos, decisiones internas o antecedentes de un proyecto.

**Cuando una respuesta depende de información particular, esa información debe estar disponible para la herramienta.**

## Elegir qué información entregar

Entregar contexto no significa copiar todo lo que se sabe sobre un tema.

Conviene preguntarse qué antecedentes cambiarían realmente la respuesta.

Para responder el reclamo del ejemplo anterior podrían importar:

- qué ocurrió;
- cuándo se realizó la compra;
- qué establece la política de cambios;
- qué solución puede ofrecerse.

En cambio, probablemente no sean necesarios la historia de la empresa, sus ventas anuales o información sobre otros clientes.

Esta distinción es importante porque incorporar antecedentes irrelevantes puede desviar la tarea o dificultar la identificación de lo importante.

## El contexto puede construirse

No siempre es necesario identificar todos los antecedentes antes de comenzar.

La conversación permite incorporar información progresivamente.

Después de recibir una primera respuesta, por ejemplo, podría agregarse:

> El cliente realizó la compra hace diez días.

Luego:

> No prometas una fecha de entrega porque todavía no está confirmada la disponibilidad del producto.

La respuesta puede ajustarse a medida que aparece información relevante.

También existe una alternativa útil cuando no está claro qué antecedentes proporcionar:

> Antes de responder, indica qué información falta para realizar correctamente la tarea.

La inteligencia artificial puede ayudar así a identificar parte del contexto necesario.

## Contexto no significa compartir todo

Hay información que podría resultar útil para una tarea y que, aun así, no corresponde entregar sin evaluar antes si es necesario hacerlo.

Datos personales, información de clientes, documentos internos o antecedentes comerciales pueden requerir precauciones adicionales.

Por eso, antes de compartir información conviene distinguir entre **lo que la IA necesita para realizar la tarea y todo lo que podría llegar a utilizar**.

## Informar mejor

Trabajar con inteligencia artificial no consiste solamente en formular una buena pregunta. Cuando una tarea depende de una situación particular, también importa proporcionar los antecedentes necesarios para comprenderla.

**Un buen contexto entrega la información relevante para realizar la tarea, sin incorporar antecedentes innecesarios.**

## Fuentes

- [OpenAI - Mejores prácticas de ingeniería de prompts para ChatGPT](https://help.openai.com/es-419/articles/10032626-prompt-engineering-best-practices-for-chatgpt)
- [OpenAI - Guía de prompt engineering](https://developers.openai.com/api/docs/guides/prompt-engineering)
- [Google Cloud - Información contextual para modelos generativos](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/introduction-prompt-design)
