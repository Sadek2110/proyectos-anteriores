import { randomUUID } from 'node:crypto';
import type { Pool, PoolClient } from 'pg';
import type { CreateApprovalInput } from './schemas.js';
import { ApiError } from './errors.js';
import type { Approval, ApprovalService, ApprovalStatus } from './types.js';

type Decision = 'approved' | 'rejected';

interface ApprovalRow {
  id: string;
  telegram_user_id: string;
  action_type: string;
  summary: string;
  risk_level: number;
  payload: Record<string, unknown>;
  status: ApprovalStatus;
  expires_at: Date;
  approved_at: Date | null;
  rejected_at: Date | null;
  used_at: Date | null;
  created_at: Date;
  updated_at: Date;
}

function forbiddenUser(): ApiError {
  return new ApiError(403, 'telegram_user_not_allowed', 'El usuario de Telegram no está autorizado.');
}

function notFound(): ApiError {
  return new ApiError(404, 'approval_not_found', 'La aprobación no existe.');
}

function expired(): ApiError {
  return new ApiError(410, 'approval_expired', 'La aprobación ha caducado.');
}

function invalidStatus(status: ApprovalStatus, expected: ApprovalStatus): ApiError {
  return new ApiError(409, 'approval_invalid_status', `La aprobación está en estado ${status}; se esperaba ${expected}.`);
}

function mapApproval(row: ApprovalRow): Approval {
  return {
    id: row.id,
    telegramUserId: Number(row.telegram_user_id),
    actionType: row.action_type,
    summary: row.summary,
    riskLevel: row.risk_level as 3 | 4,
    payload: row.payload,
    status: row.status,
    expiresAt: row.expires_at.toISOString(),
    approvedAt: row.approved_at?.toISOString() ?? null,
    rejectedAt: row.rejected_at?.toISOString() ?? null,
    usedAt: row.used_at?.toISOString() ?? null,
    createdAt: row.created_at.toISOString(),
    updatedAt: row.updated_at.toISOString(),
  };
}

function assertOwner(approval: Approval, telegramUserId: number): void {
  if (approval.telegramUserId !== telegramUserId) throw forbiddenUser();
}

export class MemoryApprovalService implements ApprovalService {
  private readonly records = new Map<string, Approval>();
  private readonly allowedUsers: Set<number>;

  constructor(
    allowedUsers: number[],
    private readonly now: () => Date = () => new Date(),
  ) {
    this.allowedUsers = new Set(allowedUsers);
  }

  private assertAllowed(telegramUserId: number): void {
    if (!this.allowedUsers.has(telegramUserId)) throw forbiddenUser();
  }

  private refresh(record: Approval): Approval {
    if ((record.status === 'pending' || record.status === 'approved') && Date.parse(record.expiresAt) <= this.now().getTime()) {
      record.status = 'expired';
      record.updatedAt = this.now().toISOString();
    }
    return record;
  }

  async create(input: CreateApprovalInput, ttlSeconds: number): Promise<Approval> {
    this.assertAllowed(input.telegramUserId);
    const createdAt = this.now();
    const approval: Approval = {
      id: randomUUID(),
      telegramUserId: input.telegramUserId,
      actionType: input.actionType,
      summary: input.summary,
      riskLevel: input.riskLevel,
      payload: input.payload,
      status: 'pending',
      expiresAt: new Date(createdAt.getTime() + (input.expiresInSeconds ?? ttlSeconds) * 1_000).toISOString(),
      approvedAt: null,
      rejectedAt: null,
      usedAt: null,
      createdAt: createdAt.toISOString(),
      updatedAt: createdAt.toISOString(),
    };
    this.records.set(approval.id, approval);
    return structuredClone(approval);
  }

  async get(id: string): Promise<Approval> {
    const record = this.records.get(id);
    if (!record) throw notFound();
    return structuredClone(this.refresh(record));
  }

  async approve(id: string, telegramUserId: number): Promise<Approval> {
    return this.decide(id, telegramUserId, 'approved');
  }

  async reject(id: string, telegramUserId: number): Promise<Approval> {
    return this.decide(id, telegramUserId, 'rejected');
  }

  private async decide(id: string, telegramUserId: number, decision: Decision): Promise<Approval> {
    this.assertAllowed(telegramUserId);
    const approval = await this.get(id);
    assertOwner(approval, telegramUserId);
    if (approval.status === 'expired') throw expired();
    if (approval.status !== 'pending') throw invalidStatus(approval.status, 'pending');
    const decidedAt = this.now().toISOString();
    approval.status = decision;
    approval.updatedAt = decidedAt;
    if (decision === 'approved') approval.approvedAt = decidedAt;
    else approval.rejectedAt = decidedAt;
    this.records.set(id, approval);
    return structuredClone(approval);
  }

