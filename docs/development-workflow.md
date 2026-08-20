# Mininode - Workflow de desarrollo

## Propósito

Este documento define cómo se decide y ejecuta el trabajo de desarrollo de Mininode, buscando minimizar intervención manual y controlar el costo de IA.

## 1. Workflow principal

```text
Rodrigo
   ↓
ChatGPT
   ↓
crea Issue en GitHub
   ↓
/codex
   ↓
GitHub Action
   ↓
Codex API implementa
   ↓
rama + commit + PR
   ↓
ChatGPT revisa
   ↓
Rodrigo valida resultado
   ↓
MERGE
```

Objetivo: Rodrigo indica qué quiere y luego interviene principalmente para validar/aprobar el resultado.

## 2. Roles

- **Rodrigo** - define necesidad y valida el resultado como Product Owner.
- **ChatGPT** - analiza, diseña cuando corresponde, convierte el trabajo en Issues implementables y revisa el PR.
- **Codex API** - ejecuta automáticamente Issues suficientemente definidas.
- **Codex directo** - se usa principalmente para trabajo exploratorio o complejo que todavía requiere descubrir/diseñar la solución.
- **Backend / GitHub Actions** - ejecutan trabajo mecánico, batch o diagnóstico que no necesita razonamiento de programación en cada ejecución.

## 3. Regla de decisión

No clasificar únicamente por cantidad de archivos o tamaño aparente.

La pregunta principal es:

> ¿ChatGPT puede convertir el requerimiento en una Issue precisa e implementable sin pedirle a Codex que descubra qué solución debemos construir?

```text
¿Necesita programar?
 │
 ├─ NO → Backend / GitHub Action
 │
 └─ SÍ
      ↓
 ¿ChatGPT puede convertirlo
 en una Issue implementable?
      │
      ├─ SÍ → Codex API
      │
      └─ NO → Codex directo
              para explorar/diseñar
              ↓
          dividir en Issues
              ↓
           Codex API
```

### Codex API - ejecutor

Preferir cuando:

- el objetivo es claro y específico;
- el alcance está identificado;
- la arquitectura necesaria ya existe o está decidida;
- los componentes afectados son razonablemente predecibles;
- existen criterios claros para validar el resultado;
- la tarea puede expresarse como una Issue implementable.

### Codex directo - explorador

Preferir cuando:

- todavía hay que descubrir la solución;
- existen alternativas arquitectónicas relevantes;
- el alcance es incierto o transversal;
- se necesita investigar antes de decidir qué construir;
- ChatGPT todavía no puede escribir una Issue suficientemente precisa.

El resultado ideal del trabajo exploratorio es una decisión que pueda dividirse en una o más Issues acotadas para Codex API.

### Backend / GitHub Actions - ejecución mecánica

Preferir cuando no se necesita programar o razonar nuevamente en cada ejecución, por ejemplo:

- batches;
- diagnósticos repetibles;
- ejecución de tests;
- procesamiento determinístico;
- tareas operativas automatizables.

No gastar tokens de IA para trabajo que puede ejecutar código convencional.

## 4. Trabajo grande

Un requerimiento grande no implica automáticamente usar Codex directo para toda la implementación.

Preferir:

```text
Problema grande
      ↓
ChatGPT analiza/diseña
      ↓
Issue A acotada → Codex API
Issue B acotada → Codex API
Issue C acotada → Codex API
```

Usar Codex directo solo cuando la etapa de exploración/diseño todavía no puede resolverse suficientemente antes de implementar.

## 5. Contexto para Codex API

El contexto debe ser selectivo:

```text
Issue
  ↓
AGENTS.md
  ↓
documento específico del producto
  ↓
docs/architecture.md solo si hace falta
  ↓
código y pruebas relacionados
```

No reconstruir todo Mininode en cada ejecución.

Los hechos y diagnósticos ya investigados deben incluirse resumidos en la Issue para evitar que Codex los redescubra innecesariamente.

Para Issues acotadas, Codex API comienza exclusivamente por los archivos objetivo que indique la Issue. Solo amplía contexto ante una dependencia concreta (import, llamada, prueba relacionada o error observado); si aún falta información para implementar con seguridad, lo reporta en vez de explorar el repositorio indiscriminadamente. Ejecuta primero pruebas focalizadas y no amplía automáticamente a suites generales cuando las comprobaciones necesarias ya son suficientes.

El Issue Worker no fija una lista universal de archivos o productos: delega el enrutamiento selectivo a la Issue y a `AGENTS.md`. Tampoco reduce globalmente el esfuerzo de razonamiento del modelo, porque el mismo worker puede recibir tareas de distinta complejidad y hacerlo podría degradar calidad o seguridad.

## 6. Documentos de contexto relacionados

