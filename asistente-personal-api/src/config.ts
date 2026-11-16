import { z } from 'zod';

const optionalSecret = z.preprocess(
  (value) => (typeof value === 'string' && value.trim() === '' ? undefined : value),
  z.string().min(1).optional(),
);

const envSchema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  HOST: z.string().default('0.0.0.0'),
  PORT: z.coerce.number().int().min(1).max(65535).default(3000),
  LOG_LEVEL: z.enum(['fatal', 'error', 'warn', 'info', 'debug', 'trace', 'silent']).default('info'),
  INTERNAL_API_KEY: z.string().min(24, 'INTERNAL_API_KEY debe tener al menos 24 caracteres'),
  RATE_LIMIT_MAX: z.coerce.number().int().positive().default(60),
  RATE_LIMIT_WINDOW_MS: z.coerce.number().int().min(1000).default(60_000),
  DATABASE_URL: optionalSecret,
  DATABASE_POOL_MAX: z.coerce.number().int().min(1).max(50).default(10),
  DATABASE_CONNECTION_TIMEOUT_MS: z.coerce.number().int().min(500).default(5_000),
  REDIS_URL: optionalSecret,
  REDIS_PREFIX: z.string().min(1).default('assistant:'),
  REDIS_CONNECT_TIMEOUT_MS: z.coerce.number().int().min(500).default(5_000),
  IDEMPOTENCY_TTL_SEC: z.coerce.number().int().min(60).default(86_400),
  TASK_LOCK_TTL_MS: z.coerce.number().int().min(1_000).default(120_000),
  APPROVAL_TTL_SEC: z.coerce.number().int().min(60).max(86_400).default(900),
  TELEGRAM_ALLOWED_USER_IDS: z.string().default('6736438056').transform((value, context) => {
    const ids = value.split(',').map((item) => Number(item.trim())).filter((id) => Number.isSafeInteger(id) && id > 0);
    if (ids.length === 0) {
      context.addIssue({ code: 'custom', message: 'TELEGRAM_ALLOWED_USER_IDS debe incluir al menos un ID válido' });
      return z.NEVER;
    }
    return [...new Set(ids)];
  }),
  NOTION_API_TOKEN: optionalSecret,
  NOTION_API_VERSION: z.string().default('2026-03-11'),
  NOTION_TASKS_DATA_SOURCE_ID: z.string().uuid().default('9704e6c4-5a4f-4423-92ce-ea484247d7af'),
  NOTION_PROJECTS_DATA_SOURCE_ID: z.string().uuid().default('3a0ea89f-ffd0-4f3b-90b5-ac032ee2847f'),
  OPENCODE_BASE_URL: z.url().default('https://asistente-personal-opencode-agent.lm3vrq.easypanel.host'),
  OPENCODE_USERNAME: optionalSecret,
  OPENCODE_PASSWORD: optionalSecret,
  OPENCODE_PROVIDER_ID: z.string().default('opencode-go'),
  OPENCODE_MODEL_ID: z.string().default('deepseek-v4-flash'),
  OPENCODE_WORKSPACE: z.string().default('/workspace'),
});

export type AppConfig = z.infer<typeof envSchema>;

export function loadConfig(env: NodeJS.ProcessEnv = process.env): AppConfig {
  return envSchema.parse(env);
}

