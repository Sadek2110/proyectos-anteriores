import { randomUUID } from 'node:crypto';
import { Pool, type PoolConfig } from 'pg';
import type { AppConfig } from './config.js';
import type {
  AuditRecord,
  ConversationRecord,
  ExecutionRecord,
  PersistenceService,
} from './types.js';

function normalizeError(error: unknown): Record<string, unknown> {
  if (error instanceof Error) return { name: error.name, message: error.message };
  return { message: String(error) };
}

export function createPostgresPool(config: AppConfig): Pool | undefined {
  if (!config.DATABASE_URL) return undefined;
  const poolConfig: PoolConfig = {
    connectionString: config.DATABASE_URL,
    max: config.DATABASE_POOL_MAX,
    connectionTimeoutMillis: config.DATABASE_CONNECTION_TIMEOUT_MS,
    idleTimeoutMillis: 30_000,
    application_name: 'asistente-personal-api',
  };
  return new Pool(poolConfig);
}

export class PostgresPersistenceService implements PersistenceService {
  constructor(private readonly pool: Pool) {}

  async ping(): Promise<boolean> {
    await this.pool.query('SELECT 1');
    return true;
  }

  async recordAudit(record: AuditRecord): Promise<void> {
    await this.pool.query(
      `INSERT INTO audit_logs (actor, action, resource_type, resource_id, metadata)
       VALUES ($1, $2, $3, $4, $5::jsonb)`,
      [record.actor, record.action, record.resourceType, record.resourceId ?? null, JSON.stringify(record.metadata ?? {})],
    );
  }

  async startExecution(record: ExecutionRecord): Promise<string> {
    const id = randomUUID();
    await this.pool.query(
      `INSERT INTO executions (id, request_id, task_page_id, action, status, idempotency_key)
       VALUES ($1, $2, $3, $4, 'running', $5)`,
      [id, record.requestId, record.taskPageId ?? null, record.action, record.idempotencyKey ?? null],
    );
    return id;
  }

  async finishExecution(id: string, status: 'success' | 'error', result?: unknown, error?: unknown): Promise<void> {
    await this.pool.query(
      `UPDATE executions
       SET status = $2, finished_at = NOW(), result = $3::jsonb, error = $4::jsonb
       WHERE id = $1`,
      [
        id,
        status,
        result === undefined ? null : JSON.stringify(result),
        error === undefined ? null : JSON.stringify(normalizeError(error)),
      ],
    );
  }

  async recordConversation(record: ConversationRecord): Promise<void> {
    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');
      await client.query(
        `INSERT INTO conversations (id, channel)
         VALUES ($1, 'api')
         ON CONFLICT (id) DO NOTHING`,
        [record.conversationId],
      );
      await client.query(
        `INSERT INTO messages (id, conversation_id, direction, content, intent)
         VALUES ($1, $2, 'inbound', $3, $4), ($5, $2, 'outbound', $6, $4)`,
        [randomUUID(), record.conversationId, record.input, record.intent ?? null, randomUUID(), record.output],
      );
      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async close(): Promise<void> {
    await this.pool.end();
  }
}
