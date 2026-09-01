# W2.2a — Diseño de controles de formularios

## Objetivo y límites

Este documento define la familia de controles de formularios que podrá implementarse
en W2.2b. Es una decisión de producto y de evidencia, no una implementación. No añade
controles, no cambia el catálogo ni el scoring y no modifica PRV-101 o PRV-104.

Privacy Web observa únicamente la interfaz pública obtenida como HTML estático. Una
señal describe lo observado, no demuestra cumplimiento legal, necesidad empresarial,
validez del consentimiento ni seguridad del backend. Cuando no pueda establecerse la
aplicabilidad, el resultado debe ser `not_applicable` o `not_evaluable`, nunca una
penalización por ausencia.

## Capacidad actual

El Evidence Contract v0.1 conserva, por formulario, URL de origen, `action` absoluto,
método, campos, checkboxes, 500 caracteres del contenedor cercano y enlaces de
privacidad. En campos no checkbox conserva nombre, tipo, etiqueta y atributo HTML
`required`; en checkboxes solo nombre y etiqueta.

La extracción actual tiene límites relevantes:

- `nearby_text` es el texto completo del `div`, `section` o `article` padre más cercano;
  puede mezclar título, controles, botones y otros formularios, y no identifica qué
  fragmento expresa una finalidad;
- no conserva texto de botones de envío, `legend`, encabezado asociado ni texto
  introductorio separado;
- `required` expresa una restricción HTML, no una indicación visible; tampoco refleja
  validación JavaScript;
- los checkboxes no conservan `required`, estado inicial ni asociación semántica;
- `action` permite analizar transporte y destino, pero no revela qué hará el receptor;
- el adapter agrega señales de todos los formularios personales y presenta evidencia
  visible de una sola URL, por lo que un control por formulario necesitará preservar la
  correspondencia entre observación y resultado.

PRV-104 reconoce un enlace/texto de privacidad o una etiqueta de checkbox con términos
de consentimiento. El campo interno `consent_required` replica hoy la existencia de esa
etiqueta: **no prueba que el checkbox sea obligatorio**. W2.2b no debe reutilizarlo con
esa interpretación.

## Clasificación de decisiones

- **Evaluación**: señal aplicable y suficientemente determinista para producir una
  conclusión puntuable.
- **Contexto**: observación útil, con peso cero, que activa o explica otras revisiones.
- **Postergar**: hipótesis valiosa, pero el contrato o la precisión actual no permiten
  un resultado conservador.
- **No implementar**: la conclusión exige conocer procesos o necesidad interna.

## Análisis de candidatos

### A. Finalidad o contexto del formulario

**Valor.** Alto como señal de transparencia: una persona debería poder entender qué
ocurrirá al enviar sus datos. Es observable solo cuando el texto está claramente
asociado al formulario.

**Evidencia suficiente.** Una frase cercana que combine una acción o resultado
concreto con el formulario, por ejemplo solicitar una cotización, reservar una hora,
inscribirse, postular, descargar un recurso o recibir respuesta a una consulta. También
pueden aportar un `legend`, encabezado o texto introductorio inequívocamente asociado.
`Enviar`, `Continuar`, `Formulario`, `Contacto`, `Registro` o una lista de campos no son
por sí solos finalidad suficiente. Un botón como `Suscribirme al newsletter` sí puede
ser concreto porque contiene acción y resultado.

**Decisión.** Diseñar un futuro control `conditional_evaluation`, dependiente de
PRV-101, pero implementarlo en W2.2b inicialmente como **contexto con peso cero**. Sus
estados serán `concrete`, `generic`, `not_observed` y `not_evaluable`; solo después de
un benchmark representativo podrá considerarse puntuable. La clasificación debe usar
un vocabulario acotado de pares acción/resultado y casos negativos, no similitud libre
ni una coincidencia aislada.

**Requisito previo.** Ampliar el contrato para separar `introductory_text`, `legend`,
`heading` y `submit_text`, mantenerlos acotados y asociarlos a un formulario estable.
No usar el `nearby_text` agregado como única prueba.

### B. Minimización visible

**Valor.** El contraste entre un newsletter que pide solo email y otro que además pide
RUT, dirección o fecha de nacimiento es útil para una revisión humana.

**Límite.** El HTML no permite conocer la finalidad completa, obligaciones aplicables,
prevención de fraude, logística ni otras necesidades reales. Incluso con una finalidad
visible, una matriz universal de campos “necesarios” produciría falsos positivos.

**Decisión.** **No implementar como control puntuable.** W2.2b puede exponer como
contexto un inventario minimizado de categorías y conteos por formulario, sin usar
adjetivos como “excesivo”, “innecesario” o “sensible”. Postergar cualquier heurística
de desproporción hasta contar con finalidad confiable, taxonomías por caso de uso y un
benchmark; aun entonces debe ser una alerta para revisión, no una conclusión.

