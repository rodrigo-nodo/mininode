-- PW-03: manual retirement of exactly three legacy Privacy Web tables.
-- Never add this file to migrations, Pre-deploy or unattended tasks.
-- Requires Render Shell PROD identity, PO's separate destructive approval,
-- a manual confirmation, and the public target/ack values set by the runner.
-- No private hashes or customer data are bound into this SQL.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

DO $target$
BEGIN
    IF current_setting('mininode.pw03_pr5_target_database', true)
       IS DISTINCT FROM current_database()
       OR current_setting('mininode.pw03_pr5_target_user', true)
       IS DISTINCT FROM current_user
       OR pg_is_in_recovery() THEN
        RAISE EXCEPTION 'PW03: database/user/primary confirmation missing or mismatched';
    END IF;
    IF current_setting('mininode.pw03_pr5_ack', true)
       IS DISTINCT FROM 'DELETE_2_PAID_1_PENDING_LEGACY_ORDERS' THEN
        RAISE EXCEPTION 'PW03: explicit destructive acknowledgement missing';
    END IF;
END
$target$;

-- Freeze all three legacy tables before checking and dropping anything.
LOCK TABLE privacy.correction_plan_check,
           privacy.correction_plan_order,
           privacy.correction_plan
IN ACCESS EXCLUSIVE MODE NOWAIT;

DO $inventory$
DECLARE
    total_plans bigint;
    active_plans bigint;
    total_orders bigint;
    paid_orders bigint;
    pending_orders bigint;
    total_checks bigint;
    paid_linked_plans bigint;
    linked_orders bigint;
    valid_reviews bigint;
BEGIN
    SELECT count(*), count(*) FILTER (WHERE status = 'active')
      INTO total_plans, active_plans
      FROM privacy.correction_plan;

    SELECT count(*),
           count(*) FILTER (
               WHERE status = 'paid'
                 AND paid_at IS NOT NULL
                 AND correction_plan_id IS NOT NULL
           ),
           count(*) FILTER (
               WHERE status = 'pending_payment'
                 AND paid_at IS NULL
                 AND correction_plan_id IS NULL
           )
      INTO total_orders, paid_orders, pending_orders
      FROM privacy.correction_plan_order;

    SELECT count(*) INTO total_checks FROM privacy.correction_plan_check;

    SELECT count(DISTINCT o.correction_plan_id)
      INTO paid_linked_plans
      FROM privacy.correction_plan_order o
      JOIN privacy.correction_plan p ON p.id = o.correction_plan_id
      JOIN privacy.diagnostic d ON d.id = o.diagnostic_id
     WHERE o.status = 'paid' AND o.paid_at IS NOT NULL AND p.status = 'active';

    SELECT count(*) INTO linked_orders
      FROM privacy.correction_plan_order o
      JOIN privacy.diagnostic d ON d.id = o.diagnostic_id;

    SELECT count(*) INTO valid_reviews
      FROM privacy.correction_plan_check c
      JOIN privacy.correction_plan_order o ON o.id = c.order_id
       AND o.status = 'paid' AND o.correction_plan_id = c.correction_plan_id
      JOIN privacy.diagnostic d1 ON d1.id = c.original_diagnostic_id
      JOIN privacy.diagnostic d2 ON d2.id = c.check_diagnostic_id;

    IF total_plans <> 2 OR active_plans <> 2
       OR total_orders <> 3 OR paid_orders <> 2 OR pending_orders <> 1
       OR total_checks <> 1 OR paid_linked_plans <> 2
       OR linked_orders <> 3 OR valid_reviews <> 1 THEN
        RAISE EXCEPTION 'PW03: legacy inventory/status/relations differ from approved 2/3/1; abort';
    END IF;
END
$inventory$;

-- No CASCADE. External dependencies prevent all drops and roll back the txn.
DROP TABLE privacy.correction_plan_check RESTRICT;
DROP TABLE privacy.correction_plan_order RESTRICT;
DROP TABLE privacy.correction_plan RESTRICT;
COMMIT;
