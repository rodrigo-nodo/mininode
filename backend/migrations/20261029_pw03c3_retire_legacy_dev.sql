-- PW-03C3: DEV-only, manually authorized retirement of empty legacy tables.
-- PREPARATION ONLY. Do not execute during this PR. Never execute in PROD.
-- Not registered in predeploy APPROVED_CHECKSUMS; an explicit separate operation is required.
-- The manual runner provides one transaction. No CASCADE, no data migrations.
SET LOCAL lock_timeout = '5s';

DO $preflight$
BEGIN
  IF current_database() <> 'mininode_db_dev' THEN
    RAISE EXCEPTION 'PW-03C3 is DEV-only: unexpected database %', current_database();
  END IF;
  IF to_regclass('privacy.correction_plan') IS NULL
     OR to_regclass('privacy.correction_plan_order') IS NULL
     OR to_regclass('privacy.correction_plan_check') IS NULL THEN
    RAISE EXCEPTION 'PW-03C3: expected legacy tables missing; investigate, do not proceed';
  END IF;
  IF to_regclass('privacy.entitled_plan') IS NULL
     OR to_regclass('privacy.entitled_plan_check') IS NULL THEN
    RAISE EXCEPTION 'PW-03C3: current entitled Plan schema missing; do not proceed';
  END IF;
END
$preflight$;

-- Lock all targets BEFORE checking emptiness, so no concurrent writer can
-- insert between the preflight and the destructive DDL. Fail fast on contention.
LOCK TABLE privacy.correction_plan,
           privacy.correction_plan_order,
           privacy.correction_plan_check IN ACCESS EXCLUSIVE MODE NOWAIT;

DO $empty$
BEGIN
  IF EXISTS (SELECT 1 FROM privacy.correction_plan)
     OR EXISTS (SELECT 1 FROM privacy.correction_plan_order)
     OR EXISTS (SELECT 1 FROM privacy.correction_plan_check) THEN
    RAISE EXCEPTION 'PW-03C3: at least one legacy table is not empty; refusing DROP';
  END IF;
END
$empty$;

-- RESTRICT prevents dropping unexpected dependent database objects.
-- Tables share FKs among themselves; listing all three handles those FKs.
-- Do not use CASCADE. Never drop privacy.diagnostic or entitled Plan tables.
DROP TABLE privacy.correction_plan_check,
           privacy.correction_plan_order,
           privacy.correction_plan RESTRICT;
