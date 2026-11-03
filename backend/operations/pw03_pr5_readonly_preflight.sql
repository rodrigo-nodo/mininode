-- PW-03: read-only, operator-reviewed preflight.
-- Execute on the Render-selected Postgres resource BEFORE seeking destructive approval.
-- No secrets or customer email values are returned. Store IDs/manifests in private evidence.
-- Fingerprints must be reviewed outside the execution session and remain unchanged.
-- TimeZone must be UTC or Etc/UTC (the destructive script fixes it to UTC).
SELECT
    current_database() AS database_name,
    current_user AS database_user,
    current_setting('TimeZone') AS timezone,
    CASE WHEN current_setting('TimeZone') IN ('UTC', 'Etc/UTC')
         THEN encode(sha256(convert_to((SELECT system_identifier::text FROM pg_control_system()), 'UTF8')), 'hex')
         ELSE NULL END AS cluster_fingerprint_sha256,
    CASE WHEN current_setting('TimeZone') IN ('UTC', 'Etc/UTC')
         THEN encode(sha256(convert_to(
        jsonb_build_object(
            'plans', COALESCE(
                (SELECT jsonb_agg(to_jsonb(p) ORDER BY p.id) FROM privacy.correction_plan p),
                '[]'::jsonb),
            'orders', COALESCE(
                (SELECT jsonb_agg(to_jsonb(o) ORDER BY o.id) FROM privacy.correction_plan_order o),
                '[]'::jsonb),
            'checks', COALESCE(
                (SELECT jsonb_agg(to_jsonb(c) ORDER BY c.id) FROM privacy.correction_plan_check c),
                '[]'::jsonb)
        )::text, 'UTF8')), 'hex')
         ELSE NULL END AS legacy_inventory_sha256,
    (SELECT COALESCE(jsonb_agg(
         jsonb_build_object('id', p.id, 'status', p.status) ORDER BY p.id), '[]'::jsonb)
     FROM privacy.correction_plan p) AS plans_manifest,
    (SELECT COALESCE(jsonb_agg(
         jsonb_build_object('id', o.id, 'status', o.status,
          'paid_at_present', o.paid_at IS NOT NULL,
          'correction_plan_id', o.correction_plan_id, 'diagnostic_id', o.diagnostic_id)
         ORDER BY o.id), '[]'::jsonb)
     FROM privacy.correction_plan_order o) AS orders_manifest,
    (SELECT COALESCE(jsonb_agg(
         jsonb_build_object('id', c.id, 'order_id', c.order_id,
          'correction_plan_id', c.correction_plan_id,
          'original_diagnostic_id', c.original_diagnostic_id,
          'check_diagnostic_id', c.check_diagnostic_id)
         ORDER BY c.id), '[]'::jsonb)
     FROM privacy.correction_plan_check c) AS checks_manifest;
