import type { AppConfig } from './config.js';
import { MemoryApprovalService, PostgresApprovalService } from './approvals.js';
import { MemoryCoordinationService, NullPersistenceService } from './memory-infrastructure.js';
import { createPostgresPool, PostgresPersistenceService } from './postgres.js';
import { createRedisClient, RedisCoordinationService } from './redis.js';
import type { ApprovalService, CoordinationService, PersistenceService } from './types.js';

export interface RuntimeServices {
  persistence: PersistenceService;
  coordination: CoordinationService;
  approvals: ApprovalService;
  postgresConfigured: boolean;
  redisConfigured: boolean;
  close(): Promise<void>;
}

export async function createRuntimeServices(config: AppConfig): Promise<RuntimeServices> {
  const pool = createPostgresPool(config);
  const redis = createRedisClient(config);

  const persistence: PersistenceService = pool
    ? new PostgresPersistenceService(pool)
    : new NullPersistenceService();
  const approvals: ApprovalService = pool
    ? new PostgresApprovalService(pool, config.TELEGRAM_ALLOWED_USER_IDS)
    : new MemoryApprovalService(config.TELEGRAM_ALLOWED_USER_IDS);
  let coordination: CoordinationService = new MemoryCoordinationService();

  try {
    if (pool) await persistence.ping();
    if (redis) {
      await redis.connect();
      coordination = new RedisCoordinationService(redis, config.REDIS_PREFIX);
      await coordination.ping();
    }
  } catch (error) {
    if (redis?.isOpen) await redis.quit();
    if (pool) await pool.end();
    throw error;
  }

  return {
    persistence,
    coordination,
    approvals,
    postgresConfigured: Boolean(pool),
    redisConfigured: Boolean(redis),
    async close() {
      await Promise.allSettled([coordination.close(), persistence.close()]);
    },
  };
}
