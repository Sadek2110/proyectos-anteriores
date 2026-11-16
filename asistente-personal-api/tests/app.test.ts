import assert from 'node:assert/strict';
import { test } from 'node:test';
import { buildApp } from '../src/app.js';
import type { AppConfig } from '../src/config.js';
import { MemoryCoordinationService } from '../src/memory-infrastructure.js';
import type { AssistantService, Project, ProjectStatus, Task, WorkspaceService } from '../src/types.js';

const apiKey = 'test-key-with-at-least-24-characters';
const config: AppConfig = {
  NODE_ENV: 'test',
  HOST: '127.0.0.1',
  PORT: 3000,
  LOG_LEVEL: 'silent',
  INTERNAL_API_KEY: apiKey,
  RATE_LIMIT_MAX: 100,
  RATE_LIMIT_WINDOW_MS: 60_000,
  DATABASE_POOL_MAX: 10,
  DATABASE_CONNECTION_TIMEOUT_MS: 5_000,
  REDIS_PREFIX: 'assistant:',
  REDIS_CONNECT_TIMEOUT_MS: 5_000,
  IDEMPOTENCY_TTL_SEC: 86_400,
  TASK_LOCK_TTL_MS: 120_000,
  APPROVAL_TTL_SEC: 900,
  TELEGRAM_ALLOWED_USER_IDS: [6736438056, 1111111111],
  NOTION_API_VERSION: '2026-03-11',
  NOTION_TASKS_DATA_SOURCE_ID: '9704e6c4-5a4f-4423-92ce-ea484247d7af',
  NOTION_PROJECTS_DATA_SOURCE_ID: '3a0ea89f-ffd0-4f3b-90b5-ac032ee2847f',
  OPENCODE_BASE_URL: 'https://example.com',
  OPENCODE_PROVIDER_ID: 'opencode-go',
  OPENCODE_MODEL_ID: 'deepseek-v4-flash',
  OPENCODE_WORKSPACE: '/workspace',
};

const sampleTask: Task = {
  id: 'task-1', title: 'Probar API', state: 'Próxima', priority: 'P2', area: 'Personal', type: 'Tarea',
  origin: 'API', aiMode: 'Ninguno', needsApproval: false, dueDate: '2026-07-20', projectIds: [], result: null,
  url: 'https://notion.so/task-1', createdAt: '2026-07-20T00:00:00.000Z', updatedAt: '2026-07-20T00:00:00.000Z',
};

const assistant: AssistantService = {
  async message() {
    return { message: 'Respuesta de prueba', sessionId: 'session-1', providerId: 'opencode-go', modelId: 'deepseek-v4-flash' };
  },
};

const workspace: WorkspaceService = {
  async createTask(input) { return { ...sampleTask, title: input.title, priority: input.priority, state: input.state }; },
  async listTasks() { return [sampleTask]; },
  async listToday() { return [sampleTask]; },
  async updateTask(_id, input) { return { ...sampleTask, ...('state' in input ? { state: input.state ?? sampleTask.state } : {}) }; },
  async completeTask(_id, input) { return { ...sampleTask, state: 'Hecha', result: input.result ?? null }; },
  async listProjects(): Promise<Project[]> { return []; },
  async getProjectStatus(): Promise<ProjectStatus> {
    throw new Error('not used');
  },
};

function createApp() {
  return buildApp(config, { assistant, workspace, now: () => new Date('2026-07-20T12:00:00+02:00') });
}

test('GET /health es público', async () => {
  const app = createApp();
  const response = await app.inject({ method: 'GET', url: '/health' });
  assert.equal(response.statusCode, 200);
  assert.equal(response.json().status, 'ok');
  await app.close();
});

test('los endpoints privados exigen API key', async () => {
  const app = createApp();
  const response = await app.inject({ method: 'GET', url: '/tasks/today' });
  assert.equal(response.statusCode, 401);
  assert.equal(response.json().error.code, 'unauthorized');
  await app.close();
});

