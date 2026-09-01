# W2.2a - Diseño de controles de formularios

## Objetivo y límites

Este documento decide el alcance de W2.2b. Es una decisión de producto y evidencia,
no una implementación: no añade controles, no cambia PRV-101 o PRV-104 y no modifica
catálogo, extracción, adaptación ni scoring.

Privacy Web observa HTML público estático. Una señal describe lo observado; no prueba
cumplimiento legal, necesidad empresarial, validez del consentimiento ni seguridad
interna. La ausencia de evidencia no es incumplimiento cuando la condición puede no
aplicar.

## Capacidad actual

El Evidence Contract v0.1 conserva por formulario `source_url`, `action` absoluto,
`method`, campos, checkboxes, 500 caracteres de `nearby_text` y enlaces de privacidad.
Los campos no checkbox incluyen nombre, tipo, etiqueta y atributo HTML `required`.
Los checkboxes solo incluyen nombre y etiqueta.

Límites relevantes:

- `nearby_text` puede mezclar títulos, botones y varios formularios del contenedor;
- no se separan encabezado, `legend`, introducción ni texto de envío;
- `required` es un atributo técnico, no una indicación visible ni validación JavaScript;
- los checkboxes no conservan `required`, `checked` ni `disabled`;
- `action` permite observar transporte y hostname, no el tratamiento posterior;
- la evidencia debe continuar asociada al formulario concreto para consolidar varios
  formularios sin mezclar señales.

PRV-104 reconoce información de privacidad o una etiqueta relacionada con aceptación.
Su valor interno actual `consent_required` replica esa coincidencia textual y **no
prueba obligatoriedad**. W2.2b no debe reinterpretarlo.

## Matriz de decisión A-I

| Candidato | Valor para usuario | Observable públicamente | Evidencia actual disponible | Evidencia faltante | Riesgo de falso positivo | Automatización | Tipo recomendado | Impacto sugerido si puntuable | Dependency/applicability | Decisión final |
|---|---|---|---|---|---|---|---|---|---|---|
| A - Finalidad/contexto | Entender para qué se solicitan los datos | parcial | `nearby_text`, etiquetas y campos | `heading`, `legend`, `introductory_text`, `submit_text` y asociación inequívoca por formulario | medio | parcial | `context` | `no_aplica` | `dependency = PRV-101`; aplica si PRV-101 = `detected` | **CONTEXT NOW**, solo tras extensión mínima |
| B - Minimización | Facilitar revisión de cantidad y categorías solicitadas | parcial | campos, tipos, nombres, etiquetas y `required` | finalidad confiable y taxonomía por caso de uso | alto | no | `defer` | `no_aplica` | requeriría PRV-101 y finalidad conocida; hoy no permite inferir necesidad | **DEFER** |
| C - Obligatorios/opcionales | Describir restricciones técnicas del formulario | parcial | `FieldEvidence.required` | indicación visible estructurada; validación dinámica sigue fuera de alcance | medio | parcial | `context` | `no_aplica` | `dependency = PRV-101`; solo observación técnica cuando aplica | **CONTEXT NOW** |
| D - Consentimiento/aceptación general obligatorio | Ninguno como regla universal; induciría una conclusión incorrecta | no | etiquetas de checkbox y señal parcial de PRV-104 | no existe evidencia capaz de hacer universal esa obligación | alto | no | `reject` | `no_aplica` | no aplicable: no todo formulario requiere checkbox o consentimiento | **REJECT** |
| E - Marketing separado | Mostrar si una preferencia promocional está separada de la finalidad principal | parcial | etiquetas y formulario asociado | finalidad principal confiable; checkbox `required`, `checked` y `disabled` | medio | parcial | `defer` | `no_aplica` | solo formulario no promocional con opción promocional inequívoca; newsletter dedicado no aplica | **DEFER** |
| F - Datos especialmente delicados | Priorizar revisión humana de recopilaciones de mayor riesgo | parcial | nombre, tipo y etiqueta de campo | taxonomía conservadora, combinaciones y benchmark de negativos | alto | parcial | `defer` | `no_aplica` | solo etiquetas explícitas dentro de formulario personal; no clasificación jurídica | **DEFER** |
| G - Menores | Priorizar revisión de formularios aparentemente relacionados con menores | parcial | nombres y etiquetas de campos, `nearby_text` | evidencia por formulario y combinaciones semánticas validadas | alto | parcial | `defer` | `no_aplica` | señal explícita de menor o combinación alumno/apoderado; términos aislados no bastan | **DEFER** |
| H - Envío seguro | Advertir transporte HTTP observable al cargar o enviar datos | sí | `source_url` y `action` absoluto por formulario | ninguna para la clasificación principal | bajo | sí | `conditional_evaluation` | `medio` | `dependency = PRV-101`; aplica solo si PRV-101 = `detected` | **IMPLEMENT NOW** |
| I - Destino externo | Mostrar que el envío apunta a otro hostname | sí | `source_url` y `action` absoluto | hostnames pueden derivarse; no requiere ampliar el contrato | bajo | sí | `context` | `no_aplica` | `dependency = PRV-101`; aplica a formularios personales con URL HTTP(S) evaluable | **CONTEXT NOW** |

