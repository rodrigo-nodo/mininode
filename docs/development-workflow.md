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

## 6. Costos de desarrollo IA

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

## 7. Métricas objetivo

Medir progresivamente:

```text
US$ / ejecución Codex
US$ / Issue terminada
US$ / PR mergeado
US$ / funcionalidad
US$ / producto
```

La métrica más útil debe evolucionar desde costo técnico por ejecución hacia costo real de desarrollo por funcionalidad/producto.

## 8. Principio económico

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

## 9. Mantenimiento

Este documento es la fuente de verdad del workflow de desarrollo de Mininode.

Actualizarlo cuando cambie de forma estable:

- el workflow;
- la división de responsabilidades;
- el criterio Codex API vs Codex directo vs ejecución mecánica;
- la estrategia de contexto;
- las métricas o criterios de costo.

No usarlo como historial detallado de PRs o ejecuciones.