  async consume(id: string, telegramUserId: number): Promise<Approval> {
    this.assertAllowed(telegramUserId);
    const approval = await this.get(id);
    assertOwner(approval, telegramUserId);
    if (approval.status === 'expired') throw expired();
    if (approval.status !== 'approved') throw invalidStatus(approval.status, 'approved');
    approval.status = 'used';
    approval.usedAt = this.now().toISOString();
    approval.updatedAt = approval.usedAt;
    this.records.set(id, approval);
    return structuredClone(approval);
  }
}

export class PostgresApprovalService implements ApprovalService {
  private readonly allowedUsers: Set<number>;

  constructor(
    private readonly pool: Pool,
    allowedUsers: number[],
    private readonly now: () => Date = () => new Date(),
  ) {
    this.allowedUsers = new Set(allowedUsers);
  }

  private assertAllowed(telegramUserId: number): void {
    if (!this.allowedUsers.has(telegramUserId)) throw forbiddenUser();
  }

  private async audit(
    client: PoolClient,
    actor: string,
    action: string,
    approval: Approval,
  ): Promise<void> {
    await client.query(
      `INSERT INTO audit_logs (actor, action, resource_type, resource_id, metadata)
       VALUES ($1, $2, 'approval', $3, $4::jsonb)`,
      [actor, action, approval.id, JSON.stringify({
        actionType: approval.actionType,
        riskLevel: approval.riskLevel,
        status: approval.status,
      })],
    );
  }

