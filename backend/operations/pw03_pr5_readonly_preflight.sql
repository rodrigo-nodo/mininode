-- PW-03: manual, read-only inventory inspection of three legacy tables.
-- Do not emit IDs, customer email addresses, fingerprints or snapshots.
-- The caller inspects these manifests internally and prints counts only.
SELECT
    current_database() AS database_name,
    current_user AS database_user,
    pg_is_in_recovery() AS is_replica,
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
