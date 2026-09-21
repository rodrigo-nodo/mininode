# Privacy Web - Matriz de cobertura legal observable

## Objetivo

Esta matriz relaciona la Ley N° 21.719 con las señales públicas que Privacy Web puede observar desde un sitio web y con los controles vigentes del producto.

**Privacy Web no mide ni acredita el porcentaje de cumplimiento legal de una organización.** Realiza un diagnóstico inicial de evidencia pública observable y su resultado no constituye una certificación legal ni una auditoría completa.

La regla central de interpretación es:

> **Privacy Web observa lo declarado y técnicamente visible. Privacy Data ayuda a entender la operación real.**

Fuente legal principal: Ley N° 21.719 y texto consolidado de la Ley N° 19.628, especialmente artículos 3, 10, 11, 12, 14 ter, 14 quáter, 14 quinquies, 14 sexies y 14 septies.

Referencia oficial: https://www.bcn.cl/leychile/navegar?i=1209272

La interpretación debe revisarse cuando la Agencia de Protección de Datos Personales publique instrucciones generales que concreten estándares, condiciones mínimas o medidas diferenciadas.

## Alcance de referencia

El catálogo canónico vigente de Privacy Web contiene **21 controles en 5 áreas**:

- Transparencia: PRV-001 a PRV-014.
- Formularios: PRV-101 a PRV-104.
- Cookies: PRV-201.
- Contacto: PRV-301.
- Seguridad: PRV-501.

La interfaz actual incorpora PRV-102 y PRV-103 mediante el framework de Formularios y presenta **21 puntos** revisados.

Estados usados en esta matriz:

- **Observado**: existe uno o más controles que observan directamente evidencia pública relacionada con la materia.
- **Parcialmente observable**: existe evidencia relacionada, pero el control no cubre toda la información exigida o no permite concluir su suficiencia jurídica.
- **Señal contextual**: aporta información útil, pero no debe interpretarse como verificación de la obligación.
- **Observable pendiente**: la materia es razonablemente observable en información pública, pero no existe hoy un control específico suficientemente validado.
- **Interno / no observable**: requiere conocer procesos, sistemas o evidencia interna; queda fuera de una conclusión de Privacy Web.

Estos estados describen **capacidad de observación del producto**, no cumplimiento o incumplimiento legal.

## Artículo 14 ter - información y transparencia pública

