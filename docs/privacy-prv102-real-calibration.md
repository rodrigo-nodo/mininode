# PRV-102 - calibración en sitios públicos reales (W2.2b.1-QA)

## Estado de la ejecución

**network calibration blocked**

La calibración no pudo ejecutarse porque el entorno no permitió conexiones de
salida directas desde `WebFetcher`. Los seis intentos fallaron durante
`home_fetch`, antes de obtener HTML, con `PrivacyInspectionError:
http_fetch_failed`, `ConnectError` y detalle técnico `network_unreachable`.

Por lo tanto, este documento **no presenta resultados inventados ni sustituye la
muestra real por fixtures sintéticos**. No es posible asignar `PASS`, `PASS WITH
OBSERVATIONS` o `NEEDS FIX` hasta repetir la ejecución en un entorno que permita
al pipeline actual acceder directamente a sitios públicos.

También se intentó preparar la ejecución temporal solicitada en GitHub Actions,
pero este entorno no dispone de un remote Git configurado ni de credenciales para
el repositorio privado. `gh auth status` indicó que no existe una sesión de GitHub
y `gh pr view 167 --repo rodrigo-nodo/mininode` no pudo autenticarse. Por ello no
fue posible subir el workflow temporal a la rama del PR #167 ni iniciar un run.
Esto es un bloqueo de acceso a GitHub desde el entorno de trabajo, no evidencia de
que los runners de GitHub Actions carezcan de conectividad a los seis sitios.

## Línea base

| Campo | Valor |
|---|---|
| Fecha de intento | 2026-09-01 |
| Main SHA | `457dee7da163f9541bc2e55e01f94f69f860e26a` |
| `framework_version` | `0.2` |
| `scoring_version` | `0.1` |
| `actions_version` | `2` |
| Código o catálogos modificados | No |

## Intento de GitHub Actions

| Campo | Resultado |
|---|---|
| GitHub Actions ejecutado | No |
| Motivo | Sin remote Git ni credenciales para actualizar el PR privado #167 |
| Workflow run URL | No disponible; no se pudo iniciar un run |
| Artifact esperado | `privacy-prv102-calibration` |
| Artifact obtenido | No; no hubo run |
| Sitios diagnosticados mediante Actions | 0 |
| Workflow temporal presente en el estado final | No |
| Runner temporal presente en el estado final | No |

No se incorporó un workflow o runner sin posibilidad de ejecutarlo: hacerlo no
habría aportado evidencia real y habría contradicho el requisito de que el estado
final del PR fuera únicamente documental. La ejecución en Actions sigue pendiente
en un entorno con permisos para actualizar la rama del PR.

## Metodología intentada

Se invocó localmente `diagnose_privacy_url(...)`, sin mocks y sin modificar el
pipeline, una vez para cada URL solicitada. La llamada usa el `WebFetcher` real y
falló en la lectura inicial de HOME. No se ejecutó ningún `action`, no se envió
ningún formulario y no se introdujeron datos personales.

La segunda lectura manual independiente no se realizó: sin HTML obtenido no
existían hechos visibles que pudieran etiquetarse con rigor. En particular, no se
usó `_form_transport(...)` ni se conservaron HTML, cuerpos, cookies, headers,
queries, credenciales o tokens.

## Casos previstos e intentos de red

Estas URLs constituyen intentos de cobertura sectorial, no casos calibrados ni
afirmaciones sobre los formularios que contienen.

| Caso | Sector | URL pública solicitada | Operación bloqueada | Resultado técnico |
|---|---|---|---|---|
| C01 | E-commerce | `https://www.patagonia.com/` | Lectura HOME del pipeline | `home_fetch`: `ConnectError` / `network_unreachable` |
| C02 | Servicios profesionales | `https://www.beneschlaw.com/` | Lectura HOME del pipeline | `home_fetch`: `ConnectError` / `network_unreachable` |
| C03 | Educación | `https://www.harvard.edu/` | Lectura HOME del pipeline | `home_fetch`: `ConnectError` / `network_unreachable` |
| C04 | Salud | `https://www.mayoclinic.org/` | Lectura HOME del pipeline | `home_fetch`: `ConnectError` / `network_unreachable` |
| C05 | SaaS/tecnología | `https://about.gitlab.com/` | Lectura HOME del pipeline | `home_fetch`: `ConnectError` / `network_unreachable` |
| C06 | Microempresa/sitio simple | `https://wickedgrounds.com/` | Lectura HOME del pipeline | `home_fetch`: `ConnectError` / `network_unreachable` |