  async create(input: CreateApprovalInput, ttlSeconds: number): Promise<Approval> {
    this.assertAllowed(input.telegramUserId);
    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');
      const userId = `telegram:${input.telegramUserId}`;
      const userResult = await client.query<{ id: string }>(
        `INSERT INTO users (id, telegram_user_id, name, role)
         VALUES ($1, $2, $3, 'owner')
         ON CONFLICT (telegram_user_id) DO UPDATE SET updated_at = NOW()
         RETURNING id`,
        [userId, input.telegramUserId, `Telegram ${input.telegramUserId}`],
      );
      const persistedUserId = userResult.rows[0]?.id;
      if (!persistedUserId) throw new Error('No se pudo resolver el usuario de la aprobación.');
      const id = randomUUID();
      const expiresAt = new Date(this.now().getTime() + (input.expiresInSeconds ?? ttlSeconds) * 1_000);
      const result = await client.query<ApprovalRow>(
        `INSERT INTO approvals (id, user_id, action_type, summary, risk_level, payload, status, expires_at)
         VALUES ($1, $2, $3, $4, $5, $6::jsonb, 'pending', $7)
         RETURNING id, $8::bigint AS telegram_user_id, action_type, summary, risk_level, payload, status,
                   expires_at, approved_at, rejected_at, used_at, created_at, updated_at`,
        [id, persistedUserId, input.actionType, input.summary, input.riskLevel, JSON.stringify(input.payload), expiresAt, input.telegramUserId],
      );
      const row = result.rows[0];
      if (!row) throw new Error('No se pudo crear la aprobación.');
      const approval = mapApproval(row);
      await this.audit(client, `telegram:${input.telegramUserId}`, 'approval.create', approval);
      await client.query('COMMIT');
      return approval;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async get(id: string): Promise<Approval> {
    await this.pool.query(
      `UPDATE approvals
       SET status = 'expired', updated_at = NOW()
       WHERE id = $1 AND status IN ('pending', 'approved') AND expires_at <= NOW()`,
      [id],
    );
    const result = await this.pool.query<ApprovalRow>(
      `SELECT a.id, u.telegram_user_id, a.action_type, a.summary, a.risk_level, a.payload, a.status,
              a.expires_at, a.approved_at, a.rejected_at, a.used_at, a.created_at, a.updated_at
       FROM approvals a
       JOIN users u ON u.id = a.user_id
       WHERE a.id = $1`,
      [id],
    );
    const row = result.rows[0];
    if (!row) throw notFound();
    return mapApproval(row);
  }

  async approve(id: string, telegramUserId: number): Promise<Approval> {
    return this.decide(id, telegramUserId, 'approved');
  }

  async reject(id: string, telegramUserId: number): Promise<Approval> {
    return this.decide(id, telegramUserId, 'rejected');
  }

  private async decide(id: string, telegramUserId: number, decision: Decision): Promise<Approval> {
    this.assertAllowed(telegramUserId);
    const client = await this.pool.connect();
    let errorAfterCommit: ApiError | undefined;
    try {
      await client.query('BEGIN');
      const result = await client.query<ApprovalRow>(
        `SELECT a.id, u.telegram_user_id, a.action_type, a.summary, a.risk_level, a.payload, a.status,
                a.expires_at, a.approved_at, a.rejected_at, a.used_at, a.created_at, a.updated_at
         FROM approvals a
         JOIN users u ON u.id = a.user_id
         WHERE a.id = $1
         FOR UPDATE OF a`,
        [id],
      );
      const row = result.rows[0];
      if (!row) throw notFound();
      let approval = mapApproval(row);
      assertOwner(approval, telegramUserId);

      if ((approval.status === 'pending' || approval.status === 'approved') && approval.expiresAt <= this.now().toISOString()) {
        const expiredResult = await client.query<ApprovalRow>(
          `UPDATE approvals SET status = 'expired', updated_at = NOW()
           WHERE id = $1
           RETURNING id, $2::bigint AS telegram_user_id, action_type, summary, risk_level, payload, status,
                     expires_at, approved_at, rejected_at, used_at, created_at, updated_at`,
          [id, telegramUserId],
        );
        const expiredRow = expiredResult.rows[0];
        if (!expiredRow) throw notFound();
        approval = mapApproval(expiredRow);
        await this.audit(client, `telegram:${telegramUserId}`, 'approval.expire', approval);
        errorAfterCommit = expired();
      } else if (approval.status !== 'pending') {
        throw invalidStatus(approval.status, 'pending');
      } else {
        const timestampColumn = decision === 'approved' ? 'approved_at' : 'rejected_at';
        const updated = await client.query<ApprovalRow>(
          `UPDATE approvals SET status = $2, ${timestampColumn} = NOW(), updated_at = NOW()
           WHERE id = $1
           RETURNING id, $3::bigint AS telegram_user_id, action_type, summary, risk_level, payload, status,
                     expires_at, approved_at, rejected_at, used_at, created_at, updated_at`,
          [id, decision, telegramUserId],
        );
        const updatedRow = updated.rows[0];
        if (!updatedRow) throw notFound();
        approval = mapApproval(updatedRow);
        await this.audit(client, `telegram:${telegramUserId}`, `approval.${decision}`, approval);
      }
      await client.query('COMMIT');
      if (errorAfterCommit) throw errorAfterCommit;
      return approval;
    } catch (error) {
      if (!errorAfterCommit) await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async consume(id: string, telegramUserId: number): Promise<Approval> {
    this.assertAllowed(telegramUserId);
    const client = await this.pool.connect();
    let errorAfterCommit: ApiError | undefined;
    try {
      await client.query('BEGIN');
      const result = await client.query<ApprovalRow>(
        `SELECT a.id, u.telegram_user_id, a.action_type, a.summary, a.risk_level, a.payload, a.status,
                a.expires_at, a.approved_at, a.rejected_at, a.used_at, a.created_at, a.updated_at
         FROM approvals a
         JOIN users u ON u.id = a.user_id
         WHERE a.id = $1
         FOR UPDATE OF a`,
        [id],
      );
      const row = result.rows[0];
      if (!row) throw notFound();
      let approval = mapApproval(row);
      assertOwner(approval, telegramUserId);

      if (approval.status === 'approved' && approval.expiresAt <= this.now().toISOString()) {
        const expiredResult = await client.query<ApprovalRow>(
          `UPDATE approvals SET status = 'expired', updated_at = NOW()
           WHERE id = $1
           RETURNING id, $2::bigint AS telegram_user_id, action_type, summary, risk_level, payload, status,
                     expires_at, approved_at, rejected_at, used_at, created_at, updated_at`,
          [id, telegramUserId],
        );
        const expiredRow = expiredResult.rows[0];
        if (!expiredRow) throw notFound();
        approval = mapApproval(expiredRow);
        await this.audit(client, `telegram:${telegramUserId}`, 'approval.expire', approval);
        errorAfterCommit = expired();
      } else if (approval.status !== 'approved') {
        throw invalidStatus(approval.status, 'approved');
      } else {
        const updated = await client.query<ApprovalRow>(
          `UPDATE approvals SET status = 'used', used_at = NOW(), updated_at = NOW()
           WHERE id = $1
           RETURNING id, $2::bigint AS telegram_user_id, action_type, summary, risk_level, payload, status,
                     expires_at, approved_at, rejected_at, used_at, created_at, updated_at`,
          [id, telegramUserId],
        );
        const updatedRow = updated.rows[0];
        if (!updatedRow) throw notFound();
        approval = mapApproval(updatedRow);
        await this.audit(client, `telegram:${telegramUserId}`, 'approval.consume', approval);
      }
      await client.query('COMMIT');
      if (errorAfterCommit) throw errorAfterCommit;
      return approval;
    } catch (error) {
      if (!errorAfterCommit) await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }
}
