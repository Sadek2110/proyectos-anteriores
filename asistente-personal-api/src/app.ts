import { createHash, timingSafeEqual } from 'node:crypto';
import { readFileSync } from 'node:fs';
import Fastify, { type FastifyInstance, type FastifyRequest } from 'fastify';
import { ZodError, type ZodType } from 'zod';
import type { AppConfig } from './config.js';
import { MemoryApprovalService } from './approvals.js';
import { ApiError, validationError } from './errors.js';
import { MemoryCoordinationService, NullPersistenceService } from './memory-infrastructure.js';
import { NotionWorkspaceService } from './notion.js';
import { OpenCodeAssistantService } from './opencode.js';
import {
  completeTaskSchema,
  approvalDecisionSchema,
  approvalParamsSchema,
  createApprovalSchema,
  createTaskSchema,
  listTasksQuerySchema,
  messageSchema,
  projectParamsSchema,
  taskParamsSchema,
  updateTaskSchema,
} from './schemas.js';
import type {
  ApprovalService,
  AssistantService,
  CoordinationService,
  PersistenceService,
  WorkspaceService,
} from './types.js';

const packageVersion: string = (() => {
  try {
    const raw = readFileSync(new URL('../../package.json', import.meta.url), 'utf8');
    return (JSON.parse(raw) as { version?: string }).version ?? 'unknown';
  } catch {
    return 'unknown';
  }
})();

interface Dependencies {
  assistant?: AssistantService;
  workspace?: WorkspaceService;
  persistence?: PersistenceService;
  coordination?: CoordinationService;
  approvals?: ApprovalService;
  postgresConfigured?: boolean;
  redisConfigured?: boolean;
  now?: () => Date;
}

function parse<T>(schema: ZodType<T>, value: unknown): T {
  const result = schema.safeParse(value);
  if (!result.success) throw validationError(result.error);
  return result.data;
}

function safeEqual(received: string, expected: string): boolean {
  const a = Buffer.from(received);
  const b = Buffer.from(expected);
  return a.length === b.length && timingSafeEqual(a, b);
}

