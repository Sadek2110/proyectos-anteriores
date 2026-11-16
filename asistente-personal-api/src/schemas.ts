import { z } from 'zod';

const isoDate = /^\d{4}-\d{2}-\d{2}$/;
const taskId = z.string().min(1).max(100);
const telegramUserId = z.coerce.number().int().positive();

export const TASK_STATES = [
  'Bandeja',
  'Próxima',
  'En progreso',
  'Esperando',
  'Bloqueada',
  'Hecha',
  'Cancelada',
] as const;

export const CLOSED_TASK_STATES = ['Hecha', 'Cancelada'] as const;

const taskState = z.enum(TASK_STATES);

export const messageSchema = z.object({
  message: z.string().trim().min(1).max(20_000),
  context: z.record(z.string(), z.unknown()).optional(),
});

export const createTaskSchema = z.object({
  title: z.string().trim().min(1).max(200),
  state: taskState.default('Próxima'),
  priority: z.enum(['P1', 'P2', 'P3', 'P4']).default('P3'),
  area: z.string().trim().min(1).max(100).default('Personal'),
  type: z.string().trim().min(1).max(100).default('Tarea'),
  origin: z.string().trim().min(1).max(100).default('API'),
  aiMode: z.enum(['Ninguno', 'Planificar', 'Analizar']).default('Ninguno'),
  needsApproval: z.boolean().default(false),
  dueDate: z.string().regex(isoDate, 'dueDate debe usar YYYY-MM-DD').nullable().optional(),
  projectId: z.string().uuid().nullable().optional(),
});

export const updateTaskSchema = z.object({
  title: z.string().trim().min(1).max(200).optional(),
  state: taskState.optional(),
  priority: z.enum(['P1', 'P2', 'P3', 'P4']).optional(),
  area: z.string().trim().min(1).max(100).optional(),
  type: z.string().trim().min(1).max(100).optional(),
  aiMode: z.enum(['Ninguno', 'Planificar', 'Analizar']).optional(),
  needsApproval: z.boolean().optional(),
  dueDate: z.string().regex(isoDate, 'dueDate debe usar YYYY-MM-DD').nullable().optional(),
  projectId: z.string().uuid().nullable().optional(),
  result: z.string().max(2_000).nullable().optional(),
}).refine((value) => Object.keys(value).length > 0, 'Debes enviar al menos un campo.');

export const completeTaskSchema = z.object({
  result: z.string().trim().max(2_000).optional(),
});

export const listTasksQuerySchema = z.object({
  state: taskState.optional(),
  projectId: z.string().uuid().optional(),
  includeClosed: z.enum(['true', 'false']).optional().transform((value) => value === 'true'),
});

export const taskParamsSchema = z.object({ id: taskId });
export const projectParamsSchema = z.object({ id: taskId });

export const createApprovalSchema = z.object({
  telegramUserId,
  actionType: z.string().trim().min(3).max(100).regex(
    /^[a-z][a-z0-9_.-]+$/,
    'actionType debe ser un identificador estable como deploy.staging',
  ),
  summary: z.string().trim().min(1).max(500),
  riskLevel: z.union([z.literal(3), z.literal(4)]).default(3),
  payload: z.record(z.string(), z.unknown()).default({}),
  expiresInSeconds: z.number().int().min(60).max(86_400).optional(),
});

export const approvalParamsSchema = z.object({ id: z.string().uuid() });
export const approvalDecisionSchema = z.object({ telegramUserId });

export type MessageInput = z.infer<typeof messageSchema>;
export type CreateTaskInput = z.infer<typeof createTaskSchema>;
export type UpdateTaskInput = z.infer<typeof updateTaskSchema>;
export type ListTasksQuery = z.infer<typeof listTasksQuerySchema>;
export type CompleteTaskInput = z.infer<typeof completeTaskSchema>;
export type CreateApprovalInput = z.infer<typeof createApprovalSchema>;

