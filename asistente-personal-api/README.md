# Asistente Personal API

API privada del Asistente Personal. Centraliza validación, autenticación, límites, trazabilidad y acceso a Notion/OpenCode; n8n sigue encargado de Telegram, horarios y automatizaciones. PostgreSQL conserva conversaciones, ejecuciones y auditoría; Redis aporta rate limiting compartido, idempotencia y bloqueos.

## Endpoints

- `GET /health` — público, para EasyPanel.
- `POST /assistant/message` — conversación de solo lectura mediante OpenCode Go.
- `POST /tasks` — crear tarea en Notion.
- `GET /tasks` — listar tareas. Filtros opcionales: `state`, `projectId` e `includeClosed`.
- `GET /tasks/today` — tareas vencidas/de hoy y tareas en progreso.
- `PATCH /tasks/:id` — actualizar una tarea.
- `POST /tasks/:id/complete` — completar una tarea.
- `GET /projects` — listar proyectos.
- `GET /projects/:id/status` — proyecto y conteos de tareas.
- `POST /approvals` — crear una solicitud persistente para un usuario autorizado de Telegram.
- `GET /approvals/:id` — consultar estado y payload almacenado en servidor.
- `POST /approvals/:id/approve` — aprobar una solicitud pendiente y vigente.
- `POST /approvals/:id/reject` — rechazar una solicitud pendiente y vigente.
- `POST /approvals/:id/consume` — consumir una aprobación aceptada una sola vez.

Salvo `/health`, todos requieren `Authorization: Bearer <INTERNAL_API_KEY>` o `x-api-key: <INTERNAL_API_KEY>`.

## Desarrollo local

Requisitos: Node.js 22 o superior.

```bash
cp .env.example .env
npm install
npm run dev
```

Comprobaciones:

```bash
npm test
npm run typecheck
```

## PostgreSQL y Redis

La API funciona sin ambos servicios durante desarrollo, usando coordinación en memoria y persistencia nula. En producción configura `DATABASE_URL` y `REDIS_URL`.

Las migraciones son explícitas y nunca se ejecutan al arrancar:

```bash
npm run migrate
```

La primera migración crea `users`, `conversations`, `messages`, `executions`, `approvals`, `audit_logs` y `external_links`. Las operaciones mutables aceptan `Idempotency-Key`; una repetición completada devuelve el resultado anterior y la cabecera `x-idempotent-replay: true`.

La segunda migración completa el sistema de aprobaciones. Cada solicitud pertenece a un ID incluido en `TELEGRAM_ALLOWED_USER_IDS`, caduca según `APPROVAL_TTL_SEC`, guarda el payload solo en PostgreSQL y recorre `pending → approved/rejected/expired → used`. Aprobar, rechazar y consumir son transacciones bloqueadas; una aprobación no puede decidirse o utilizarse dos veces.

## Docker / EasyPanel

El repositorio incluye un `Dockerfile` multi-stage. En EasyPanel, crea una App desde GitHub y usa:

- Build method: Dockerfile.
- Dockerfile: `Dockerfile`.
- Puerto: `3000`.
- Health check: `GET /health` (incluye estado de PostgreSQL y Redis).
- Variables: las descritas en `.env.example`.

No copies `.env` al repositorio. `INTERNAL_API_KEY`, `NOTION_API_TOKEN` y las credenciales de OpenCode deben configurarse como secretos en EasyPanel.