test('POST /assistant/message usa OpenCode Go mediante el servicio', async () => {
  const app = createApp();
  const response = await app.inject({
    method: 'POST', url: '/assistant/message', headers: { 'x-api-key': apiKey }, payload: { message: 'Hola' },
  });
  assert.equal(response.statusCode, 200);
  assert.equal(response.json().data.modelId, 'deepseek-v4-flash');
  await app.close();
});

test('POST /tasks valida y crea una tarea', async () => {
  const app = createApp();
  const response = await app.inject({
    method: 'POST', url: '/tasks', headers: { authorization: `Bearer ${apiKey}` }, payload: { title: 'Nueva tarea', priority: 'P1' },
  });
  assert.equal(response.statusCode, 201);
  assert.equal(response.json().data.title, 'Nueva tarea');
  assert.equal(response.json().data.priority, 'P1');
  await app.close();
});

test('POST /tasks rechaza una prioridad inválida', async () => {
  const app = createApp();
  const response = await app.inject({
    method: 'POST', url: '/tasks', headers: { 'x-api-key': apiKey }, payload: { title: 'Nueva tarea', priority: 'urgente' },
  });
  assert.equal(response.statusCode, 400);
  assert.equal(response.json().error.code, 'validation_error');
  await app.close();
});

test('GET /tasks/today devuelve fecha de Madrid y metadatos', async () => {
  const app = createApp();
  const response = await app.inject({ method: 'GET', url: '/tasks/today', headers: { 'x-api-key': apiKey } });
  assert.equal(response.statusCode, 200);
  assert.equal(response.json().meta.date, '2026-07-20');
  assert.equal(response.json().meta.total, 1);
  await app.close();
});

test('POST /tasks acepta los estados Bandeja y Esperando de Notion', async () => {
  const app = createApp();
  for (const state of ['Bandeja', 'Esperando']) {
    const response = await app.inject({
      method: 'POST', url: '/tasks', headers: { 'x-api-key': apiKey }, payload: { title: 'Nueva tarea', state },
    });
    assert.equal(response.statusCode, 201);
    assert.equal(response.json().data.state, state);
  }
  await app.close();
});

test('POST /tasks rechaza un estado inexistente en Notion', async () => {
  const app = createApp();
  const response = await app.inject({
    method: 'POST', url: '/tasks', headers: { 'x-api-key': apiKey }, payload: { title: 'Nueva tarea', state: 'Pendiente' },
  });
  assert.equal(response.statusCode, 400);
  assert.equal(response.json().error.code, 'validation_error');
  await app.close();
});

test('GET /tasks devuelve la lista con total y filtros aplicados', async () => {
  const app = createApp();
  const response = await app.inject({ method: 'GET', url: '/tasks', headers: { 'x-api-key': apiKey } });
  assert.equal(response.statusCode, 200);
  assert.equal(response.json().meta.total, 1);
  assert.equal(response.json().meta.filters.includeClosed, false);
  assert.equal(response.json().data[0].id, 'task-1');
  await app.close();
});

test('GET /tasks traslada state, projectId e includeClosed al workspace', async () => {
  let received: unknown;
  const app = buildApp(config, {
    assistant,
    workspace: { ...workspace, async listTasks(query) { received = query; return []; } },
    now: () => new Date('2026-07-20T12:00:00+02:00'),
  });
  const projectId = '3a0ea89f-ffd0-4f3b-90b5-ac032ee2847f';
  const response = await app.inject({
    method: 'GET',
    url: `/tasks?state=Bandeja&projectId=${projectId}&includeClosed=true`,
    headers: { 'x-api-key': apiKey },
  });
  assert.equal(response.statusCode, 200);
  assert.deepEqual(received, { state: 'Bandeja', projectId, includeClosed: true });
  await app.close();
});

test('GET /tasks rechaza un estado desconocido en la query', async () => {
  const app = createApp();
  const response = await app.inject({
    method: 'GET', url: '/tasks?state=Pendiente', headers: { 'x-api-key': apiKey },
  });
  assert.equal(response.statusCode, 400);
  assert.equal(response.json().error.code, 'validation_error');
  await app.close();
});