## Decisión W2.2b

### IMPLEMENT NOW

- **H - Envío seguro del formulario.** Nuevo control puntuable, automatizable y
  condicional a PRV-101.

### CONTEXT NOW

- **A - Finalidad visible del formulario.** Control contextual después de separar
  evidencia textual mínima y trazable por formulario.
- **C - Campos obligatorios/opcionales.** Contexto técnico basado en el atributo HTML
  `required`; no afirma necesidad, opcionalidad real ni visibilidad.
- **I - Destino externo observable.** Contexto objetivo cuando `source hostname` y
  `action hostname` son distintos; no afirma que pertenezcan a organizaciones distintas.

### DEFER

- **B - Minimización.** Puede existir después como inventario contextual, pero no será
  puntuable con evidencia actual ni calificará campos como innecesarios.
- **E - Marketing separado.** Requiere finalidad principal y evidencia adicional del
  checkbox.
- **F - Datos especialmente delicados.** Requiere taxonomía y benchmark conservadores.
- **G - Menores.** Requiere combinaciones explícitas y casos negativos por formulario.

### REJECT

- **D - Consentimiento general obligatorio.** Se rechaza el concepto “todo formulario
  debe tener checkbox o consentimiento”. Esto no elimina PRV-104 ni impide diseñar en
  el futuro una elección específica cuando exista aplicabilidad observable.

**Conteos:** IMPLEMENT NOW: **1**; CONTEXT NOW: **3**; DEFER: **4**; REJECT: **1**.

## A - Finalidad visible

### Definición de catálogo para W2.2b

- `type = context`
- `score_weight = 0`
- `dependency = PRV-101`
- aplicabilidad: solo cuando PRV-101 = `detected`

No se define como `conditional_evaluation`: en W2.2b es contextual y no puntúa. La
clasificación semántica interna y los resultados públicos son niveles diferentes:

| Evidencia interna | Resultado del control |
|---|---|
| `concrete` | `detected` |
| `generic` | `partial` |
| `none` | `not_detected` |
| PRV-101 = `not_detected` | `not_applicable` |
| limitación técnica o asociación insuficiente | `not_evaluable` |

Una finalidad concreta combina acción o resultado comprensible, como solicitar una
cotización, reservar una hora, recibir respuesta o suscribirse a un newsletter.
`Enviar`, `Continuar`, `Formulario` o `Contacto` aislados son genéricos. El texto debe
estar inequívocamente asociado al formulario; no basta una frase en otra sección.

## B - Minimización visible

Los campos y categorías observados pueden formar un inventario para revisión humana,
pero el HTML no revela necesidades contractuales, operativas o regulatorias. No se
implementará como control puntuable ni se usarán conclusiones como “excesivo” o
“innecesario”. Incluso con finalidad visible, una matriz universal produciría falsos
positivos. La decisión es DEFER.

## C - Campos obligatorios y opcionales

`FieldEvidence.required` permite afirmar únicamente que existe el atributo HTML
`required`. Su ausencia no demuestra que el campo sea opcional, porque puede existir
validación dinámica. Tampoco demuestra una indicación visible. W2.2b puede mostrar
conteos técnicos por formulario con peso cero; `visible_requirement` queda separado y
solo podrá poblarse desde texto o símbolos explicados visiblemente.

## D y E - Aceptación y marketing

Un checkbox puede representar términos, privacidad, marketing u otra declaración.
`Acepto` sin objeto es ambiguo y la ausencia de checkbox no es una brecha. PRV-104 se
mantiene intacto; una futura separación entre información de privacidad y elección
específica requerirá una decisión y versión de framework propias.

Marketing separado solo sería aplicable cuando coexistan una finalidad principal
concreta no promocional y una opción inequívocamente promocional. Un formulario dedicado
al newsletter no necesita otro checkbox por esta regla. La evaluación se posterga hasta
conservar estados técnicos del checkbox y calibrar casos reales.

## F y G - Señales de mayor riesgo y menores

