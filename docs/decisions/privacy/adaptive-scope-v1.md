# Privacy — Adaptive Scope V1

Estado: Aprobado
Fecha: 2026-08-13

## Decisión

Privacy Diagnostic V1 utiliza un alcance adaptativo y acotado.

El diagnóstico:

- inspecciona HOME obligatoriamente;
- identifica gaps de evidencia;
- expande hacia páginas públicas relevantes cuando pueden aportar evidencia;
- prioriza las categorías definidas por Adaptive Scope;
- utiliza un máximo de 5 páginas intentadas;
- puede terminar antes si no existen gaps resolubles, candidates disponibles o presupuesto de tiempo.

## Objetivo

Obtener evidencia suficiente para un diagnóstico inicial útil sin realizar un crawling exhaustivo del sitio.

## Alcance

El número de páginas analizadas no es fijo.

Según el sitio, el diagnóstico puede inspeccionar solamente HOME o expandirse hacia páginas adicionales relevantes.

Una página fallida cuenta como intento, pero no como página analizada.

## Limitación explícita

Privacy Diagnostic V1 no pretende descubrir ni revisar exhaustivamente todas las páginas o formularios de un sitio.

Por lo tanto, encontrar y evaluar un formulario no implica que todos los formularios existentes hayan sido inspeccionados.

Los resultados representan las señales encontradas dentro del alcance efectivamente inspeccionado.

## Evidencia de validación

La validación en sitios reales mostró comportamiento adaptativo de:

- 1 página;
- 2 páginas;
- 3 páginas;
- hasta el máximo de 5 intentos.

También se observaron distintas secuencias de categorías según los gaps detectados.

## Decisión sobre PRV-104

PRV-104 puede continuar justificando expansión cuando exista una página candidata capaz de aportar evidencia.

No se detiene necesariamente después de encontrar el primer formulario, porque un sitio puede contener múltiples formularios con tratamientos diferentes.

## Fuera de alcance V1

Queda para una versión posterior una revisión ampliada capaz de descubrir y evaluar una mayor cantidad de formularios y páginas relevantes.

Esto podría constituir un nivel de diagnóstico más profundo que el diagnóstico inicial.

---
