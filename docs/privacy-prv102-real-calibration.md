# PRV-102 - calibración en sitios públicos reales (W2.2b.1-QA)

## Resultado

**PASS WITH OBSERVATIONS**

PRV-102 se validó sobre seis sitios públicos reales usando el pipeline productivo actual mediante GitHub Actions. Los seis casos finalmente utilizados pudieron diagnosticarse y el resultado de PRV-102 coincidió con la revisión manual independiente en 6/6.

No se observaron:

- false positive promotions;
- false adverse;
- penalizaciones causadas únicamente por formularios MEDIUM;
- filtraciones del `action` completo en la evidencia pública.

La calibración se clasifica como **PASS WITH OBSERVATIONS** porque la muestra real no incluyó:

- un formulario personal HIGH con transporte HTTP;
- un candidato personal MEDIUM;
- un `action` HTTPS hacia hostname externo.

Estos fenómenos continúan cubiertos por tests sintéticos, pero no fueron observados naturalmente en esta muestra real.

## Línea base

| Campo | Valor |
|---|---|
| Fecha | 2026-09-01 |
| Main SHA evaluado | `457dee7da163f9541bc2e55e01f94f69f860e26a` |
| `framework_version` | `0.2` |
| `scoring_version` | `0.1` |
| `actions_version` | `2` |
| Producción modificada durante calibración | No |
| Catálogos modificados | No |

## Ejecución

La primera ejecución local desde el entorno Codex quedó bloqueada por conectividad saliente (`network_unreachable`).

Luego se ejecutó la calibración mediante un workflow temporal de GitHub Actions. Los primeros sitios de e-commerce y salud seleccionados originalmente no fueron inspeccionables por respuestas HTTP del propio sitio, por lo que se reemplazaron conservando el sector:

- E-commerce: Patagonia y luego Bookshop fueron reemplazados por Beardbrand.
- Salud: Mayo Clinic fue reemplazado por NHS.

No se modificó ninguna regla de PRV-101 o PRV-102 después de observar los resultados.

Ejecuciones relevantes:

- Run inicial: https://github.com/rodrigo-nodo/mininode/actions/runs/33518106555
- Run con reemplazo de salud: https://github.com/rodrigo-nodo/mininode/actions/runs/33518320612
- Run final de seis casos diagnosticables: https://github.com/rodrigo-nodo/mininode/actions/runs/33518493862

Artifact final:

- nombre: `privacy-prv102-calibration`
- artifact id: `9804636915`
- retención temporal: 7 días

El workflow temporal fue eliminado después de documentar los resultados.

## Metodología

Para cada sitio se ejecutó el pipeline real:

`diagnose_privacy_url(...)`

sin mocks y sin modificar producción.

Se registró de forma sanitizada:

- URL solicitada y URL final;
- páginas solicitadas y analizadas;
- resultado/confianza de PRV-101;
- resultado/confianza de PRV-102;
- `framework_version`;
- `scoring_version`;
- evidencia mínima de formularios para revisión.

No se enviaron formularios ni se introdujeron datos personales.

Para la revisión manual se observaron únicamente hechos estructurados del formulario:

- campos visibles;
- esquema de la página;
- esquema del `action`;
- método;
- contexto suficiente para decidir si el formulario era razonablemente personal.

La etiqueta manual de PRV-102 se aplicó según la especificación aprobada y no se tomó del resultado productivo.

## Matriz de resultados

| Caso | Sector | Sitio final | Páginas analizadas | PRV-101 producto | PRV-102 producto | PRV-102 esperado manual | Acuerdo |
|---|---|---|---:|---|---|---|---|
| C01 | E-commerce | `beardbrand.com` | 2 | detected | detected | detected | Sí |
| C02 | Servicios profesionales | `beneschlaw.com` | 2 | detected | detected | detected | Sí |
| C03 | Educación | `harvard.edu` | 3 | not_detected | not_applicable | not_applicable | Sí |
| C04 | Salud | `nhs.uk` | 1 | not_detected | not_applicable | not_applicable | Sí |
| C05 | SaaS/tecnología | `about.gitlab.com` | 4 | not_detected | not_applicable | not_applicable | Sí |
| C06 | Microempresa/sitio simple | `wickedgrounds.com` | 2 | detected | detected | detected | Sí |

Resumen:

| Métrica | Resultado |
|---|---:|
| Sitios diagnosticados | 6/6 |
| Acuerdos producto/manual | 6/6 |
| PRV-102 detected | 3 |
| PRV-102 not_detected | 0 |
| PRV-102 not_evaluable | 0 |
| PRV-102 not_applicable | 3 |
| False positive promotions | 0 |
| False adverse | 0 |
| Casos MEDIUM observados | 0 |
| Action HTTPS externo observado | 0 |

## Revisión por caso

### C01 - E-commerce

Beardbrand expuso un formulario de email en HOME. La evidencia manual mostró un campo email y transporte HTTPS tanto en la página como en el destino declarado.

Esperado manual: `detected`.

Producto: `detected`.

No se observó discrepancia.

### C02 - Servicios profesionales

