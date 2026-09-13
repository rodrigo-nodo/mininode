# PRV-103 framework 0.9 — QA independiente final

## Etapa actual: Artifact A ciego

El QA se limita en este PR a la captura de Artifact A. El workflow manual `Privacy PRV-103 QA09 Artifact A` queda preparado para ejecutarse en GitHub Actions, donde existe salida HTTPS pública. No se inició Artifact B, adjudicación Gold, evaluación ni cálculo de métricas.

Este checkout no tiene remote ni autenticación de GitHub, por lo que no fue posible despachar `workflow_dispatch` ni obtener un identificador de run desde el runner de Codex. No se sustituyó ese run por una captura local: la salida HTTPS de este entorno está bloqueada y no produciría evidencia válida.

## Producto y pool congelados

| Campo | Valor |
|---|---|
| SHA productivo | `6fbe6f94887114f4a5459af861f1fcaa0c4b7bd7` |
| `framework_version` | `0.9` |
| `scoring_version` | `0.1` |
| PRV-103 | determinístico; no ejecutado en Artifact A |
| LLM/shadow | desactivado |
| Candidatos congelados | 99 |
| SHA-256 del pool | `33383fc229068633915d215404f0c9e0d368a1c7d2d968ad7047b97c1136b14a` |

El workflow falla antes de la captura si cambia el hash, el número de candidatos, su unicidad o cualquier archivo de producto protegido respecto del SHA congelado.

## Contrato de captura

La captura usa el Web Inspector actual exclusivamente mediante GET públicos, respeta robots y redirecciones normales, analiza HTML como datos inertes y no ejecuta JavaScript. Recorre los 99 candidatos en el orden congelado, conserva todos los formularios personales con confianza HIGH y los deduplica por hostname y los cuatro campos semánticos permitidos.

Artifact A contiene exclusivamente:

- `blind_id`;
- `heading`;
- `legend`;
- `introductory_text`;
- `submit_text`.

La identidad derivable del hostname se redacta de esos textos. Dominio, URL, estado de captura, campos personales y trazas quedan únicamente en `internal-manifest.json`, publicado como artifact separado y no entregado al reviewer.

Si la ejecución obtiene menos de 30 formularios HIGH elegibles, el resumen interno queda con `sufficient=false` y el comando termina con código 2. Los artifacts disponibles se publican para trazabilidad, pero el workflow queda fallido y el protocolo no puede avanzar.

## Estado de ejecución

| Campo | Estado |
|---|---|
| Workflow | `.github/workflows/privacy-prv103-qa09-artifact-a.yml` |
| Run de GitHub Actions | pendiente de `workflow_dispatch` externo |
| Sitios procesados | pendiente del run |
| Formularios HIGH elegibles | pendiente del run |
| Artifact A | pendiente del run |
| Manifest interno sellado | pendiente del run |

## Protección de independencia

El script de Artifact A no importa ni llama `run_privacy_diagnostic` o `_form_purpose_signal`. No produce predicciones PRV-103. No existe Gold ni Artifact B en esta etapa.

No se envían formularios ni solicitudes POST, no se inicia sesión, no se crean cuentas, no se introducen datos y no se eluden protecciones. Tampoco se modifican PRV-103, extractor, scoring, frontend, API, base de datos ni versiones.