| Ley | Información que debe mantenerse disponible | Aplica cuando | Control Privacy Web | Observabilidad | Limitación / pendiente |
|---|---|---|---|---|---|
| 14 ter a) | Política de tratamiento de datos personales | Siempre | PRV-001, PRV-002, PRV-003 | Observado | Los controles verifican presencia, acceso y atribución observable; no validan por sí solos suficiencia jurídica integral. |
| 14 ter a) | Fecha y versión de la política | Siempre | PRV-004 | Señal contextual | PRV-004 tiene peso cero y observa fecha o versión sin concluir cumplimiento. |
| 14 ter b) | Individualización del responsable | Siempre | PRV-005 | Observado | Se limita a identificación observable en la política seleccionada. |
| 14 ter b) | Representante legal | Cuando corresponda a la organización | PRV-005 | Parcialmente observable | El control actual no separa ni exige de forma completa la identificación del representante legal. |
| 14 ter b) | Encargado de prevención | Si existe | PRV-005 | Parcialmente observable | El control actual no identifica de forma específica esta figura. |
| 14 ter c) | Domicilio postal | Siempre | — | Observable pendiente | PRV-301 puede detectar una dirección como contacto general, pero hoy no existe un control específico que la evalúe como información exigida por 14 ter c). |
| 14 ter c) | Correo electrónico, formulario de contacto o medio tecnológico equivalente para solicitudes de titulares | Siempre | PRV-006 | Observado | Observa un canal asociado a privacidad, datos personales o derechos; no prueba funcionamiento, recepción ni gestión del procedimiento. |
| 14 ter c) | Contacto general del negocio | Contextual | PRV-301 | Señal contextual | Complementa la observación del sitio, pero no sustituye un canal específico para solicitudes de titulares. |
| 14 ter d) | Categorías, clases o tipos de datos tratados | Siempre | PRV-007 | Observado | Observa la declaración pública; no contrasta con bases de datos internas. |
| 14 ter d) | Universo de personas comprendidas en las bases de datos | Siempre | — | Observable pendiente | Crear o extender un control solo cuando exista evidencia pública suficiente y una regla confiable. |
| 14 ter d) | Destinatarios previstos | Cuando existan comunicaciones o cesiones previstas | PRV-010 | Observado | Observa declaraciones públicas; no verifica comunicaciones reales. |
| 14 ter d) | Finalidades del tratamiento | Siempre | PRV-008 | Observado | Observa finalidades declaradas en la política seleccionada. |
| 14 ter d) | Base de legitimidad | Siempre | PRV-009 | Señal contextual | Peso cero; no evalúa corrección jurídica ni aplicabilidad de la base declarada. |
| 14 ter d) | Intereses legítimos específicos | Cuando el tratamiento se base en interés legítimo | PRV-009 | Parcialmente observable | El control reconoce bases o fundamentos, pero no cubre de forma específica y completa la descripción del interés legítimo. |
| 14 ter e) | Política y medidas de seguridad adoptadas para proteger las bases de datos | Siempre | — | Observable pendiente | PRV-501 observa HTTPS/TLS, pero eso no equivale a observar la información pública exigida por 14 ter e). Debe diseñarse un control documental separado si la evidencia permite hacerlo de forma confiable. |
| 14 ter f) | Derechos de acceso, rectificación, supresión, oposición y portabilidad | Siempre | PRV-011 | Observado | Observa información pública sobre derechos; no verifica su ejecución interna. |
| 14 ter g) | Derecho a recurrir ante la Agencia en caso de rechazo o falta de respuesta oportuna | Siempre | PRV-013 | Parcialmente observable | PRV-013 detecta la posibilidad de reclamar o recurrir ante la Agencia o autoridad competente, pero hoy no exige de forma completa el contexto de rechazo o falta de respuesta oportuna. |
| 14 ter h) | Transferencias a tercer país u organización internacional y nivel de protección o garantías | Cuando existan transferencias internacionales | — | Observable pendiente | Materia expresamente prevista por la ley y potencialmente observable en la política. |
| 14 ter i) | Período de conservación | Siempre | PRV-012 | Observado | Observacional; no valora si el plazo o criterio es jurídicamente adecuado ni si se cumple en la práctica. |
| 14 ter j) | Fuente de los datos y si provienen de fuentes de acceso público | Cuando corresponda | — | Observable pendiente | Materia expresamente prevista por la ley y potencialmente observable en la política. |
| 14 ter k) | Derecho a retirar el consentimiento | Cuando el tratamiento se base en consentimiento | PRV-014 | Observado cuando aplica | Control condicional: solo aplica cuando la política declara claramente tratamiento basado en consentimiento. |
| 14 ter l) | Decisiones automatizadas y perfiles; lógica y consecuencias previstas | Cuando existan decisiones automatizadas o elaboración de perfiles | — | Observable pendiente | Requiere una señal pública suficientemente explícita y una evaluación semántica confiable. |

## Artículo 3 - calidad de la transparencia

El principio de transparencia e información exige que la información necesaria para el ejercicio de derechos esté permanentemente accesible y disponible de manera precisa, clara, inequívoca y gratuita.

Privacy Web puede observar parcialmente esta dimensión, pero no debe inferir calidad jurídica completa a partir de señales superficiales.

| Materia | Relación con Privacy Web | Estado actual |
|---|---|---|
| Accesibilidad pública | PRV-001, PRV-002 y controles documentales aportan evidencia directa | Parcialmente observable |
| Gratuidad de acceso | Normalmente puede observarse si el contenido público requiere pago o una barrera equivalente | No existe control específico |
| Precisión | Requiere interpretación semántica y contraste contextual | Observable pendiente |
| Claridad | Requiere interpretación semántica suficientemente validada | Observable pendiente |
| Carácter inequívoco | Requiere interpretación semántica suficientemente validada | Observable pendiente |

**Decisión actual:** no crear controles semánticos independientes para cerrar estas brechas. Deben esperar o reutilizar la arquitectura común de extracción semántica definida en `docs/privacy.md`.

## Otras obligaciones con señales web observables

