# Privacy Web - Extractor semántico común

## Estado

Primera implementación aislada del contrato `declared_processing/v1`.

Esta pieza recibe **un texto público ya obtenido** junto con su URL y procedencia, y devuelve hechos estructurados según `docs/privacy-declared-processing-v1.md`.

No realiza crawling, no selecciona políticas, no ejecuta controles y no participa todavía en el diagnóstico público.

## Frontera

Entrada:

- URL pública;
- texto público;
- tipo documental;
- título opcional.

Salida:

- `schema_version=declared_processing/v1`;
- records con los ocho tipos de hechos V1;
- evidencia literal y URL para cada hecho.

La llamada usa `gpt-5.6-sol`, Structured Outputs estricto y `store=false`.

## Salvaguardas V1

- máximo de entrada explícito;
- máximo de records y hechos;
- solo `supported` y `ambiguous`;
- evidencia debe existir literalmente en el texto recibido;
- URL, tipo documental y título devueltos deben coincidir con la entrada;
- una ausencia se representa con una colección vacía;
- no se aceptan conclusiones de cumplimiento, score ni estados PRV en el contrato.

## Integración

La implementación permanece desacoplada de PRV-202 y de los controles existentes.

El siguiente gate es QA independiente del extractor con un holdout nuevo. Los seis sitios usados para validar el modelo de representación del contrato no deben reutilizarse como holdout de calidad.

Solo después de ese QA debe decidirse si se conecta la salida a una normalización tecnológica y a PRV-202.
