import type { AppConfig } from './config.js';
import { ApiError, upstreamError } from './errors.js';
import { CLOSED_TASK_STATES } from './schemas.js';
import type { CompleteTaskInput, CreateTaskInput, ListTasksQuery, UpdateTaskInput } from './schemas.js';
import type { Project, ProjectStatus, Task, WorkspaceService } from './types.js';

type JsonObject = Record<string, any>;

const propertyNames = {
  task: {
    title: 'Tarea',
    state: 'Estado',
    priority: 'Prioridad',
    area: 'Área',
    type: 'Tipo',
    origin: 'Origen',
    aiMode: 'Modo IA',
    needsApproval: 'Necesita aprobación',
    dueDate: 'Fecha límite',
    project: 'Proyecto',
    result: 'Resultado',
  },
  project: {
    title: 'Proyecto',
    state: 'Estado',
    priority: 'Prioridad',
    progress: 'Progreso',
    nextAction: 'Próxima acción',
    repository: 'Repositorio',
  },
} as const;

function richText(content: string): JsonObject {
  return { rich_text: content ? [{ type: 'text', text: { content } }] : [] };
}

function title(content: string): JsonObject {
  return { title: [{ type: 'text', text: { content } }] };
}

function textValue(property: JsonObject | undefined): string | null {
  if (!property) return null;
  const values = property.title ?? property.rich_text;
  if (!Array.isArray(values)) return null;
  const value = values.map((item: JsonObject) => item.plain_text ?? item.text?.content ?? '').join('');
  return value || null;
}

function selectValue(property: JsonObject | undefined): string | null {
  return property?.select?.name ?? property?.status?.name ?? null;
}

function numberValue(property: JsonObject | undefined): number | null {
  const value = property?.number ?? property?.formula?.number ?? property?.rollup?.number;
  return typeof value === 'number' ? value : null;
}

function relationValue(property: JsonObject | undefined): string[] {
  return Array.isArray(property?.relation)
    ? property.relation.map((item: JsonObject) => String(item.id)).filter(Boolean)
    : [];
}

function normalizeTask(page: JsonObject): Task {
  const p = page.properties ?? {};
  return {
    id: String(page.id),
    title: textValue(p[propertyNames.task.title]) ?? '(sin título)',
    state: selectValue(p[propertyNames.task.state]),
    priority: selectValue(p[propertyNames.task.priority]),
    area: selectValue(p[propertyNames.task.area]),
    type: selectValue(p[propertyNames.task.type]),
    origin: selectValue(p[propertyNames.task.origin]),
    aiMode: selectValue(p[propertyNames.task.aiMode]),
    needsApproval: Boolean(p[propertyNames.task.needsApproval]?.checkbox),
    dueDate: p[propertyNames.task.dueDate]?.date?.start ?? null,
    projectIds: relationValue(p[propertyNames.task.project]),
    result: textValue(p[propertyNames.task.result]),
    url: page.url ?? null,
    createdAt: page.created_time ?? null,
    updatedAt: page.last_edited_time ?? null,
  };
}

function normalizeProject(page: JsonObject): Project {
  const p = page.properties ?? {};
  return {
    id: String(page.id),
    name: textValue(p[propertyNames.project.title]) ?? '(sin nombre)',
    state: selectValue(p[propertyNames.project.state]),
    priority: selectValue(p[propertyNames.project.priority]),
    progress: numberValue(p[propertyNames.project.progress]),
    nextAction: textValue(p[propertyNames.project.nextAction]),
    repository: p[propertyNames.project.repository]?.url ?? textValue(p[propertyNames.project.repository]),
    url: page.url ?? null,
  };
}

const priorityRank = new Map([['P1', 1], ['P2', 2], ['P3', 3], ['P4', 4]]);

function rank(priority: string | null): number {
  return priorityRank.get(priority ?? '') ?? 9;
}

function byPriorityThenDueDate(a: Task, b: Task): number {
  return rank(a.priority) - rank(b.priority)
    || (a.dueDate ?? '9999-12-31').localeCompare(b.dueDate ?? '9999-12-31');
}

export class NotionWorkspaceService implements WorkspaceService {
  constructor(private readonly config: AppConfig) {}

  private assertConfigured(): string {
    if (!this.config.NOTION_API_TOKEN) {
      throw new ApiError(503, 'notion_not_configured', 'La integración con Notion no está configurada.');
    }
    return this.config.NOTION_API_TOKEN;
  }

  private async request(path: string, init: RequestInit = {}): Promise<JsonObject> {
    const token = this.assertConfigured();
    const response = await fetch(`https://api.notion.com/v1${path}`, {
      ...init,
      headers: {
        Authorization: `Bearer ${token}`,
        'Notion-Version': this.config.NOTION_API_VERSION,
        'Content-Type': 'application/json',
        ...init.headers,
      },
      signal: AbortSignal.timeout(20_000),
    });
    const payload = await response.json().catch(() => ({ message: response.statusText })) as JsonObject;
    if (!response.ok) throw upstreamError('notion', response.status, payload);
    return payload;
  }

  private async queryAll(dataSourceId: string, body: JsonObject = {}): Promise<JsonObject[]> {
    const results: JsonObject[] = [];
    let cursor: string | undefined;
    do {
      const payload = await this.request(`/data_sources/${dataSourceId}/query`, {
        method: 'POST',
        body: JSON.stringify({ ...body, page_size: 100, ...(cursor ? { start_cursor: cursor } : {}) }),
      });
      results.push(...(payload.results ?? []));
      cursor = payload.has_more && payload.next_cursor ? String(payload.next_cursor) : undefined;
    } while (cursor);
    return results;
  }