| Ley / materia | Relación con Privacy Web | Aplica cuando | Control actual | Observabilidad | Frontera |
|---|---|---|---|---|---|
| Art. 10 - mecanismos sencillos para ejercer derechos | Un sitio puede publicar un canal o herramienta para solicitudes | Siempre | PRV-006 | Parcialmente observable | La existencia visible del canal no prueba que sea expedito, eficaz ni que opere correctamente. |
| Art. 11 - procedimiento ante el responsable | Puede observarse el medio publicado para presentar solicitudes | Siempre | PRV-006 | Parcialmente observable | Recepción, autenticación, acuse de recibo, plazos, respuesta y respaldos son procesos internos y no se verifican desde Web. |
| Art. 12 - consentimiento | Formularios pueden mostrar información o mecanismos de consentimiento | Cuando el tratamiento se base en consentimiento | PRV-104, PRV-014 | Señal contextual / parcialmente observable | La señal visible no demuestra que el consentimiento sea jurídicamente válido, libre, informado, específico ni correctamente registrado. |
| Art. 14 quáter - protección desde el diseño y por defecto | Algunas configuraciones públicas pueden aportar indicios | Cuando exista tratamiento de datos | PRV-101, PRV-103, PRV-104 | Señal contextual | La obligación es principalmente técnica y organizativa interna; Privacy Web no debe concluir cumplimiento. |
| Art. 14 quinquies - seguridad | HTTPS y transporte seguro son señales públicas limitadas | Siempre | PRV-102, PRV-501 | Señal contextual / parcialmente observable | Confidencialidad, integridad, disponibilidad, resiliencia, recuperación y evaluación de medidas no pueden acreditarse mediante HTTPS. |
| Art. 14 sexies - vulneraciones de seguridad | Un sitio podría publicar información relacionada con incidentes | Cuando exista una vulneración reportable | — | Interno / no observable | Detección, registro, evaluación y reporte de incidentes son capacidades internas. Una publicación eventual no permite verificar el proceso. |
| Transparencia sobre tecnologías que recopilan información | Cookies observadas pueden revelar puntos que conviene contrastar con la información pública | Cuando se observen cookies o tecnologías equivalentes | PRV-201 | Señal contextual | Observar una cookie no determina por sí mismo una obligación incumplida ni exige automáticamente un banner. |

## Controles públicos actuales - trazabilidad

| Control | Área | Relación legal principal | Estado en esta matriz |
|---|---|---|---|
| PRV-001 Política de privacidad visible | Transparencia | 14 ter a), art. 3 | Observado |
| PRV-002 Política de privacidad accesible | Transparencia | 14 ter a), art. 3 | Observado / parcialmente observable |
| PRV-003 Política propia del responsable | Transparencia | 14 ter a) | Observado |
| PRV-004 Fecha o versión de la política | Transparencia | 14 ter a) | Señal contextual |
| PRV-005 Identificación del responsable | Transparencia | 14 ter b) | Observado / parcialmente observable |
| PRV-006 Canal para ejercer derechos | Transparencia | 14 ter c), arts. 10 y 11 | Observado / parcialmente observable |
| PRV-007 Categorías de datos tratados | Transparencia | 14 ter d) | Observado |
| PRV-008 Finalidades del tratamiento | Transparencia | 14 ter d) | Observado |
| PRV-009 Base declarada del tratamiento | Transparencia | 14 ter d) | Señal contextual / parcialmente observable |
| PRV-010 Destinatarios o terceros | Transparencia | 14 ter d) | Observado |
| PRV-011 Derechos del titular | Transparencia | 14 ter f) | Observado |
| PRV-012 Conservación de datos | Transparencia | 14 ter i) | Observado |
| PRV-013 Reclamo ante la Agencia | Transparencia | 14 ter g) | Parcialmente observable |
| PRV-014 Retiro del consentimiento | Transparencia | 14 ter k), art. 12 | Observado cuando aplica |
| PRV-101 Formularios que recopilan datos personales | Formularios | 14 quáter / contexto de recolección | Señal contextual |
| PRV-102 Envío seguro del formulario | Formularios | 14 quinquies / seguridad de transporte | Parcialmente observable |
| PRV-103 Finalidad visible del formulario | Formularios | art. 3 / transparencia en punto de recolección | Señal contextual |
| PRV-104 Información de privacidad asociada al formulario | Formularios | art. 12 / transparencia | Señal contextual / parcialmente observable |
| PRV-201 Cookies observadas | Cookies | transparencia / contexto técnico | Señal contextual |
| PRV-301 Canal de contacto visible | Contacto | contexto de contacto | Señal contextual |
| PRV-501 Uso de HTTPS | Seguridad visible | 14 quinquies / seguridad de transporte | Parcialmente observable |

## Frontera de producto - Privacy Web vs Privacy Data

Privacy Web y Privacy Data son productos separados. Pueden complementarse, pero no deben duplicar responsabilidades.

| Privacy Web observa | Privacy Data ayuda a entender |
|---|---|
| ¿La política declara categorías de datos? | ¿Qué datos maneja realmente el negocio? |
| ¿Declara finalidades? | ¿Para qué se utilizan realmente? |
| ¿Declara destinatarios o terceros? | ¿Con qué terceros se comparten realmente y bajo qué relación? |
| ¿Declara conservación? | ¿Cuánto tiempo se conservan realmente y cómo se elimina? |
| ¿Declara medidas de seguridad? | ¿Qué medidas existen realmente y cómo se aplican? |
| ¿Existe un canal para derechos? | ¿Cómo se reciben, gestionan y responden las solicitudes? |
| ¿Declara transferencias internacionales? | ¿Qué transferencias internacionales existen realmente? |
| ¿Expone formularios, cookies o señales técnicas? | ¿Cómo se conectan esas señales con los procesos, sistemas y datos internos? |

