# Validación post-deploy del Plan de corrección

El acceso al Plan es una credencial por posesión: quien posee el enlace puede abrir
el snapshot desde cualquier navegador o dispositivo, sin sesión ni cookies. Esta
validación debe realizarse contra un ambiente de prueba desplegado, nunca contra la
base de producción desde un entorno de desarrollo.

1. Preparar variables locales, sin escribir secretos en el repositorio:

   ```bash
   export API_BASE="https://<backend-de-prueba>"
   export WEB_BASE="https://<frontend-de-prueba>"
   export MININODE_API_KEY="<api-key-de-prueba>"
   ```

2. Crear un archivo temporal `request.json` con `site_url` y un `plan` compatible
   con PLAN-001. Para QA puede copiarse el objeto de
   `frontend/privacy/plan-demo/fixture.json` dentro de la propiedad `plan`.

3. Crear el Plan y conservar la respuesta solo durante la prueba:

   ```bash
   curl --fail-with-body -sS -X POST "$API_BASE/privacy/correction-plans" \
     -H "Content-Type: application/json" \
     -H "X-Api-Key: $MININODE_API_KEY" \
     --data-binary @request.json > response.json
   ACCESS_TOKEN="$(python -c 'import json; print(json.load(open("response.json"))["access_token"])')"
   ```

4. Con una `DATABASE_URL` exclusiva del ambiente de prueba, comprobar mediante
   `psql` que la fila contiene `site_url`, `token_hash`, `plan_snapshot`, versiones
   y score, y que el token original no aparece en ninguna columna:

   ```bash
   TOKEN_HASH="$(python -c 'import hashlib, os; print(hashlib.sha256(os.environ["ACCESS_TOKEN"].encode()).hexdigest())')"
   ```

   ```sql
   SELECT site_url, token_hash, plan_version, actions_version, initial_score,
          jsonb_typeof(plan_snapshot) AS snapshot_type,
          token_hash = '<TOKEN_HASH_CALCULADO>' AS hash_matches,
          position('<TOKEN_DE_LA_PRUEBA>' in row_to_json(correction_plan)::text) AS raw_token_position
   FROM privacy.correction_plan
   ORDER BY created_at DESC
   LIMIT 1;
   ```

   `hash_matches` debe ser verdadero y `raw_token_position` debe ser cero. No
   guardar el token usado en scripts, historial compartido ni documentación.

5. Recuperar exactamente el mismo snapshot sin API key:

   ```bash
   curl --fail-with-body -sS "$WEB_BASE/api/privacy/correction-plans/$ACCESS_TOKEN"
   ```

6. Abrir `$WEB_BASE/privacy/plan/$ACCESS_TOKEN` en dos navegadores o dispositivos.
   Ambos deben mostrar el mismo sitio, score, cantidad, orden e instrucciones del
   snapshot. Finalmente eliminar `request.json`, `response.json` y las variables
   locales de la sesión.
