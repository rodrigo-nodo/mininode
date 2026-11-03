-- PW-03 PR 5: manually operated, destructive Privacy Web legacy retirement.
-- NEVER register this file in MIGRATION_APPROVED_FILES or run it as Render Pre-deploy.
-- Requires separate authorization, an operator-reviewed inventory and recovery decision.
-- Execute using psql with ON_ERROR_STOP=1, on ONE verified connection.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

DO $approval$
BEGIN
    IF current_setting('mininode.pw03_pr5_target_database', true)
       IS DISTINCT FROM current_database() THEN
        RAISE EXCEPTION 'PW03 PR5: target database approval is missing or mismatched';
    END IF;
    IF current_setting('mininode.pw03_pr5_ack', true)
       IS DISTINCT FROM 'DELETE_2_PAID_1_PENDING_LEGACY_ORDERS' THEN
        RAISE EXCEPTION 'PW03 PR5: explicit destructive acknowledgement missing';
    END IF;
END
$approval$;

-- Freeze legacy writes and the inventory before checking expected records.
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
BEGIN
    SELECT count(*), count(*) FILTER (WHERE status = 'active')
      INTO total_plans, active_plans
      FROM privacy.correction_plan;
    SELECT count(*),
           count(*) FILTER (
               WHERE status = 'paid' AND paid_at IS NOT NULL AND correction_plan_id IS NOT NULL
           ),
           count(*) FILTER (
               WHERE status = 'pending_payment' AND paid_at IS NULL AND correction_plan_id IS NULL
           )
      INTO total_orders, paid_orders, pending_orders
      FROM privacy.correction_plan_order;
    SELECT count(*) INTO total_checks FROM privacy.correction_plan_check;

    IF total_plans <> 2 OR active_plans <> 2
       OR total_orders <> 3 OR paid_orders <> 2 OR pending_orders <> 1
       OR total_checks <> 1 THEN
        RAISE EXCEPTION 'PW03 PR5: legacy inventory differs from approved 2 plans / 3 orders / 1 check; abort';
    END IF;
END
$inventory$;

-- Exact legacy objects only; any unforeseen external FK/dependency blocks the
-- whole transaction rather than cascading into diagnostics or the new Plan.
DROP TABLE privacy.correction_plan_check RESTRICT;
DROP TABLE privacy.correction_plan_order RESTRICT;
DROP TABLE privacy.correction_plan RESTRICT;
COMMIT;
