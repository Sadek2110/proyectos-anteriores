import type {
  CompleteTaskInput,
  CreateApprovalInput,
  CreateTaskInput,
  ListTasksQuery,
  MessageInput,
  UpdateTaskInput,
} from './schemas.js';

export interface Task {
  id: string;
  title: string;
  state: string | null;
  priority: string | null;
  area: string | null;
  type: string | null;
  origin: string | null;
  aiMode: string | null;
  needsApproval: boolean;
  dueDate: string | null;
  projectIds: string[];
  result: string | null;
  url: string | null;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface Project {
  id: string;
  name: string;
  state: string | null;
  priority: string | null;
  progress: number | null;
  nextAction: string | null;
  repository: string | null;
  url: string | null;
}

export interface ProjectStatus {
  project: Project;
  tasks: {
    total: number;
    pending: number;
    inProgress: number;
    blocked: number;
    done: number;
    cancelled: number;
  };
}

export interface AssistantReply {
  message: string;
  sessionId: string;
  providerId: string;
  modelId: string;
}

export interface AssistantService {
  message(input: MessageInput): Promise<AssistantReply>;
}

export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'expired' | 'used';

export interface Approval {
  id: string;
  telegramUserId: number;
  actionType: string;
  summary: string;
  riskLevel: 3 | 4;
  payload: Record<string, unknown>;
  status: ApprovalStatus;
  expiresAt: string;
  approvedAt: string | null;
  rejectedAt: string | null;
  usedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ApprovalService {
  create(input: CreateApprovalInput, ttlSeconds: number): Promise<Approval>;
  get(id: string): Promise<Approval>;
  approve(id: string, telegramUserId: number): Promise<Approval>;
  reject(id: string, telegramUserId: number): Promise<Approval>;
  consume(id: string, telegramUserId: number): Promise<Approval>;
}

export interface WorkspaceService {
  createTask(input: CreateTaskInput): Promise<Task>;
  listTasks(query: ListTasksQuery): Promise<Task[]>;
  listToday(date: string): Promise<Task[]>;
  updateTask(id: string, input: UpdateTaskInput): Promise<Task>;
  completeTask(id: string, input: CompleteTaskInput): Promise<Task>;
  listProjects(): Promise<Project[]>;
  getProjectStatus(id: string): Promise<ProjectStatus>;
}

export interface RateLimitResult {
  allowed: boolean;
  retryAfterSeconds: number;
}

export interface CoordinationService {
  ping(): Promise<boolean>;
  consumeRateLimit(key: string, limit: number, windowMs: number): Promise<RateLimitResult>;
  withLock<T>(key: string, ttlMs: number, operation: () => Promise<T>): Promise<T>;
  runIdempotent<T>(key: string | undefined, ttlSeconds: number, operation: () => Promise<T>): Promise<{
    value: T;
    replayed: boolean;
  }>;
  close(): Promise<void>;
}

export interface AuditRecord {
  actor: string;
  action: string;
  resourceType: string;
  resourceId?: string;
  metadata?: Record<string, unknown>;
}

export interface ExecutionRecord {
  requestId: string;
  taskPageId?: string;
  action: string;
  idempotencyKey?: string;
}

export interface ConversationRecord {
  conversationId: string;
  input: string;
  output: string;
  intent?: string;
}

export interface PersistenceService {
  ping(): Promise<boolean>;
  recordAudit(record: AuditRecord): Promise<void>;
  startExecution(record: ExecutionRecord): Promise<string>;
  finishExecution(id: string, status: 'success' | 'error', result?: unknown, error?: unknown): Promise<void>;
  recordConversation(record: ConversationRecord): Promise<void>;
  close(): Promise<void>;
}