function headerValue(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function resourceType(url: string): string {
  if (url.startsWith('/tasks')) return 'task';
  if (url.startsWith('/projects')) return 'project';
  if (url.startsWith('/assistant')) return 'assistant';
  if (url.startsWith('/approvals')) return 'approval';
  return 'api';
}

export function buildApp(config: AppConfig, dependencies: Dependencies = {}): FastifyInstance {
  const app = Fastify({
    logger: config.LOG_LEVEL === 'silent' ? false : { level: config.LOG_LEVEL },
    requestIdHeader: 'x-request-id',
    trustProxy: true,
    bodyLimit: 256 * 1024,
  });
  const assistant = dependencies.assistant ?? new OpenCodeAssistantService(config);
  const workspace = dependencies.workspace ?? new NotionWorkspaceService(config);
  const persistence = dependencies.persistence ?? new NullPersistenceService();
  const coordination = dependencies.coordination ?? new MemoryCoordinationService();
  const now = dependencies.now ?? (() => new Date());
  const approvals = dependencies.approvals ?? new MemoryApprovalService(config.TELEGRAM_ALLOWED_USER_IDS, now);
  const postgresConfigured = dependencies.postgresConfigured ?? Boolean(config.DATABASE_URL);
  const redisConfigured = dependencies.redisConfigured ?? Boolean(config.REDIS_URL);

  async function executeTracked<T>(
    request: FastifyRequest,
    action: string,
    taskPageId: string | undefined,
    operation: () => Promise<T>,
    lockKey?: string,
  ): Promise<{ value: T; replayed: boolean }> {
    const idempotencyHeader = headerValue(request.headers['idempotency-key']);
    const idempotencyKey = idempotencyHeader ? `${action}:${idempotencyHeader}` : undefined;
    const executionId = await persistence.startExecution({
      requestId: request.id,
      action,
      ...(taskPageId ? { taskPageId } : {}),
      ...(idempotencyKey ? { idempotencyKey } : {}),
    });

    try {
      const run = () => lockKey
        ? coordination.withLock(lockKey, config.TASK_LOCK_TTL_MS, operation)
        : operation();
      const result = await coordination.runIdempotent(idempotencyKey, config.IDEMPOTENCY_TTL_SEC, run);
      try {
        await persistence.finishExecution(executionId, 'success', { replayed: result.replayed });
      } catch (error) {
        request.log.error({ err: error, executionId }, 'No se pudo cerrar el registro de ejecución.');
      }
      return result;
    } catch (error) {
      try {
        await persistence.finishExecution(executionId, 'error', undefined, error);
      } catch (persistenceError) {
        request.log.error({ err: persistenceError, executionId }, 'No se pudo registrar el error de ejecución.');
      }
      throw error;
    }
  }

  app.addHook('onRequest', async (request, reply) => {
    if (request.url === '/health') return;
    const bearer = request.headers.authorization?.startsWith('Bearer ')
      ? request.headers.authorization.slice(7)
      : undefined;
    const received = bearer ?? headerValue(request.headers['x-api-key']) ?? '';
    if (!safeEqual(received, config.INTERNAL_API_KEY)) {
      throw new ApiError(401, 'unauthorized', 'Credenciales no válidas.');
    }

    const credentialDigest = createHash('sha256').update(received).digest('hex');
    const rate = await coordination.consumeRateLimit(
      `${credentialDigest}:${request.ip}`,
      config.RATE_LIMIT_MAX,
      config.RATE_LIMIT_WINDOW_MS,
    );
    if (!rate.allowed) {
      reply.header('retry-after', rate.retryAfterSeconds);
      throw new ApiError(429, 'rate_limit_exceeded', 'Demasiadas solicitudes. Inténtalo de nuevo más tarde.');
    }
  });

  app.addHook('onResponse', async (request, reply) => {
    if (request.url === '/health') return;
    try {
      await persistence.recordAudit({
        actor: 'internal-api',
        action: `${request.method} ${request.routeOptions.url ?? request.url}`,
        resourceType: resourceType(request.url),
        metadata: {
          requestId: request.id,
          statusCode: reply.statusCode,
          ip: request.ip,
        },
      });
    } catch (error) {
      request.log.error({ err: error }, 'No se pudo guardar el evento de auditoría.');
    }
  });

  app.setErrorHandler((error, request, reply) => {
    const normalized = error instanceof ZodError ? validationError(error) : error;
    if (normalized instanceof ApiError) {
      request.log.warn({ code: normalized.code, details: normalized.details }, normalized.message);
      return reply.status(normalized.statusCode).send({
        error: {
          code: normalized.code,
          message: normalized.message,
          ...(normalized.details === undefined ? {} : { details: normalized.details }),
          requestId: request.id,
        },
      });
    }
    request.log.error(error);
    return reply.status(500).send({
      error: { code: 'internal_error', message: 'Error interno del servidor.', requestId: request.id },
    });
  });

  app.get('/health', async (_request, reply) => {
    const [postgres, redis] = await Promise.allSettled([
      postgresConfigured ? persistence.ping() : Promise.resolve(false),
      redisConfigured ? coordination.ping() : Promise.resolve(false),
    ]);
    const postgresOk = postgres.status === 'fulfilled' && postgres.value;
    const redisOk = redis.status === 'fulfilled' && redis.value;
    const degraded = (postgresConfigured && !postgresOk) || (redisConfigured && !redisOk);
    return reply.status(degraded ? 503 : 200).send({
      status: degraded ? 'degraded' : 'ok',
      service: 'asistente-personal-api',
      version: packageVersion,
      timestamp: now().toISOString(),
      integrations: {
        notion: Boolean(config.NOTION_API_TOKEN),
        opencode: Boolean(config.OPENCODE_USERNAME && config.OPENCODE_PASSWORD),
        postgres: { configured: postgresConfigured, ok: postgresOk },
        redis: { configured: redisConfigured, ok: redisOk },
      },
    });
  });

  app.post('/assistant/message', async (request, reply) => {
    const input = parse(messageSchema, request.body);
    const result = await executeTracked(request, 'assistant.message', undefined, async () => {
      const assistantReply = await assistant.message(input);
      await persistence.recordConversation({
        conversationId: assistantReply.sessionId,
        input: input.message,
        output: assistantReply.message,
      });
      return assistantReply;
    });
    if (result.replayed) reply.header('x-idempotent-replay', 'true');
    return reply.send({ data: result.value });
  });

  app.post('/tasks', async (request, reply) => {
    const input = parse(createTaskSchema, request.body);
    const result = await executeTracked(request, 'task.create', undefined, () => workspace.createTask(input));
    if (result.replayed) reply.header('x-idempotent-replay', 'true');
    return reply.status(result.replayed ? 200 : 201).send({ data: result.value });
  });

  app.get('/tasks', async (request, reply) => {
    const query = parse(listTasksQuerySchema, request.query);
    const tasks = await workspace.listTasks(query);
    return reply.send({ data: tasks, meta: { total: tasks.length, filters: query } });
  });

  app.get('/tasks/today', async (_request, reply) => {
    const date = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Europe/Madrid', year: 'numeric', month: '2-digit', day: '2-digit',
    }).format(now());
    const tasks = await workspace.listToday(date);
    return reply.send({ data: tasks, meta: { total: tasks.length, date } });
  });

  app.patch('/tasks/:id', async (request, reply) => {
    const { id } = parse(taskParamsSchema, request.params);
    const input = parse(updateTaskSchema, request.body);
    const result = await executeTracked(
      request,
      'task.update',
      id,
      () => workspace.updateTask(id, input),
      `notion-task:${id}`,
    );
    if (result.replayed) reply.header('x-idempotent-replay', 'true');
    return reply.send({ data: result.value });
  });

  app.post('/tasks/:id/complete', async (request, reply) => {
    const { id } = parse(taskParamsSchema, request.params);
    const input = parse(completeTaskSchema, request.body ?? {});
    const result = await executeTracked(
      request,
      'task.complete',
      id,
      () => workspace.completeTask(id, input),
      `notion-task:${id}`,
    );
    if (result.replayed) reply.header('x-idempotent-replay', 'true');
    return reply.send({ data: result.value });
  });

  app.get('/projects', async (_request, reply) => {
    const projects = await workspace.listProjects();
    return reply.send({ data: projects, meta: { total: projects.length } });
  });

  app.get('/projects/:id/status', async (request, reply) => {
    const { id } = parse(projectParamsSchema, request.params);
    return reply.send({ data: await workspace.getProjectStatus(id) });
  });

  app.post('/approvals', async (request, reply) => {
    const input = parse(createApprovalSchema, request.body);
    const result = await executeTracked(
      request,
      'approval.create',
      undefined,
      () => approvals.create(input, config.APPROVAL_TTL_SEC),
    );
    if (result.replayed) reply.header('x-idempotent-replay', 'true');
    return reply.status(result.replayed ? 200 : 201).send({ data: result.value });
  });

  app.get('/approvals/:id', async (request, reply) => {
    const { id } = parse(approvalParamsSchema, request.params);
    return reply.send({ data: await approvals.get(id) });
  });

  app.post('/approvals/:id/approve', async (request, reply) => {
    const { id } = parse(approvalParamsSchema, request.params);
    const { telegramUserId } = parse(approvalDecisionSchema, request.body);
    const result = await executeTracked(
      request,
      'approval.approve',
      undefined,
      () => approvals.approve(id, telegramUserId),
      `approval:${id}`,
    );
    if (result.replayed) reply.header('x-idempotent-replay', 'true');
    return reply.send({ data: result.value });
  });

  app.post('/approvals/:id/reject', async (request, reply) => {
    const { id } = parse(approvalParamsSchema, request.params);
    const { telegramUserId } = parse(approvalDecisionSchema, request.body);
    const result = await executeTracked(
      request,
      'approval.reject',
      undefined,
      () => approvals.reject(id, telegramUserId),
      `approval:${id}`,
    );
    if (result.replayed) reply.header('x-idempotent-replay', 'true');
    return reply.send({ data: result.value });
  });

  app.post('/approvals/:id/consume', async (request, reply) => {
    const { id } = parse(approvalParamsSchema, request.params);
    const { telegramUserId } = parse(approvalDecisionSchema, request.body);
    const result = await executeTracked(
      request,
      'approval.consume',
      undefined,
      () => approvals.consume(id, telegramUserId),
      `approval:${id}`,
    );
    if (result.replayed) reply.header('x-idempotent-replay', 'true');
    return reply.send({ data: result.value });
  });

  return app;
}