El workflow se apoya en documentos separados para evitar cargar todo el contexto de Mininode en cada tarea:

- `AGENTS.md` - reglas generales para los agentes de código y enrutamiento del contexto.
- `docs/architecture.md` - arquitectura general y estable de Mininode.
- `docs/privacy.md` - contexto específico y vigente de Mininode Privacy.
- `docs/development-workflow.md` - proceso de desarrollo, automatización y criterios de costo.

Cada documento tiene una responsabilidad distinta. Evitar duplicar información innecesariamente entre ellos.

Cuando aparezca un nuevo producto que necesite contexto propio, puede crearse un documento específico dentro de `docs/` y registrarse en `AGENTS.md` para que los agentes sepan cuándo consultarlo.

Ejemplo:

```text
AGENTS.md
docs/
├── architecture.md
├── development-workflow.md
├── privacy.md
├── futuro-producto-a.md
└── futuro-producto-b.md
```

La existencia de un documento no implica que deba cargarse en todas las tareas. La Issue y `AGENTS.md` determinan qué contexto corresponde consultar.

## 7. Protocolo operativo de interacción

La interacción debe minimizar pasos manuales y comentarios intermedios innecesarios.

### Principio

> No narrar ni pedir a Rodrigo pasos que ChatGPT pueda ejecutar directamente con las herramientas disponibles.

Flujo esperado:

```text
ChatGPT ejecuta
   ↓
GitHub Action
   │
   ├─ verde → continuar con la siguiente parte que ChatGPT pueda ejecutar
   │
   └─ rojo → diagnosticar directamente si es posible;
             pedir a Rodrigo solo el dato o captura que no sea accesible
   ↓
PR listo
   ↓
ChatGPT revisa
   ↓
entrega link directo al PR + acción esperada
   ↓
Rodrigo valida / mergea
   ↓
"listo"
   ↓
ChatGPT continúa
```

Reglas operativas:

- Después de iniciar una ejecución automatizada, evitar narrar cada paso interno.
- Si ChatGPT puede consultar directamente el estado o error de GitHub Actions, debe hacerlo sin pedir una captura.
- Si no puede observar el resultado de la Action, Rodrigo puede indicar **"verde"** o **"rojo"** como señal mínima.
- Ante **verde**, ChatGPT continúa automáticamente con su parte del flujo sin pedir confirmaciones innecesarias.
- Ante **rojo**, ChatGPT investiga el fallo y solicita únicamente información que no pueda obtener directamente.
- Cuando exista un PR, ChatGPT debe revisarlo antes de recomendar merge.
- Cuando el PR esté listo para intervención humana, ChatGPT debe entregar siempre el link directo al PR.
- La respuesta debe indicar claramente una única acción esperada cuando corresponda: **mergear**, **no mergear**, **esperar** o **enviar el dato faltante**.
- Después de que Rodrigo indique que el merge está listo, ChatGPT continúa con la validación o siguiente paso acordado.

El objetivo es acercarse progresivamente a:

```text
Rodrigo pide → sistema ejecuta → Rodrigo aprueba
```

## 8. Costos de desarrollo IA

Separar:

- **ChatGPT Plus** - costo fijo.
- **Codex directo** - incluido/sujeto al plan de ChatGPT.
- **Codex API** - costo variable adicional.
- **GitHub Actions / infraestructura** - controlar si pasa a ser material.

### Línea base inicial - 19-ago-2026

Antes de la optimización de contexto:

- costo Codex API acumulado: **US$5,02**;
- requests: **116**;
- tokens de entrada: **3,286 M**;
- incluye construcción del workflow, pruebas, errores y desarrollo real.

Esta línea base no representa todavía el costo normal de una tarea productiva.

## 9. Métricas objetivo

Medir progresivamente:

```text
US$ / ejecución Codex
US$ / Issue terminada
US$ / PR mergeado
US$ / funcionalidad
US$ / producto
```

La métrica más útil debe evolucionar desde costo técnico por ejecución hacia costo real de desarrollo por funcionalidad/producto.

## 10. Principio económico

No reemplazar Codex directo por API indiscriminadamente.

La API se justifica principalmente cuando transforma:

```text
copiar prompts + mover información manualmente
```

en:

```text
pedir → implementar → revisar → aprobar
```

La automatización debe reducir trabajo manual suficiente para justificar su costo variable.

## 11. Mantenimiento

Este documento es la fuente de verdad del workflow de desarrollo de Mininode.

Actualizarlo cuando cambie de forma estable:

- el workflow;
- la división de responsabilidades;
- el criterio Codex API vs Codex directo vs ejecución mecánica;
- la estrategia de contexto;
- el protocolo operativo de interacción;
- las métricas o criterios de costo.

No usarlo como historial detallado de PRs o ejecuciones.