  async createTask(input: CreateTaskInput): Promise<Task> {
    const properties: JsonObject = {
      [propertyNames.task.title]: title(input.title),
      [propertyNames.task.state]: { select: { name: input.state } },
      [propertyNames.task.priority]: { select: { name: input.priority } },
      [propertyNames.task.area]: { select: { name: input.area } },
      [propertyNames.task.type]: { select: { name: input.type } },
      [propertyNames.task.origin]: { select: { name: input.origin } },
      [propertyNames.task.aiMode]: { select: { name: input.aiMode } },
      [propertyNames.task.needsApproval]: { checkbox: input.needsApproval },
    };
    if (input.dueDate !== undefined) properties[propertyNames.task.dueDate] = { date: input.dueDate ? { start: input.dueDate } : null };
    if (input.projectId !== undefined) properties[propertyNames.task.project] = { relation: input.projectId ? [{ id: input.projectId }] : [] };

    const page = await this.request('/pages', {
      method: 'POST',
      body: JSON.stringify({
        parent: { type: 'data_source_id', data_source_id: this.config.NOTION_TASKS_DATA_SOURCE_ID },
        properties,
      }),
    });
    return normalizeTask(page);
  }

  async listTasks(query: ListTasksQuery): Promise<Task[]> {
    const conditions: JsonObject[] = [];
    if (query.state) {
      conditions.push({ property: propertyNames.task.state, select: { equals: query.state } });
    } else if (!query.includeClosed) {
      for (const state of CLOSED_TASK_STATES) {
        conditions.push({ property: propertyNames.task.state, select: { does_not_equal: state } });
      }
    }
    if (query.projectId) {
      conditions.push({ property: propertyNames.task.project, relation: { contains: query.projectId } });
    }

    const pages = await this.queryAll(
      this.config.NOTION_TASKS_DATA_SOURCE_ID,
      conditions.length > 0 ? { filter: { and: conditions } } : {},
    );
    return pages.map(normalizeTask).sort(byPriorityThenDueDate);
  }

  async listToday(date: string): Promise<Task[]> {
    const tasks = await this.listTasks({ includeClosed: false });
    return tasks.filter((task) => task.state === 'En progreso'
      || (task.dueDate !== null && task.dueDate.slice(0, 10) <= date));
  }

  async updateTask(id: string, input: UpdateTaskInput): Promise<Task> {
    const properties: JsonObject = {};
    if (input.title !== undefined) properties[propertyNames.task.title] = title(input.title);
    if (input.state !== undefined) properties[propertyNames.task.state] = { select: { name: input.state } };
    if (input.priority !== undefined) properties[propertyNames.task.priority] = { select: { name: input.priority } };
    if (input.area !== undefined) properties[propertyNames.task.area] = { select: { name: input.area } };
    if (input.type !== undefined) properties[propertyNames.task.type] = { select: { name: input.type } };
    if (input.aiMode !== undefined) properties[propertyNames.task.aiMode] = { select: { name: input.aiMode } };
    if (input.needsApproval !== undefined) properties[propertyNames.task.needsApproval] = { checkbox: input.needsApproval };
    if (input.dueDate !== undefined) properties[propertyNames.task.dueDate] = { date: input.dueDate ? { start: input.dueDate } : null };
    if (input.projectId !== undefined) properties[propertyNames.task.project] = { relation: input.projectId ? [{ id: input.projectId }] : [] };
    if (input.result !== undefined) properties[propertyNames.task.result] = richText(input.result ?? '');

    const page = await this.request(`/pages/${encodeURIComponent(id)}`, {
      method: 'PATCH',
      body: JSON.stringify({ properties }),
    });
    return normalizeTask(page);
  }

  completeTask(id: string, input: CompleteTaskInput): Promise<Task> {
    return this.updateTask(id, {
      state: 'Hecha',
      ...(input.result !== undefined ? { result: input.result } : {}),
    });
  }

  async listProjects(): Promise<Project[]> {
    const pages = await this.queryAll(this.config.NOTION_PROJECTS_DATA_SOURCE_ID);
    return pages.map(normalizeProject).sort((a, b) =>
      rank(a.priority) - rank(b.priority) || a.name.localeCompare(b.name),
    );
  }

  async getProjectStatus(id: string): Promise<ProjectStatus> {
    const projectPage = await this.request(`/pages/${encodeURIComponent(id)}`);
    const tasks = (await this.queryAll(this.config.NOTION_TASKS_DATA_SOURCE_ID, {
      filter: { property: propertyNames.task.project, relation: { contains: id } },
    })).map(normalizeTask);
    const states = tasks.map((task) => task.state);
    return {
      project: normalizeProject(projectPage),
      tasks: {
        total: tasks.length,
        pending: states.filter((state) => !['En progreso', 'Bloqueada', 'Hecha', 'Cancelada'].includes(state ?? '')).length,
        inProgress: states.filter((state) => state === 'En progreso').length,
        blocked: states.filter((state) => state === 'Bloqueada').length,
        done: states.filter((state) => state === 'Hecha').length,
        cancelled: states.filter((state) => state === 'Cancelada').length,
      },
    };
  }
}

