import { ZodError } from 'zod';

export class ApiError extends Error {
  constructor(
    public readonly statusCode: number,
    public readonly code: string,
    message: string,
    public readonly details?: unknown,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export function validationError(error: ZodError): ApiError {
  return new ApiError(400, 'validation_error', 'La entrada no es válida.', error.issues);
}

export function upstreamError(service: string, status: number, payload: unknown): ApiError {
  const exposedStatus = status === 429 ? 429 : 502;
  return new ApiError(exposedStatus, `${service}_error`, `${service} no pudo completar la operación.`, {
    upstreamStatus: status,
    upstream: payload,
  });
}

export function conflictError(message: string): ApiError {
  return new ApiError(409, 'operation_in_progress', message);
}