### C. Campos obligatorios y opcionales

**Valor.** Los conteos técnicos ayudan a describir la fricción y a revisar si la
interfaz permite distinguir campos opcionales. No prueban minimización ni validez.

**Observabilidad.** `FieldEvidence.required` permite afirmar “tiene atributo HTML
`required`”, no “se muestra como obligatorio”. La indicación visible exige observar
texto o símbolos asociados y, para un asterisco, una leyenda visible que explique su
significado. La ausencia del atributo tampoco prueba que el campo sea opcional por la
posible validación JavaScript.

**Decisión.** **Contexto, peso cero.** Registrar por formulario conteos de controles con
`required` HTML y de indicaciones visibles reconocidas, siempre con nombres distintos.
No evaluar la proporción ni penalizar la falta de diferenciación en W2.2b.

**Requisito previo.** Añadir evidencia separada como `html_required` y
`visible_requirement` (`required`, `optional`, `unknown`), conservando el texto o señal
que justificó la clasificación. No derivar visibilidad del atributo técnico.

### D. Consentimiento y aceptación

Un checkbox puede referirse a privacidad, términos contractuales, promociones, una
declaración operativa o una preferencia; `Acepto` sin objeto no permite clasificarlos.
La ausencia de checkbox tampoco indica una brecha, pues no todo tratamiento requiere
consentimiento y existen otras formas de expresión cuando corresponde.

**Decisión.** No crear un control general “consentimiento presente”. Mantener PRV-104
sin cambios en esta fase y documentar para una evolución posterior su separación en:

1. información de privacidad asociada al formulario; y
2. mecanismo específico de elección, evaluado solo cuando una finalidad observable lo
   haga aplicable.

Esa separación requerirá migración explícita del framework porque cambiará la
interpretación observable de PRV-104. Un checkbox genérico, la palabra
`consentimiento` aislada o la mera ausencia de checkbox nunca deben activar una
conclusión negativa.

### E. Marketing separado

**Valor.** En un formulario con finalidad principal no promocional, una opción separada
como “Quiero recibir promociones” es observable y útil. Si esa opción es técnicamente
obligatoria, existe una señal fuerte de que la elección promocional no está separada.

**Aplicabilidad.** Solo aplica cuando coexisten (a) una finalidad principal concreta no
promocional y (b) un checkbox inequívocamente promocional. No aplica a un formulario
dedicado exclusivamente a newsletter ni cuando la finalidad principal es desconocida.
“Acepto”, “novedades” o “comunicaciones” sin contexto son ambiguos.

**Decisión.** Candidato a `conditional_evaluation`, pero **postergado fuera de W2.2b**
hasta mejorar el contrato y validar un benchmark. Un futuro control podría distinguir
`separate_optional`, `separate_required`, `ambiguous` y `not_applicable`. Solo
`separate_required` debería originar una observación adversa, y únicamente cuando la
obligatoriedad pueda probarse conservadoramente.

**Evidencia necesaria.** `CheckboxEvidence` debe incorporar al menos `required` HTML y
estado inicial `checked`, mantener etiqueta completa y formulario asociado. Conviene
preservar también `disabled`; no debe afirmarse que JavaScript permite o impide el envío.

### F. Datos especialmente delicados

**Valor.** Puede priorizar una revisión humana, pero los nombres de campo son ambiguos:
`salud` puede referirse al estado de un servicio, `cuenta` no necesariamente es
financiera y `huella` puede ser metafórica.

**Decisión.** No implementar una evaluación ni usar terminología jurídica como “dato
sensible”. Tras un benchmark, puede incorporarse un **trigger contextual de riesgo
elevado**, con peso cero, solo ante etiquetas visibles explícitas y combinaciones
conservadoras (por ejemplo, “número de cuenta bancaria”, “diagnóstico médico” o
“información de salud”). Una coincidencia en `name`, placeholder o texto general no
debe bastar. Biometría requiere lenguaje inequívoco sobre captura biométrica, no campos
comunes de imagen o firma.

### G. Menores

**Valor.** Expresiones como “fecha de nacimiento del menor” o la combinación “nombre
del alumno”/“nombre del apoderado” justifican atención especial. `Alumno`, `edad` o
`fecha de nacimiento` aislados no prueban que la persona sea menor.

**Decisión.** Futuro **contexto/trigger con peso cero**, no control puntuable. Exigir una
referencia explícita a niño, niña o menor, o una combinación de señales de estudiante y
apoderado dentro del mismo formulario. Describirlo como “formulario aparentemente
relacionado con menores”, sin inferir edad, representación, autorización ni legalidad.
Postergar W2.2b hasta tener evidencia por formulario y casos negativos suficientes.

### H. Envío seguro del formulario

**Valor.** Es el candidato más determinista. La URL de origen y el `action` absoluto
permiten observar el transporte previsto sin inferir seguridad del backend.

