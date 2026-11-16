CREATE TABLE IF NOT EXISTS users (
  id text PRIMARY KEY,
  telegram_user_id bigint UNIQUE,
  name text NOT NULL,
  role text NOT NULL DEFAULT 'user',
  enabled boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS conversations (
  id text PRIMARY KEY,
  user_id text REFERENCES users(id) ON DELETE SET NULL,
  channel text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
  id text PRIMARY KEY,
  conversation_id text NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  direction text NOT NULL CHECK (direction IN ('inbound', 'outbound')),
  content text NOT NULL,
  intent text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS messages_conversation_created_idx
  ON messages (conversation_id, created_at);

CREATE TABLE IF NOT EXISTS executions (
  id text PRIMARY KEY,
  request_id text NOT NULL,
  task_page_id text,
  action text NOT NULL,
  status text NOT NULL CHECK (status IN ('running', 'success', 'error')),
  idempotency_key text,
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz,
  result jsonb,
  error jsonb
);

CREATE INDEX IF NOT EXISTS executions_task_started_idx
  ON executions (task_page_id, started_at DESC);
CREATE INDEX IF NOT EXISTS executions_action_started_idx
  ON executions (action, started_at DESC);
CREATE INDEX IF NOT EXISTS executions_idempotency_idx
  ON executions (idempotency_key) WHERE idempotency_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS approvals (
  id text PRIMARY KEY,
  user_id text REFERENCES users(id) ON DELETE SET NULL,
  action_type text NOT NULL,
  payload jsonb NOT NULL,
  status text NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'approved', 'rejected', 'expired', 'used')),
  expires_at timestamptz NOT NULL,
  approved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS approvals_status_expires_idx
  ON approvals (status, expires_at);

CREATE TABLE IF NOT EXISTS audit_logs (
  id bigserial PRIMARY KEY,
  actor text NOT NULL,
  action text NOT NULL,
  resource_type text NOT NULL,
  resource_id text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS audit_logs_resource_created_idx
  ON audit_logs (resource_type, resource_id, created_at DESC);
CREATE INDEX IF NOT EXISTS audit_logs_action_created_idx
  ON audit_logs (action, created_at DESC);

CREATE TABLE IF NOT EXISTS external_links (
  id bigserial PRIMARY KEY,
  notion_page_id text NOT NULL,
  github_issue_id text,
  github_pr_id text,
  deployment_id text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (notion_page_id, github_issue_id, github_pr_id, deployment_id)
);
