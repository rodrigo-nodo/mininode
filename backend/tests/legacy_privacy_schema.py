"""SQL de compatibilidad histórica, usado solo para pruebas con PostgreSQL desechable."""

LEGACY_PLAN_SQL = """
CREATE SCHEMA IF NOT EXISTS privacy;

CREATE TABLE IF NOT EXISTS privacy.correction_plan (
    id UUID PRIMARY KEY,
    site_url TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    plan_snapshot JSONB NOT NULL,
    plan_version TEXT NOT NULL,
    actions_version TEXT NOT NULL,
    initial_score INTEGER NOT NULL CHECK (initial_score BETWEEN 0 AND 100),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'revoked')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

LEGACY_ORDER_SQL = """
CREATE SCHEMA IF NOT EXISTS privacy;

CREATE TABLE IF NOT EXISTS privacy.correction_plan_order (
    id UUID PRIMARY KEY,
    diagnostic_id UUID NOT NULL REFERENCES privacy.diagnostic(id),
    correction_plan_id UUID NULL REFERENCES privacy.correction_plan(id),
    site_url TEXT NOT NULL,
    email TEXT NOT NULL,
    product_code TEXT NOT NULL CHECK (product_code = 'PRIVACY_CORRECTION_PLAN'),
    amount INTEGER NOT NULL CONSTRAINT correction_plan_order_amount_allowed_check
        CHECK (amount IN (49900, 9900)),
    currency TEXT NOT NULL CHECK (currency = 'CLP'),
    status TEXT NOT NULL CHECK (status IN ('pending_payment', 'paid', 'cancelled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE privacy.correction_plan_order
    ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ NULL;

ALTER TABLE privacy.correction_plan_order
    ADD COLUMN IF NOT EXISTS correction_plan_id UUID NULL;

DO $$
DECLARE
    legacy_constraint RECORD;
BEGIN
    FOR legacy_constraint IN
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'privacy.correction_plan_order'::regclass
          AND contype = 'c'
          AND pg_get_constraintdef(oid) ~ '^CHECK \\(\\(amount = 49900\\)\\)$'
    LOOP
        EXECUTE format(
            'ALTER TABLE privacy.correction_plan_order DROP CONSTRAINT %I',
            legacy_constraint.conname
        );
    END LOOP;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'correction_plan_order_amount_allowed_check'
          AND conrelid = 'privacy.correction_plan_order'::regclass
    ) THEN
        ALTER TABLE privacy.correction_plan_order
            ADD CONSTRAINT correction_plan_order_amount_allowed_check
            CHECK (amount IN (49900, 9900));
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'correction_plan_order_correction_plan_id_fkey'
          AND conrelid = 'privacy.correction_plan_order'::regclass
    ) THEN
        ALTER TABLE privacy.correction_plan_order
            ADD CONSTRAINT correction_plan_order_correction_plan_id_fkey
            FOREIGN KEY (correction_plan_id) REFERENCES privacy.correction_plan(id);
    END IF;
END $$;
"""

LEGACY_CHECK_SQL = """
CREATE SCHEMA IF NOT EXISTS privacy;

CREATE TABLE IF NOT EXISTS privacy.correction_plan_check (
    id UUID PRIMARY KEY,
    correction_plan_id UUID NOT NULL REFERENCES privacy.correction_plan(id),
    order_id UUID NOT NULL REFERENCES privacy.correction_plan_order(id),
    original_diagnostic_id UUID NOT NULL REFERENCES privacy.diagnostic(id),
    check_diagnostic_id UUID NOT NULL REFERENCES privacy.diagnostic(id),
    result_snapshot JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

DO $$
DECLARE
    single_use_constraint RECORD;
BEGIN
    FOR single_use_constraint IN
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'privacy.correction_plan_check'::regclass
          AND contype = 'u'
          AND pg_get_constraintdef(oid) = 'UNIQUE (correction_plan_id)'
    LOOP
        EXECUTE format(
            'ALTER TABLE privacy.correction_plan_check DROP CONSTRAINT %I',
            single_use_constraint.conname
        );
    END LOOP;
END $$;

CREATE INDEX IF NOT EXISTS correction_plan_check_plan_created_idx
    ON privacy.correction_plan_check (correction_plan_id, created_at DESC);
"""
