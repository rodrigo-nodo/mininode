# Privacy Web - Matriz de cobertura legal observable

## Objetivo

Esta matriz relaciona la Ley N° 21.719 con las señales públicas que Privacy Web puede observar desde un sitio web y con los controles públicos vigentes del producto.

**No mide ni acredita el porcentaje de cumplimiento legal de una organización.** Privacy Web realiza un diagnóstico inicial de señales públicas y su resultado no constituye una certificación legal ni una auditoría completa.

Fuente legal principal: Ley N° 21.719, especialmente artículos 10, 12, 14 ter, 14 quinquies y 14 septies. La interpretación debe revisarse cuando la Agencia de Protección de Datos Personales publique instrucciones generales que concreten estándares o condiciones mínimas.

## Alcance de referencia

La interfaz pública de Privacy Web presenta actualmente **19 controles en 5 áreas**:

- Transparencia: PRV-001 a PRV-014.
- Formularios: PRV-101 y PRV-104.
- Cookies: PRV-201.
- Contacto: PRV-301.
- Seguridad: PRV-501.

El catálogo backend contiene además PRV-102 y PRV-103. No forman parte de los 19 controles mostrados en el resumen público y, por tanto, esta matriz no los cuenta como cobertura pública vigente.

Estados usados:

- **Cubierto**: existe uno o más controles públicos que observan directamente la materia.
- **Parcial**: existe evidencia relacionada, pero el control no cubre toda la información exigida o no permite concluir su suficiencia jurídica.
- **Contextual**: aporta una señal útil, pero no debe interpretarse como verificación de la obligación.
- **Pendiente**: la materia es razonablemente observable en información pública, pero no existe hoy un control público específico.
- **No verificable desde Web**: requiere conocer procesos, sistemas o evidencia interna; queda fuera de una conclusión de Privacy Web.

## Artículo 14 ter - información y transparencia pública

| Ley | Información que debe mantenerse disponible | Control Privacy Web | Cobertura | Limitación / pendiente |
|---|---|---|---|---|
| 14 ter a) | Política de tratamiento de datos personales | PRV-001, PRV-002, PRV-003 | Cubierto | Los controles verifican presencia, acceso y atribución observable; no validan por sí solos suficiencia jurídica integral. |
| 14 ter a) | Fecha y versión de la política | PRV-004 | Contextual | PRV-004 tiene peso cero y observa fecha o versión sin concluir cumplimiento. |
| 14 ter b) | Individualización del responsable | PRV-005 | Cubierto | Se limita a identificación observable en la política seleccionada. |
| 14 ter b) | Representante legal y encargado de prevención, si existe | PRV-005 | Parcial | El control actual no separa ni exige de forma completa estas identificaciones. |
| 14 ter c) | Medio para recibir solicitudes de titulares | PRV-006, PRV-301 | Cubierto | PRV-006 observa el canal de derechos en la política; PRV-301 complementa con contacto general. No prueba que el canal funcione operativamente ni que las solicitudes sean gestionadas conforme a plazo. |
| 14 ter d) | Categorías, clases o tipos de datos tratados | PRV-007 | Cubierto | Observa la declaración pública; no contrasta con bases de datos internas. |
| 14 ter d) | Universo de personas comprendidas en las bases de datos | — | Pendiente | Crear o extender un control solo cuando exista evidencia pública suficiente y una regla confiable. |
| 14 ter d) | Destinatarios previstos | PRV-010 | Cubierto | Observa declaraciones públicas; no verifica comunicaciones reales. |
| 14 ter d) | Finalidades del tratamiento | PRV-008 | Cubierto | Observa finalidades declaradas en la política seleccionada. |
| 14 ter d) | Base de legitimidad | PRV-009 | Contextual | Peso cero; no evalúa corrección jurídica ni aplicabilidad de la base declarada. |
| 14 ter d) | Intereses legítimos específicos, cuando correspondan | PRV-009 | Parcial | El control reconoce bases/fundamentos, pero no cubre de forma específica y completa la descripción del interés legítimo. |
| 14 ter e) | Política y medidas de seguridad adoptadas para proteger las bases de datos | PRV-501 | Parcial | HTTPS es solo una señal técnica pública básica. No demuestra las medidas organizativas y técnicas internas exigidas por la ley. |
| 14 ter f) | Derechos de acceso, rectificación, supresión, oposición y portabilidad | PRV-011 | Cubierto | Observa información pública sobre derechos; no verifica su ejecución interna. |
| 14 ter g) | Derecho a recurrir ante la Agencia | PRV-013 | Cubierto | Observa la información publicada sobre reclamación o recurso. |
| 14 ter h) | Transferencias a tercer país u organización internacional y garantías, cuando correspondan | — | Pendiente | Materia pública expresamente prevista por la ley y potencialmente observable en la política. |
| 14 ter i) | Período de conservación | PRV-012 | Cubierto | Observacional; no valora si el plazo o criterio es jurídicamente adecuado. |
| 14 ter j) | Fuente de los datos y si provienen de fuentes de acceso público | — | Pendiente | Materia pública expresamente prevista por la ley y potencialmente observable en la política. |
| 14 ter k) | Derecho a retirar el consentimiento, cuando el tratamiento se base en consentimiento | PRV-014 | Cubierto | Control condicional: solo aplica cuando la política declara claramente tratamiento basado en consentimiento. |
| 14 ter l) | Decisiones automatizadas y perfiles; lógica y consecuencias previstas | — | Pendiente | Debe evaluarse solo cuando corresponda; requiere una señal pública suficientemente explícita. |