Benesch expuso varios formularios, incluyendo formularios de contacto con nombre, email, teléfono y mensaje. Todos los formularios personales relevantes observados usaron HTTPS en source y action.

También se observaron formularios de búsqueda. Aunque su clasificación como formulario personal puede discutirse de forma aislada, no altera el resultado PRV-102 de este caso porque existen además formularios personales claros y todos los transportes observados son HTTPS.

Esperado manual: `detected`.

Producto: `detected`.

No se observó discrepancia de score para PRV-102.

### C03 - Educación

Harvard no presentó formularios personales en las páginas inspeccionadas.

Esperado manual: `not_applicable`.

Producto: `not_applicable`.

### C04 - Salud

NHS presentó un formulario de búsqueda, pero no un formulario que razonablemente recopilara datos personales dentro del alcance observado.

Esperado manual: `not_applicable`.

Producto: `not_applicable`.

### C05 - SaaS/tecnología

GitLab permitió llegar a la página de contacto, pero los formularios estructurados observados no contenían campos personales utilizables por PRV-101.

Esperado manual: `not_applicable`.

Producto: `not_applicable`.

### C06 - Microempresa/sitio simple

Wicked Grounds permitió descubrir de forma adaptativa su página de contacto. Se observó un formulario con nombre, email y mensaje, con source HTTPS y action HTTPS.

Esperado manual: `detected`.

Producto: `detected`.

## PRV-101

No se observó un falso positivo de PRV-101 capaz de cambiar incorrectamente el resultado de PRV-102 en esta muestra.

Sí queda una observación útil en C02: campos de búsqueda de texto libre pueden ser clasificados como personales por la lógica actual. En este caso no produjo una decisión adversa ni una promoción incorrecta porque existían además formularios personales claros y todo el transporte observado era HTTPS.

No se recomienda ajustar PRV-101 a partir de este único caso.

## Formularios MEDIUM

No se observaron candidatos MEDIUM en los seis casos finales.

Por tanto, la regla:

`MEDIUM` por sí solo no puede producir `not_detected`

queda validada por tests sintéticos, pero no por evidencia real en esta muestra.

Esto es una limitación de cobertura del benchmark, no un fallo observado.

## Action HTTPS externo

No apareció de forma natural un formulario personal cuyo `action` HTTPS apuntara a un hostname externo.

El comportamiento esperado continúa cubierto por tests sintéticos:

HTTPS externo no debe ser penalizado solo por cambiar de hostname.

## Minimización

**PASS 6/6**

La salida productiva sanitizada de PRV-102 no expuso:

- `action` completo;
- query strings;
- credenciales;
- tokens;
- IP del destino;
- valores introducidos por usuarios.

La evidencia pública utilizada por PRV-102 conservó únicamente trazas de origen sanitizadas cuando correspondía.

## Descubrimiento adaptativo

No se observó un problema sistemático.

Casos relevantes:

- C02 analizó HOME y una página adicional de contacto.
- C03 analizó tres páginas.
- C05 analizó cuatro páginas y alcanzó la zona de contacto.
- C06 descubrió y analizó `/contact/`, donde estaba el formulario personal.

C06 confirma específicamente que un formulario ausente en HOME puede ser descubierto por la expansión adaptativa y luego evaluado por PRV-102.

## Discrepancias

No hubo discrepancias producto/manual de PRV-102 en los seis casos finales.

Por tanto:

| Tipo | Cantidad |
|---|---:|
| personal_form_detection con impacto PRV-102 | 0 |
| adaptive_page_discovery | 0 |
| source_scheme | 0 |
| action_resolution | 0 |
| transport_consolidation | 0 |
| confidence_handling | 0 |
| technical_limitation en muestra final | 0 |
| manual_label_uncertain | 0 |

Los sitios descartados por 403/404 corresponden a limitaciones de inspección del sitio y no forman parte de los seis casos finales calibrados.

## Conclusión

**PASS WITH OBSERVATIONS**

PRV-102 se comportó correctamente en los seis casos reales finalmente diagnosticados:

- 6/6 acuerdo producto/manual;
- 0 false positive promotions;
- 0 false adverse;
- 0 penalizaciones por MEDIUM;
- minimización PASS 6/6;
- sin evidencia de problema sistemático de descubrimiento adaptativo.

Las observaciones pendientes son de cobertura del benchmark: no aparecieron naturalmente un transporte HTTP inseguro, un candidato MEDIUM ni un action HTTPS externo.

No existe evidencia que justifique modificar PRV-102 en esta fase.

## Recomendación

Cerrar W2.2b.1-QA con **PASS WITH OBSERVATIONS** y mantener:

- `framework_version = 0.2`;
- `scoring_version = 0.1`;
- `actions_version = 2`.

No cambiar reglas a partir de esta muestra.

El siguiente paso puede avanzar a W2.2b.2, manteniendo como observaciones futuras:

- incorporar en una calibración posterior un caso real MEDIUM si aparece naturalmente;
- incorporar un action HTTPS externo si aparece naturalmente;
- continuar usando tests sintéticos para los casos HTTP inseguros, sin buscar ni explotar sitios vulnerables.
