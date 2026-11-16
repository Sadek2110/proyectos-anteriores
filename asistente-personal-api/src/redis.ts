import { createHash, randomUUID } from 'node:crypto';
import { createClient, type RedisClientType } from 'redis';
import type { AppConfig } from './config.js';
import { conflictError } from './errors.js';
import type { CoordinationService, RateLimitResult } from './types.js';

const RATE_LIMIT_SCRIPT = `
local current = redis.call('INCR', KEYS[1])
if current == 1 then redis.call('PEXPIRE', KEYS[1], ARGV[1]) end
local ttl = redis.call('PTTL', KEYS[1])
return {current, ttl}
`;

const RELEASE_LOCK_SCRIPT = `
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('DEL', KEYS[1])
end
return 0
`;

export function createRedisClient(config: AppConfig): RedisClientType | undefined {
  if (!config.REDIS_URL) return undefined;
  return createClient({
    url: config.REDIS_URL,
    socket: {
      connectTimeout: config.REDIS_CONNECT_TIMEOUT_MS,
      reconnectStrategy: (retries) => Math.min(100 * 2 ** retries, 3_000),
    },
  });
}

export class RedisCoordinationService implements CoordinationService {
  constructor(
    private readonly client: RedisClientType,
    private readonly prefix: string,
  ) {}

  private key(kind: string, value: string): string {
    return `${this.prefix}${kind}:${value}`;
  }

  private digest(value: string): string {
    return createHash('sha256').update(value).digest('hex');
  }

  async ping(): Promise<boolean> {
    return (await this.client.ping()) === 'PONG';
  }

  async consumeRateLimit(key: string, limit: number, windowMs: number): Promise<RateLimitResult> {
    const result = await this.client.eval(RATE_LIMIT_SCRIPT, {
      keys: [this.key('rate', this.digest(key))],
      arguments: [String(windowMs)],
    }) as [number, number];
    const [count, ttl] = result;
    return {
      allowed: count <= limit,
      retryAfterSeconds: Math.max(1, Math.ceil(Math.max(ttl, 0) / 1000)),
    };
  }

  async withLock<T>(key: string, ttlMs: number, operation: () => Promise<T>): Promise<T> {
    const redisKey = this.key('lock', key);
    const token = randomUUID();
    const acquired = await this.client.set(redisKey, token, { NX: true, PX: ttlMs });
    if (acquired !== 'OK') throw conflictError('El recurso ya se está procesando.');
    try {
      return await operation();
    } finally {
      try {
        await this.client.eval(RELEASE_LOCK_SCRIPT, { keys: [redisKey], arguments: [token] });
      } catch {
        // El TTL liberará el bloqueo aunque Redis falle durante el cleanup.
      }
    }
  }

  async runIdempotent<T>(
    key: string | undefined,
    ttlSeconds: number,
    operation: () => Promise<T>,
  ): Promise<{ value: T; replayed: boolean }> {
    if (!key) return { value: await operation(), replayed: false };

    const redisKey = this.key('idempotency', this.digest(key));
    const token = randomUUID();
    const pending = JSON.stringify({ state: 'pending', token });
    const acquired = await this.client.set(redisKey, pending, { NX: true, EX: ttlSeconds });
    if (acquired !== 'OK') {
      const existing = await this.client.get(redisKey);
      if (existing) {
        const parsed = JSON.parse(existing) as { state?: string; value?: T };
        if (parsed.state === 'done') return { value: parsed.value as T, replayed: true };
      }
      throw conflictError('Ya existe una operación con esta clave de idempotencia en curso.');
    }

    try {
      const value = await operation();
      await this.client.set(redisKey, JSON.stringify({ state: 'done', value }), { EX: ttlSeconds });
      return { value, replayed: false };
    } catch (error) {
      await this.client.eval(RELEASE_LOCK_SCRIPT, { keys: [redisKey], arguments: [pending] });
      throw error;
    }
  }

  async close(): Promise<void> {
    if (this.client.isOpen) await this.client.quit();
  }
}