## Otras obligaciones con señales web observables

| Ley / materia | Relación con Privacy Web | Control actual | Cobertura | Frontera |
|---|---|---|---|---|
| Art. 10 - mecanismos sencillos para ejercer derechos | Un sitio puede publicar un canal o herramienta para solicitudes | PRV-006, PRV-301 | Parcial | La existencia visible del canal no prueba que sea expedito, eficaz ni que opere correctamente. |
| Art. 11 - procedimiento ante el responsable | Puede observarse el medio publicado para presentar solicitudes | PRV-006 | Parcial | Recepción, autenticación, plazos, respuesta y respaldos son procesos internos y no se verifican desde Web. |
| Art. 12 - consentimiento | Formularios pueden mostrar información o mecanismos de consentimiento | PRV-104, PRV-014 | Contextual / parcial | La señal visible no demuestra que el consentimiento sea jurídicamente válido, libre, informado, específico ni correctamente registrado. |
| Art. 14 quáter - protección desde el diseño y por defecto | Algunas configuraciones públicas pueden aportar indicios | PRV-101, PRV-104 | Contextual | La obligación es principalmente técnica y organizativa interna; Privacy Web no debe concluir cumplimiento. |
| Art. 14 quinquies - seguridad | HTTPS y transporte son señales públicas limitadas | PRV-501 | Parcial | Confidencialidad, integridad, disponibilidad, resiliencia, recuperación y evaluación de medidas no pueden acreditarse mediante HTTPS. |
| Transparencia sobre tecnologías que recopilan información | Cookies observadas pueden revelar puntos que conviene contrastar con la información pública | PRV-201 | Contextual | Observar una cookie no determina por sí mismo una obligación incumplida ni exige automáticamente un banner. |

## Controles públicos actuales - trazabilidad