**Reglas propuestas.** Control `conditional_evaluation`, dependiente de PRV-101:

- `detected`: página de origen HTTPS y `action` HTTPS;
- `not_detected`: página de origen HTTP o `action` HTTP;
- `not_evaluable`: esquema no HTTP(S), URL inválida o evidencia incompleta;
- `not_applicable`: PRV-101 no detecta formularios personales.

Una acción relativa resuelta a HTTPS equivale a acción HTTPS. El dominio, subdominio o
carácter tercero no cambia el resultado. El control evalúa transporte observable, no
TLS del receptor al momento futuro del envío, cifrado en reposo, autenticación, CSRF,
logs ni controles internos. El método `GET` debe informarse como contexto separado
porque puede exponer valores en URL e historiales, pero no debe convertir por sí solo
“envío seguro” en una conclusión sobre el backend.

**Decisión.** **Implementar y puntuar en W2.2b**, evaluando cada formulario personal y
consolidando conservadoramente: cualquier formulario con transporte HTTP produce
`not_detected`; evidencia incompleta produce `not_evaluable` salvo que ya exista un
caso HTTP concluyente. Antes de fijar peso e impacto se debe validar coherencia con
PRV-501 y evitar doble penalización desproporcionada en `scoring.json`.

### I. Envío a terceros

**Observabilidad.** Puede compararse el hostname normalizado de `source_url` y `action`.
La comparación debe distinguir mismo host, subdominio relacionado y registrable domain
distinto; puertos y `www` no deben crear terceros artificiales. Sin Public Suffix List
o regla equivalente no es seguro decidir relaciones como `empresa.co.cl`.

**Límite.** Un destino distinto puede ser un proveedor legítimo y no revela el rol,
contrato, finalidad ni transferencias posteriores.

**Decisión.** **Contexto con peso cero**, denominado “destino externo observable”, no
“cesión” ni incumplimiento. Puede alimentar en el futuro una vista transversal de
terceros, pero no debe pertenecer a Cookies ni penalizarse automáticamente. W2.2b solo
debe incorporarlo si se añade una resolución robusta de dominio registrable; de lo
contrario se posterga. Debe mostrar los hostnames de origen y destino y nunca navegar
al `action` para comprobarlo.

## Cambio mínimo aprobado para W2.2b

1. Implementar el control condicional y puntuable de **envío seguro** descrito en H.
2. Ampliar el Evidence Contract solo con lo necesario para mantener evidencia por
   formulario y resultados trazables; la URL de origen y `action` actuales ya cubren la
   clasificación principal.
3. Incorporar la **finalidad visible** como control contextual de peso cero únicamente
   si antes se separan y acotan `introductory_text`, `legend`, `heading` y
   `submit_text`, con fixtures positivos, genéricos y ambiguos. Si esa ampliación no
   cabe en un cambio pequeño, se divide en una fase de Evidence Contract previa.
4. No implementar todavía minimización puntuable, consentimiento general, marketing
   separado, datos de riesgo elevado ni menores.
5. El destino externo puede añadirse como contexto solo con una clasificación de
   dominio registrable probada; no es requisito para cerrar W2.2b.

Los códigos, impacto y pesos definitivos se asignarán al actualizar el catálogo. No se
reutilizará un código por conveniencia ni se cambiarán PRV-101/PRV-104 silenciosamente.

## Requisitos de evidencia y pruebas

Toda implementación posterior debe:

- producir evidencia por formulario y seleccionar una URL pública trazable;
- diferenciar hechos HTML (`required`, `checked`, método, esquema) de interpretación
  visible;
- conservar valores minimizados y acotados, sin cuerpos completos ni valores escritos
  por usuarios;
- cubrir acciones ausentes, relativas, absolutas HTTPS/HTTP, esquemas no HTTP, página
  HTTP, múltiples formularios y destinos externos;
- cubrir textos concretos, genéricos y negativos en español e inglés para cualquier
  clasificador semántico añadido;
- probar `not_applicable` por dependencia, `not_evaluable` por evidencia insuficiente y
  consolidación de múltiples formularios;
- ejecutar el benchmark antes de volver puntuable una señal contextual;
- incrementar `framework_version` cuando la extracción, adaptación, criterio o conjunto
  de controles pueda cambiar el diagnóstico; cambiar `scoring_version` solo si cambian
  pesos, factores, exclusiones, rangos o fórmula.

## Riesgos explícitamente no cubiertos

Este diseño no comprueba validación JavaScript, contenido cargado dinámicamente,
requests realizados por scripts en lugar del `action`, seguridad del receptor, uso
posterior de datos, legitimación, necesidad, consentimiento jurídicamente válido ni
condiciones contractuales con proveedores. Esas ausencias deben presentarse como
límites del alcance, no como hallazgos adversos.
