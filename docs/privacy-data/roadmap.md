# Privacy Data - Roadmap

## Objetivo

Evolucionar Privacy Data desde un wizard de levantamiento hacia una experiencia simple que permita:

1. entender qué datos maneja el negocio;
2. visualizar cómo circulan;
3. revisar cómo se protegen;
4. saber qué mejorar;
5. generar respaldo y evidencia.

## Experiencia objetivo

La navegación principal propuesta es:

**Resumen · Mapa · Acciones**

El wizard deja de ser el producto completo y pasa a ser el mecanismo para construir y actualizar el mapa.

La experiencia debe mantener dos fases visibles:

### Fase 1 - Entender

**Datos · Usos · Terceros**

Objetivo: construir una primera comprensión del negocio y mostrar el mapa cuanto antes.

### Fase 2 - Proteger

**Accesos · Conservación · Seguridad · Derechos**

Objetivo: profundizar progresivamente en cómo se manejan y protegen los datos.

### Evidencia

**Respaldo · Historial · Reporte**

Evidencia es una capa transversal. No se plantea inicialmente como una tercera fase ni como una cuarta vista principal.

## Principio UX central

**Privacy Data pregunta lo necesario para entender el negocio y profundiza solo cuando encuentra algo que conviene revisar.**

La secuencia de producto es:

**Entender → Ver → Mejorar → Demostrar**

Y la secuencia de interacción es:

**Preguntar → entregar valor → preguntar → enriquecer el resultado.**

Evitar:

**Preguntar → preguntar → preguntar → mostrar todo al final.**

## Cómo se alinean las fases con las vistas

### Resumen - ¿Cómo estoy?

Muestra el avance de las dos fases:

- Fase 1 - Datos, Usos, Terceros;
- Fase 2 - Accesos, Conservación, Seguridad, Derechos.

Debe permitir distinguir rápidamente qué está revisado, qué falta y qué requiere atención.

### Mapa - ¿Cómo se manejan mis datos?

Se construye principalmente con Fase 1 y se enriquece con información posterior de Fase 2.

Debe mostrar por actividad, en simple:

- personas;
- datos;
- uso/finalidad;
- origen cuando corresponda;
- dónde se manejan;
- terceros.

Más adelante puede incorporar accesos, conservación u otros detalles sin convertir el mapa en un diagrama complejo.

### Acciones - ¿Qué hago ahora?

Es el puente entre el mapa y la profundización.

Cada hallazgo puede generar una acción concreta. Al abrir una acción pueden aparecer micro-preguntas particulares solo cuando sean necesarias.

Ejemplos:

- si hay datos de menores → revisión específica;
- si hay datos sensibles → revisión de seguridad;
- si hay terceros → detalle del tercero, relación y contrato;
- si no hay conservación definida → revisar criterio y eliminación;
- si falta claridad sobre licitud → revisar base correspondiente;
- si hay un riesgo particular → profundizar solo en ese punto.

La vista Acciones no debe ser solo una lista de recomendaciones: debe ser la puerta para seguir enriqueciendo Privacy Data.

## Bloque 1 - Fase 1 + mapa inicial

**Datos · Usos · Terceros → mostrar Resumen + Mapa.**

Objetivo:

- entregar valor temprano;
- evitar un cuestionario largo antes de mostrar resultados;
- permitir que el usuario vea una primera versión de su mapa apenas termina Fase 1.

La Fase 1 debe pedir solo lo necesario para construir el primer mapa. Las preguntas particulares o legales más profundas pueden aparecer después mediante Acciones.

Resultado esperado:

- Resumen inicial;
- Mapa inicial por actividad;
- señales de lo que falta revisar;
- primeras Acciones sugeridas.

## Bloque 2 - Fase 2 progresiva

**Accesos → Conservación → Seguridad → Derechos.**

La Fase 2 se completa en bloques pequeños. Cada bloque debe enriquecer el mapa, el resumen y las acciones sin obligar al usuario a responder todo de una vez.

Objetivo:

- reducir carga cognitiva;
- mostrar progreso visible;
- actualizar el resultado después de cada bloque;
- profundizar solo cuando una respuesta o riesgo lo justifique.

## Bloque 3 - Acciones inteligentes

Cada respuesta actualiza prioridades.

La vista Acciones debe responder:

> **¿Qué hago ahora?**

Ejemplos:

- definir base de licitud;
- completar información de un tercero;
- revisar accesos;
- definir conservación;
- mejorar una medida de seguridad;
- preparar un procedimiento para derechos.

Objetivo:

- transformar respuestas en tareas concretas;
- priorizar lo importante;
- evitar recomendaciones genéricas;
- activar micro-preguntas contextuales solo cuando corresponda.

## Bloque 4 - Evidencia

**Respaldo · Historial · Reporte.**

Objetivo:

- conservar trazabilidad;
- mostrar qué se revisó;
- registrar avances;
- generar un respaldo que pueda compartirse con un abogado, cliente o frente a una revisión.

Evidencia no se plantea inicialmente como una cuarta vista principal. Funciona como una capa transversal sobre Resumen, Mapa y Acciones.

## Antes de agregar más preguntas

Antes de desarrollar nuevas preguntas, realizar una revisión completa del cuestionario actual por **carga cognitiva**.

Evaluar cada pregunta con cuatro criterios:

1. **¿Es necesaria?**
2. **¿Se entiende?**
3. **¿Tiene demasiadas opciones?**
4. **¿Necesito preguntarla ahora?**

Regla UX de referencia:

- ideal: 4 a 6 opciones visibles;
- 7 opciones todavía aceptable;
- más de 7: buscar agrupación, sugerencias contextuales o "Ver otras opciones".

Cuando existan muchas opciones, priorizar las más probables según actividad y rubro.

## Próximos ajustes legales a incorporar

Prioridad inicial:

1. origen de los datos;
2. base de licitud;
3. rol y detalle de terceros;
4. seguridad;
5. derechos;
6. incidentes;
7. evidencia.

Estos ajustes no deben traducirse automáticamente en nuevas pantallas del wizard. Siempre evaluar primero si pueden incorporarse como:

- dato derivado;
- micro-pregunta;
- pregunta condicional;
- acción de revisión posterior.

## Principio de producto

Privacy Data debe poder ser simple para el usuario y, al mismo tiempo, construir una base cada vez más útil para explicar y respaldar cómo el negocio maneja los datos personales.

El usuario no debería sentir que completa un formulario legal. Debería sentir que construye su mapa, ve avances y resuelve temas concretos paso a paso.