Nombres como `salud`, `cuenta`, `alumno` o `edad` son ambiguos. Una evolución futura
podría emitir triggers contextuales de peso cero ante etiquetas explícitas o
combinaciones fuertes, sin usar categorías jurídicas ni afirmar edad, autorización o
ilegalidad. W2.2b no los implementará.

## H - Envío seguro del formulario

### Definición propuesta

- `type = conditional_evaluation`
- `dependency = PRV-101`
- aplicabilidad: solo cuando PRV-101 = `detected`
- automatización: sí
- riesgo de falso positivo: bajo
- impacto sugerido: **medio**

Se recomienda impacto medio porque PRV-501 ya evalúa el transporte general del sitio
con impacto `muy_alto`. H aporta precisión sobre cada punto de recopilación y su
`action`, pero un impacto alto duplicaría desproporcionadamente el fenómeno de una
página HTTP. El `action` HTTP específico sigue siendo un hallazgo relevante aunque el
resto del sitio cumpla PRV-501. Los pesos se decidirán en W2.2b sin modificar ahora
`scoring.json`.

### Resultados y consolidación

- `detected`: **todos** los formularios personales evaluables se cargan desde una página
  HTTPS y envían a un `action` HTTPS;
- `not_detected`: existe al menos un formulario personal cuya página es HTTP o cuyo
  `action` es HTTP;
- `not_evaluable`: existe evidencia insuficiente o un esquema no HTTP(S), y no existe ya
  un caso inseguro concluyente;
- `not_applicable`: PRV-101 = `not_detected`.

Una acción relativa se evalúa después de su resolución absoluta. Con varios formularios,
un caso HTTP concluyente prevalece sobre casos seguros o desconocidos. Sin casos HTTP,
cualquier caso desconocido impide afirmar que todos son seguros y produce
`not_evaluable`; solo si todos son evaluables y seguros resulta `detected`. El control
no afirma TLS futuro del receptor, cifrado en reposo, seguridad del backend, CSRF ni
tratamiento posterior. `GET` puede conservarse como contexto técnico, pero no cambia por
sí solo el resultado de transporte.

## I - Destino externo observable

W2.2b puede derivar `source hostname` y `action hostname` de las URLs existentes. Si son
distintos, `destination_external_observed = true` y la evidencia dirá: “El formulario
envía datos a un hostname distinto del sitio revisado”. Si son iguales, será `false`.

La primera versión compara hostnames normalizados literalmente. Por ello
`empresa.cl` y `forms.empresa.cl` son distintos y la señal **no** afirma que sean
organizaciones diferentes. No requiere Public Suffix List. Una futura evolución podrá
agrupar dominios relacionados. No se infiere cesión, encargado, proveedor, transferencia
o incumplimiento, y nunca se navega al `action` para clasificarlo.

## Evidence Contract mínimo

| Campo | ¿Existe hoy? | ¿Se necesita W2.2b? | Motivo |
|---|---|---|---|
| `source_url` | sí | H, A, C, I | Origen y trazabilidad por formulario |
| `action` | sí, absoluto | H, I | Esquema de envío y hostname de destino |
| `method` | sí | contexto opcional | No decide H; permite describir GET/POST |
| `FieldEvidence.required` | sí | C | Observación técnica, no visible |
| `CheckboxEvidence.required` | no | futuro E | Distinguir una restricción HTML promocional |
| `CheckboxEvidence.checked` | no | futuro E | Conocer estado inicial estático |
| `CheckboxEvidence.disabled` | no | futuro E | Evitar interpretar opciones no operables |
| `heading` | no | A | Señal de finalidad asociada |
| `legend` | no | A | Contexto semántico del formulario/fieldset |
| `introductory_text` | no | A | Frase de finalidad separada y acotada |
| `submit_text` | no | A | Acción/resultado explícito, por ejemplo “Reservar” |
| `visible_requirement` | no | C, opcional | Separar indicación visible de atributo HTML |
| categorías de campo | parcial, derivadas en adapter | C/contexto; futuro B/F/G | Inventario minimizado sin inferir necesidad |
| `source hostname` | no, derivable | I | Comparación objetiva del origen |
| `action hostname` | no, derivable | I | Comparación objetiva del destino |

**Necesario para H:** no requiere campos nuevos; necesita usar `source_url` y `action`
por cada formulario personal y conservar consolidación trazable.

**Necesario para A/C/I:** A requiere `heading`, `legend`, `introductory_text` y
`submit_text`. C puede empezar con `FieldEvidence.required`; `visible_requirement` es
opcional y nunca se deriva de `required`. I deriva hostnames y no amplía el contrato.