test('Idempotency-Key evita crear dos veces la misma tarea', async () => {
  let creations = 0;
  const countedWorkspace: WorkspaceService = {
    ...workspace,
    async createTask(input) {
      creations += 1;
      return { ...sampleTask, title: input.title };
    },
  };
  const app = buildApp(config, {
    assistant,
    workspace: countedWorkspace,
    coordination: new MemoryCoordinationService(),
  });
  const request = {
    method: 'POST' as const,
    url: '/tasks',
    headers: { 'x-api-key': apiKey, 'idempotency-key': 'create-task-123' },
    payload: { title: 'Solo una vez' },
  };

  const first = await app.inject(request);
  const replay = await app.inject(request);

  assert.equal(first.statusCode, 201);
  assert.equal(replay.statusCode, 200);
  assert.equal(replay.headers['x-idempotent-replay'], 'true');
  assert.equal(replay.json().data.title, 'Solo una vez');
  assert.equal(creations, 1);
  await app.close();
});

test('el rate limit compartido devuelve retry-after', async () => {
  const limitedConfig: AppConfig = { ...config, RATE_LIMIT_MAX: 1 };
  const app = buildApp(limitedConfig, {
    assistant,
    workspace,
    coordination: new MemoryCoordinationService(),
  });

  const first = await app.inject({ method: 'GET', url: '/tasks/today', headers: { 'x-api-key': apiKey } });
  const limited = await app.inject({ method: 'GET', url: '/tasks/today', headers: { 'x-api-key': apiKey } });

  assert.equal(first.statusCode, 200);
  assert.equal(limited.statusCode, 429);
  assert.equal(limited.json().error.code, 'rate_limit_exceeded');
  assert.ok(Number(limited.headers['retry-after']) >= 1);
  await app.close();
});

test('el health check declara PostgreSQL y Redis no configurados en desarrollo', async () => {
  const app = createApp();
  const response = await app.inject({ method: 'GET', url: '/health' });
  assert.equal(response.statusCode, 200);
  assert.deepEqual(response.json().integrations.postgres, { configured: false, ok: false });
  assert.deepEqual(response.json().integrations.redis, { configured: false, ok: false });
  await app.close();
});

test('el bloqueo por tarea rechaza una operación concurrente y se libera después', async () => {
  const coordination = new MemoryCoordinationService();
  let release!: () => void;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  const first = coordination.withLock('notion-task:task-1', 1_000, async () => {
    await gate;
    return 'ok';
  });

  await assert.rejects(
    coordination.withLock('notion-task:task-1', 1_000, async () => 'duplicate'),
    (error: unknown) => error instanceof Error && error.message.includes('procesando'),
  );
  release();
  assert.equal(await first, 'ok');
  assert.equal(await coordination.withLock('notion-task:task-1', 1_000, async () => 'again'), 'again');
});

test('una aprobación se crea pendiente sin exponer el payload en el callback', async () => {
  const app = createApp();
  const response = await app.inject({
    method: 'POST',
    url: '/approvals',
    headers: { 'x-api-key': apiKey },
    payload: {
      telegramUserId: 6736438056,
      actionType: 'deploy.staging',
      summary: 'Desplegar Fastplay en staging',
      riskLevel: 3,
      payload: { service: 'fastplay', commit: 'abc123' },
    },
  });

  assert.equal(response.statusCode, 201);
  assert.equal(response.json().data.status, 'pending');
  assert.equal(response.json().data.telegramUserId, 6736438056);
  assert.match(response.json().data.id, /^[0-9a-f-]{36}$/);
  await app.close();
});

test('solo el usuario propietario puede aprobar y la decisión es de uso único', async () => {
  const app = createApp();
  const created = await app.inject({
    method: 'POST', url: '/approvals', headers: { 'x-api-key': apiKey },
    payload: { telegramUserId: 6736438056, actionType: 'service.restart', summary: 'Reiniciar servicio' },
  });
  const id = created.json().data.id as string;

  const wrongUser = await app.inject({
    method: 'POST', url: `/approvals/${id}/approve`, headers: { 'x-api-key': apiKey },
    payload: { telegramUserId: 1111111111 },
  });
  assert.equal(wrongUser.statusCode, 403);

  const approved = await app.inject({
    method: 'POST', url: `/approvals/${id}/approve`, headers: { 'x-api-key': apiKey },
    payload: { telegramUserId: 6736438056 },
  });
  assert.equal(approved.statusCode, 200);
  assert.equal(approved.json().data.status, 'approved');

  const repeated = await app.inject({
    method: 'POST', url: `/approvals/${id}/approve`, headers: { 'x-api-key': apiKey },
    payload: { telegramUserId: 6736438056 },
  });
  assert.equal(repeated.statusCode, 409);
  assert.equal(repeated.json().error.code, 'approval_invalid_status');
  await app.close();
});

