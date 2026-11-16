ALTER TABLE approvals
  ADD COLUMN IF NOT EXISTS summary text NOT NULL DEFAULT 'Aprobación pendiente',
  ADD COLUMN IF NOT EXISTS risk_level smallint NOT NULL DEFAULT 3,
  ADD COLUMN IF NOT EXISTS rejected_at timestamptz,
  ADD COLUMN IF NOT EXISTS used_at timestamptz,
  ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

ALTER TABLE approvals
  DROP CONSTRAINT IF EXISTS approvals_risk_level_check;

ALTER TABLE approvals
  ADD CONSTRAINT approvals_risk_level_check CHECK (risk_level IN (3, 4));

CREATE INDEX IF NOT EXISTS approvals_user_status_created_idx
  ON approvals (user_id, status, created_at DESC);