**Futuro E/F/G:** estados del checkbox corresponden a E. Categorías semánticas y
benchmarks corresponden a F/G. No deben incorporarse anticipadamente a W2.2b.

## Plan sintético de casos

No se implementan tests en W2.2a; estos casos definen los fixtures de W2.2b.

### H - Envío seguro

| Caso | Resultado esperado |
|---|---|
| Página HTTPS + acción relativa resuelta a HTTPS | `detected` |
| Página HTTPS + acción absoluta HTTPS | `detected` |
| Página HTTPS + acción HTTP | `not_detected` |
| Página HTTP + acción HTTPS | `not_detected` |
| Varios formularios personales, uno HTTP | `not_detected` |
| Esquema inválido/incompleto, sin caso HTTP concluyente | `not_evaluable` |
| Sin formularios personales | `not_applicable` |

### A - Finalidad visible

| Caso | Evidencia interna / resultado |
|---|---|
| “Envíanos tus datos para solicitar una cotización” asociado | `concrete` / `detected` |
| “Completa el formulario para reservar una hora” asociado | `concrete` / `detected` |
| “Contacto” sin resultado o uso descrito | `generic` / `partial` |
| Botón “Enviar” aislado | `generic` / `partial` |
| Botón “Suscribirme al newsletter” | `concrete` / `detected` |
| Texto concreto en una sección no asociada | `none` / `not_detected` |
| Varios formularios en una página | clasificación independiente y consolidación trazable |

### I - Destino externo

| Caso | Contexto esperado |
|---|---|
| Mismo hostname | `destination_external_observed = false` |
| Hostname distinto | `destination_external_observed = true` |
| Subdominio distinto | `true`, sin inferir organización distinta |
| Acción relativa | `false` tras resolución al hostname de origen |
| Acción inexistente | usa la URL de origen absoluta actual; `false` |
| Acción inválida o no HTTP(S) | `not_evaluable`, sin inferencias |

## Plan de calibración real

El benchmark posterior usará sitios seleccionados y revisados manualmente, sin fijar
URLs en esta fase.

| Perfil | Fenómenos a buscar |
|---|---|
| E-commerce | cuenta/checkout, newsletter, marketing, muchos campos, varios formularios, acciones HTTPS/externas |
| Servicios profesionales | contacto simple, cotización, finalidad concreta o genérica, formulario externo |
| Educación | contacto, admisión/reserva, varios formularios, muchos campos, finalidad y acciones HTTPS |
| Salud | reserva/contacto, formulario externo, muchos campos, finalidad clara/genérica, transporte |
| SaaS | registro/demo, newsletter, marketing, formulario externo, varios formularios |
| Microempresa/simple | contacto mínimo, acción relativa, finalidad genérica, ausencia de formularios personales |

La calibración medirá falsos positivos y negativos por formulario para A, verificará
todas las combinaciones de esquema de H y confirmará que I describe hostnames sin
atribuir relaciones jurídicas u organizacionales.

## Orden de implementación

1. **W2.2b.1 - Envío seguro del formulario:** implementar H con evidencia actual,
   consolidación, catálogo, acciones y pruebas focalizadas.
2. **W2.2b.2 - Extensión mínima por formulario:** añadir solo la evidencia textual
   separada y acotada necesaria para A, preservando trazabilidad.
3. **W2.2b.3 - Finalidad visible:** implementar A como `context`, peso cero y dependencia
   PRV-101, con el mapeo definido.
4. **W2.2b.4 - Destino externo observable:** implementar I como comparación objetiva de
   hostname y contexto de peso cero, sin ampliar el contrato.
5. **W2.2b.5 - Required técnico:** implementar C como contexto solo si la presentación
   aporta valor comprobado; no bloquear H, A o I por esta señal.

No ampliar esta secuencia a marketing, menores o datos especialmente delicados.

## Versionado y producción

W2.2a mantiene `framework_version = 0.1` y `scoring_version = 0.1` porque solo cambia
documentación. Producción, catálogo, score y resultados permanecen intactos.

W2.2b deberá incrementar `framework_version` al agregar controles o cambiar extracción
o adaptación de forma que pueda alterar resultados. `scoring_version` cambiará solo si
cambian pesos, factores, exclusiones, rangos o fórmula. Asignar impacto sugerido no
modifica por sí mismo ninguna versión mientras siga siendo diseño documental.

## Fuera de alcance

Este diseño no comprueba JavaScript, contenido dinámico, requests que omiten `action`,
seguridad del receptor, uso posterior de datos, legitimación, necesidad, consentimiento
jurídicamente válido ni contratos con proveedores. Estas limitaciones no son hallazgos
adversos.
