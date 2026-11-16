import { randomUUID } from 'node:crypto';
import { conflictError } from './errors.js';
import type {
  AuditRecord,
  ConversationRecord,
  CoordinationService,
  ExecutionRecord,
  PersistenceService,
  RateLimitResult,
} from './types.js';

interface RateEntry {
  count: number;
  resetAt: number;
}

interface IdempotentEntry {
  expiresAt: number;
  state: 'pending' | 'done';
  value?: unknown;
}

export class MemoryCoordinationService implements CoordinationService {
  private readonly limits = new Map<string, RateEntry>();
  private readonly locks = new Map<string, number>();
  private readonly idempotency = new Map<string, IdempotentEntry>();

  async ping(): Promise<boolean> {
    return true;
  }

  async consumeRateLimit(key: string, limit: number, windowMs: number): Promise<RateLimitResult> {
    const now = Date.now();
    const entry = this.limits.get(key);
    if (!entry || entry.resetAt <= now) {
      this.limits.set(key, { count: 1, resetAt: now + windowMs });
      return { allowed: true, retryAfterSeconds: 0 };
    }
    entry.count += 1;
    return {
      allowed: entry.count <= limit,
      retryAfterSeconds: Math.max(1, Math.ceil((entry.resetAt - now) / 1000)),
    };
  }

  async withLock<T>(key: string, ttlMs: number, operation: () => Promise<T>): Promise<T> {
    const now = Date.now();
    const lockedUntil = this.locks.get(key) ?? 0;
    if (lockedUntil > now) throw conflictError('El recurso ya se está procesando.');
    this.locks.set(key, now + ttlMs);
    try {
      return await operation();
    } finally {
      this.locks.delete(key);
    }
  }

  async runIdempotent<T>(
    key: string | undefined,
    ttlSeconds: number,
    operation: () => Promise<T>,
  ): Promise<{ value: T; replayed: boolean }> {
    if (!key) return { value: await operation(), replayed: false };

    const now = Date.now();
    const existing = this.idempotency.get(key);
    if (existing && existing.expiresAt > now) {
      if (existing.state === 'done') return { value: existing.value as T, replayed: true };
      throw conflictError('Ya existe una operación con esta clave de idempotencia en curso.');
    }

    const expiresAt = now + ttlSeconds * 1000;
    this.idempotency.set(key, { state: 'pending', expiresAt });
    try {
      const value = await operation();
      this.idempotency.set(key, { state: 'done', value, expiresAt });
      return { value, replayed: false };
    } catch (error) {
      this.idempotency.delete(key);
      throw error;
    }
  }

  async close(): Promise<void> {}
}

export class NullPersistenceService implements PersistenceService {
  async ping(): Promise<boolean> { return true; }
  async recordAudit(_record: AuditRecord): Promise<void> {}
  async startExecution(_record: ExecutionRecord): Promise<string> { return randomUUID(); }
  async finishExecution(_id: string, _status: 'success' | 'error', _result?: unknown, _error?: unknown): Promise<void> {}
  async recordConversation(_record: ConversationRecord): Promise<void> {}
  async close(): Promise<void> {}
}