| Control | Área | Relación legal principal | Estado en esta matriz |
|---|---|---|---|
| PRV-001 Política de privacidad visible | Transparencia | 14 ter a) | Cubierto |
| PRV-002 Política de privacidad accesible | Transparencia | 14 ter a) | Cubierto |
| PRV-003 Política atribuible al negocio | Transparencia | 14 ter a) | Cubierto |
| PRV-004 Fecha o versión de la política | Transparencia | 14 ter a) | Contextual |
| PRV-005 Identificación del responsable | Transparencia | 14 ter b) | Cubierto / parcial |
| PRV-006 Canal para ejercer derechos | Transparencia | 14 ter c), art. 10 | Cubierto / parcial |
| PRV-007 Categorías de datos tratados | Transparencia | 14 ter d) | Cubierto |
| PRV-008 Finalidades del tratamiento | Transparencia | 14 ter d) | Cubierto |
| PRV-009 Base declarada del tratamiento | Transparencia | 14 ter d) | Contextual / parcial |
| PRV-010 Destinatarios o terceros | Transparencia | 14 ter d) | Cubierto |
| PRV-011 Derechos de las personas | Transparencia | 14 ter f) | Cubierto |
| PRV-012 Conservación de datos | Transparencia | 14 ter i) | Cubierto |
| PRV-013 Reclamo ante la Agencia | Transparencia | 14 ter g) | Cubierto |
| PRV-014 Retiro del consentimiento | Transparencia | 14 ter k), art. 12 | Cubierto cuando aplica |
| PRV-101 Recopilación de datos personales | Formularios | 14 quáter / contexto de recolección | Contextual |
| PRV-104 Información o consentimiento en formularios | Formularios | art. 12 / transparencia | Contextual / parcial |
| PRV-201 Cookies observadas | Cookies | transparencia / contexto técnico | Contextual |
| PRV-301 Canal de contacto visible | Contacto | 14 ter c), art. 10 | Complementario |
| PRV-501 HTTPS activo | Seguridad | 14 quinquies | Parcial |

## Brechas públicas prioritarias

Las brechas directas actualmente identificadas respecto del artículo 14 ter son:

1. universo o categorías de personas comprendidas en las bases de datos;
2. representante legal y encargado de prevención, cuando corresponda, con cobertura más explícita;
3. política y medidas de seguridad declaradas, separando esta información de la señal técnica HTTPS;
4. interés legítimo específico, cuando corresponda;
5. transferencias internacionales y garantías, cuando correspondan;
6. fuente u origen de los datos;
7. decisiones automatizadas y elaboración de perfiles, cuando correspondan.

Estas brechas son candidatas de producto, no una instrucción automática para crear siete controles. Antes de implementar cada una debe definirse si la evidencia pública disponible permite una evaluación confiable, determinista o suficientemente validada.

## Tamaño de empresa

El artículo 14 septies establece diferenciación de estándares para los deberes de información del artículo 14 ter y de seguridad del artículo 14 quinquies. Deben considerarse, entre otros factores:

- tipo de datos;
- si el responsable es persona natural o jurídica;
- tamaño de la entidad o empresa según las categorías de la Ley N° 20.416;
- actividad;
- volumen, naturaleza y finalidades de los datos tratados.

La Agencia determinará mediante instrucción general los estándares o condiciones mínimas y las medidas diferenciadas.

**Decisión actual de producto:** Privacy Web no reduce ni endurece controles por tamaño de empresa mientras esos estándares diferenciados no estén suficientemente definidos para traducirlos en reglas de producto. El tamaño tampoco se interpreta como una exención general de las obligaciones de la Ley N° 21.719.

## Regla de uso

Esta matriz es la referencia para analizar la **cobertura legal observable** de Privacy Web.

No debe utilizarse para afirmar:

- que una organización cumple o incumple integralmente la Ley N° 21.719;
- que el Privacy Score equivale a un porcentaje de cumplimiento legal;
- que una señal pública acredita procesos o medidas internas;
- que una micro o pequeña empresa está exenta de obligaciones por su tamaño.

Cuando cambie la ley, se publiquen instrucciones generales de la Agencia o cambie el conjunto de controles públicos de Privacy Web, esta matriz debe revisarse junto con `docs/privacy.md`, el catálogo de controles y, cuando corresponda, las versiones del framework y scoring.