## Matriz de resultados

No existe una matriz de resultados de producto/manual válida. En los seis casos
el bloqueo ocurrió antes de producir `site_url`, `pages_requested`,
`pages_analyzed`, `scope.limited`, PRV-101 o PRV-102. En consecuencia:

| Métrica | Resultado disponible |
|---|---:|
| Sitios intentados | 6 |
| Sitios efectivamente diagnosticados | 0 |
| Acuerdos producto/manual | 0/0 (no evaluable) |
| `detected` | 0 observados |
| `not_detected` | 0 observados |
| `not_evaluable` | 0 observados |
| `not_applicable` | 0 observados |
| Formularios personales HIGH | 0 observados |
| Formularios personales MEDIUM | 0 observados |
| Actions HTTPS externos | 0 observados |

Los ceros significan **ausencia de observaciones**, no resultados negativos ni
confirmación de comportamiento.

## Discrepancias y riesgos prioritarios

No fue posible comparar producto y etiqueta manual. Por ello no se clasifican
discrepancias A–H ni se infieren defectos de PRV-101 o PRV-102.

| Riesgo | Resultado |
|---|---|
| False positive promotions | No medible |
| False adverse | No medible |
| Penalización causada solo por MEDIUM | No medible |
| Action HTTPS externo penalizado | No medible |
| Consolidación de varios formularios | No medible |

El bloqueo pertenece al entorno de ejecución y no constituye por sí solo una
discrepancia `G. technical_limitation` de un sitio diagnosticado, porque ninguna
inspección llegó a comenzar.

## Minimización de evidencia

La comprobación solicitada sobre la evidencia pública de PRV-102 es **no
evaluable (0/6)**: no se produjo evidencia pública. Los registros conservados en
este documento contienen únicamente URL solicitada y categoría técnica del fallo;
no contienen actions, queries, credenciales, tokens, IP literales, HTML, bodies,
cookies ni headers privados.

## Descubrimiento adaptativo

No hubo expansión adaptativa. Los fallos ocurrieron en HOME, antes de descubrir o
clasificar enlaces candidatos y antes de poder registrar páginas solicitadas o
analizadas. Por tanto, no puede concluirse si el pipeline habría alcanzado páginas
de contacto, reserva, cotización o demo.

## Conclusión

**Resultado: network calibration blocked (sin clasificación de calibración).**

La muestra no permite aplicar el criterio de aprobación ni afirmar que PRV-102
esté calibrado. Tampoco aporta evidencia de un error de score: simplemente no hubo
diagnósticos. Producción, API, frontend, base de datos, controles, scoring, actions
y versiones permanecen sin cambios.

El bloqueo confirmado de red corresponde al entorno Codex. GitHub Actions no fue
ejecutado por falta de acceso autenticado al PR, por lo que no se atribuye un
bloqueo de red a Actions y no existe run URL ni artifact que reportar.

## Recomendación

Repetir exactamente la calibración documental sobre el mismo SHA en un entorno
con salida directa a Internet compatible con `WebFetcher`. Solo después de obtener
los seis diagnósticos se debe:

1. realizar la revisión manual independiente de los formularios obtenidos;
2. completar la matriz producto/manual y la tabla sanitizada por formulario;
3. verificar minimización en 6/6 y descubrimiento adaptativo;
4. contar promociones falsas, resultados adversos, MEDIUM y actions HTTPS
   externos; y
5. asignar `PASS`, `PASS WITH OBSERVATIONS` o `NEEDS FIX`.

No se recomienda cambiar reglas a partir de este intento bloqueado. Cualquier
corrección futura debe realizarse en un PR posterior y revisar el cambio de
`framework_version` de `0.2` a `0.3` si puede alterar resultados de PRV-102.
