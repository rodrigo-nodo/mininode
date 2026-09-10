# Privacy Web - PRV-103 QA7 result

**Resultado formal: NEEDS FIX**

## Referencia independiente

El Reviewer adjudicó los 30 casos después de congelar el paquete ciego. Vio exclusivamente:

- `blind_id`;
- `heading`;
- `legend`;
- `introductory_text`;
- `submit_text`.

No recibió URL, hostname, baseline, salida shadow, campos del formulario ni información externa del sitio.

Distribución de referencia:

| Clase | Casos |
|---|---:|
| concrete | 7 |
| generic | 20 |
| unknown | 3 |
| none | 0 |
| **Total** | **30** |

## Comparación

| Métrica | Baseline | Shadow LLM |
|---|---:|---:|
| Exact accuracy | 63.3% (19/30) | **96.7% (29/30)** |
| Coverage | 56.7% (17/30) | **90.0% (27/30)** |
| Emitted precision | 94.1% (16/17) | **96.3% (26/27)** |
| Concrete precision | 0% (0/1) | **87.5% (7/8)** |
| Concrete recall | 0% (0/7) | **100% (7/7)** |
| False concrete | 1 | 1 |
| False adverse `none` | 0 | 0 |
| Invalid outputs | n/a | 0 |

## Qué ocurrió en los desacuerdos

Hubo 10 casos donde baseline y shadow discreparon.

En los 10:

- baseline había quedado en `unknown`;
- shadow emitió `generic` o `concrete`;
- la referencia independiente coincidió con shadow.

Por tanto, **10/10 desacuerdos fueron mejoras frente al baseline**.

El único error del shadow fue `QA7-019`:

- referencia independiente: `generic`;
- baseline: `concrete`;
- shadow: `concrete`.

El caso contenía contexto de ayuda/contacto general (`¿Tienes dudas o necesitas ayuda?` / `Escríbenos...`). El Reviewer lo clasificó como contacto genérico, sin propósito específico adicional.

Este error no fue introducido por el LLM: ya estaba presente en el baseline y el shadow coincidió con él. Sin embargo, bajo los gates congelados de QA7, cualquier falsa promoción/clasificación `concrete` impide PASS.

## Veredicto

**NEEDS FIX**, porque existe 1 falso `concrete` frente a la referencia independiente.

La conclusión importante es más específica que el veredicto agregado:

- el shadow mejora materialmente cobertura y exactitud;
- resuelve correctamente los 10 casos donde el baseline abstuvo (`unknown`);
- no apareció ningún desacuerdo `generic -> concrete` ni `concrete -> generic` entre baseline y shadow;
- el único error observado es un borde compartido por baseline y LLM: contacto/ayuda general interpretado como propósito específico.

## Implicación para integración

QA7 **no justifica activar el LLM como autoridad general todavía**.

Sí aporta evidencia fuerte para estudiar una integración más conservadora tipo **fallback solo cuando baseline = `unknown`**. En esta muestra, ese camino habría usado el LLM únicamente en los 10 desacuerdos observados y los 10 coinciden con la referencia independiente.

Antes de activar ese fallback en producción debe definirse y validar un contrato específico para esa modalidad. El problema `QA7-019` debe tratarse aparte como defecto del baseline actual y como borde semántico que el LLM también debe aprender a abstener/clasificar como genérico cuando corresponda.

## Alcance y limitación

Los 30 sitios se recapturaron después del shadow porque la telemetría productiva, por diseño de privacidad, no retuvo los textos de los formularios. Los 30 volvieron a producir exactamente un HIGH deduplicado y las clases baseline reconstruidas coincidieron con las observadas en shadow, pero no se puede afirmar identidad byte-a-byte del texto histórico.

No se realizó tuning ni se modificó producción durante QA7.