test('una aprobación aprobada se consume una sola vez', async () => {
  const app = createApp();
  const created = await app.inject({
    method: 'POST', url: '/approvals', headers: { 'x-api-key': apiKey },
    payload: { telegramUserId: 6736438056, actionType: 'git.branch.create', summary: 'Crear rama segura' },
  });
  const id = created.json().data.id as string;
  await app.inject({
    method: 'POST', url: `/approvals/${id}/approve`, headers: { 'x-api-key': apiKey },
    payload: { telegramUserId: 6736438056 },
  });

  const used = await app.inject({
    method: 'POST', url: `/approvals/${id}/consume`, headers: { 'x-api-key': apiKey },
    payload: { telegramUserId: 6736438056 },
  });
  assert.equal(used.statusCode, 200);
  assert.equal(used.json().data.status, 'used');

  const repeated = await app.inject({
    method: 'POST', url: `/approvals/${id}/consume`, headers: { 'x-api-key': apiKey },
    payload: { telegramUserId: 6736438056 },
  });
  assert.equal(repeated.statusCode, 409);
  await app.close();
});

test('una aprobación puede rechazarse y ya no puede consumirse', async () => {
  const app = createApp();
  const created = await app.inject({
    method: 'POST', url: '/approvals', headers: { 'x-api-key': apiKey },
    payload: { telegramUserId: 6736438056, actionType: 'code.modify', summary: 'Modificar código' },
  });
  const id = created.json().data.id as string;
  const rejected = await app.inject({
    method: 'POST', url: `/approvals/${id}/reject`, headers: { 'x-api-key': apiKey },
    payload: { telegramUserId: 6736438056 },
  });
  assert.equal(rejected.statusCode, 200);
  assert.equal(rejected.json().data.status, 'rejected');

  const consume = await app.inject({
    method: 'POST', url: `/approvals/${id}/consume`, headers: { 'x-api-key': apiKey },
    payload: { telegramUserId: 6736438056 },
  });
  assert.equal(consume.statusCode, 409);
  await app.close();
});

test('no se crean aprobaciones para usuarios fuera de la lista blanca', async () => {
  const app = createApp();
  const response = await app.inject({
    method: 'POST', url: '/approvals', headers: { 'x-api-key': apiKey },
    payload: { telegramUserId: 9999999999, actionType: 'deploy.staging', summary: 'No autorizado' },
  });
  assert.equal(response.statusCode, 403);
  assert.equal(response.json().error.code, 'telegram_user_not_allowed');
  await app.close();
});

test('una aprobación caducada no puede aprobarse', async () => {
  let clock = new Date('2026-07-20T10:00:00.000Z');
  const app = buildApp(config, { assistant, workspace, now: () => clock });
  const created = await app.inject({
    method: 'POST', url: '/approvals', headers: { 'x-api-key': apiKey },
    payload: {
      telegramUserId: 6736438056,
      actionType: 'deploy.production',
      summary: 'Desplegar producción',
      riskLevel: 4,
      expiresInSeconds: 60,
    },
  });
  const id = created.json().data.id as string;
  clock = new Date('2026-07-20T10:01:01.000Z');

  const expired = await app.inject({
    method: 'POST', url: `/approvals/${id}/approve`, headers: { 'x-api-key': apiKey },
    payload: { telegramUserId: 6736438056 },
  });
  assert.equal(expired.statusCode, 410);
  assert.equal(expired.json().error.code, 'approval_expired');
  const read = await app.inject({ method: 'GET', url: `/approvals/${id}`, headers: { 'x-api-key': apiKey } });
  assert.equal(read.json().data.status, 'expired');
  await app.close();
});