Regla:

> **Una declaración pública puede ser evidencia para Privacy Web. La existencia y efectividad real del proceso pertenece a Privacy Data o a una revisión interna.**

## Fuera de alcance de Privacy Web

Privacy Web no debe intentar concluir mediante inspección pública sobre:

- inventario real y completo de datos personales;
- funcionamiento efectivo del procedimiento de derechos;
- autenticación de titulares;
- cumplimiento de plazos de respuesta;
- respaldo de respuestas a titulares;
- accesos y permisos internos;
- conservación y eliminación real de datos;
- efectividad de medidas de seguridad internas;
- gestión, registro y reporte de incidentes;
- evaluaciones de impacto;
- contratos con encargados o terceros;
- modelo de prevención de infracciones;
- trazabilidad interna;
- evidencia almacenada del consentimiento;
- comunicaciones o transferencias reales de datos;
- adecuación jurídica integral de una base de legitimidad.

Estas materias pueden corresponder a Privacy Data, a herramientas futuras especializadas o a revisión jurídica/técnica adicional.

## Brechas públicas prioritarias

Las brechas observables se priorizan por valor legal, frecuencia esperada y posibilidad de evaluación confiable.

### P1 - candidatas principales

1. **Domicilio postal y canal del artículo 14 ter c)**: separar claramente el domicilio postal del contacto general y del canal específico para derechos.
2. **Universo o categorías de personas comprendidas en las bases de datos**: diseñar solo si puede reconocerse con evidencia documental suficientemente confiable.
3. **Fuente u origen de los datos**: información expresamente exigida y potencialmente observable en la política.
4. **Transferencias internacionales y garantías**: control condicional, solo cuando la política declare una transferencia internacional.

### P2 - requieren mayor diseño semántico o jurídico

5. **Política y medidas de seguridad declaradas**: separar esta obligación documental de PRV-501 y PRV-102, que solo observan seguridad técnica visible.
6. **Interés legítimo específico**: requiere identificar correctamente la base y luego el interés declarado, sin evaluar su suficiencia jurídica.

### P3 - condicional y probablemente menos frecuente en el segmento inicial

7. **Decisiones automatizadas y elaboración de perfiles**: evaluar solo cuando exista una señal pública suficientemente explícita.

Estas brechas son candidatas de producto, no una instrucción automática para crear siete controles. Antes de implementar cada una debe definirse:

1. si la materia es realmente observable desde Web;
2. cuándo aplica;
3. qué evidencia mínima es suficiente;
4. si puede evaluarse de forma determinista o mediante la capa semántica común;
5. qué falsos positivos o falsos negativos son aceptables;
6. si debe afectar score, ser informativa o quedar fuera del score.

## Tamaño de empresa

El artículo 14 septies establece diferenciación de estándares para los deberes de información del artículo 14 ter y de seguridad del artículo 14 quinquies. Deben considerarse, entre otros factores:

- tipo de datos;
- si el responsable es persona natural o jurídica;
- tamaño de la entidad o empresa según las categorías de la Ley N° 20.416;
- actividad;
- volumen, naturaleza y finalidades de los datos tratados.

La Agencia determinará mediante instrucción general los estándares o condiciones mínimas y las medidas diferenciadas.

**Decisión actual de producto:** Privacy Web no reduce ni endurece controles por tamaño de empresa mientras esos estándares diferenciados no estén suficientemente definidos para traducirlos en reglas de producto. El tamaño tampoco se interpreta como una exención general de las obligaciones de la Ley N° 21.719.

Cuando existan instrucciones suficientemente concretas, la matriz deberá incorporar la aplicabilidad diferenciada sin convertir el tamaño de empresa en una auto-declaración que permita eludir controles.

## Regla de uso

Esta matriz es la referencia para analizar la **cobertura legal observable** de Privacy Web.

No debe utilizarse para afirmar:

- que una organización cumple o incumple integralmente la Ley N° 21.719;
- que el Privacy Score equivale a un porcentaje de cumplimiento legal;
- que una señal pública acredita procesos o medidas internas;
- que la ausencia de una señal pública demuestra necesariamente que una práctica interna no existe;
- que una micro o pequeña empresa está exenta de obligaciones por su tamaño.

Cuando cambie la ley, se publiquen instrucciones generales de la Agencia o cambie el conjunto de controles de Privacy Web, esta matriz debe revisarse junto con `docs/privacy.md`, el catálogo canónico de controles y, cuando corresponda, las versiones del framework y scoring.
