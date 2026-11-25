// ABOUTME: The one error shape every backend failure arrives in ({ error: { category, message,
// ABOUTME: retryable, details } }), plus the client-side failures (offline, timeout, no config).

export type ApiErrorCategory =
  | 'rate_limited'
  | 'llm_unavailable'
  | 'llm_timeout'
  | 'storage_error'
  | 'auth_provider_error'
  | 'config_error'
  | 'not_found'
  | 'invalid_request'
  | 'conflict'
  | 'busy'
  | 'unauthenticated'
  | 'forbidden'
  | 'chat_paused'
  | 'unknown'
  | 'network'
  | 'timeout';

export class ApiError extends Error {
  readonly category: ApiErrorCategory;
  readonly status: number | null;
  readonly retryable: boolean;
  // The backend's sentence, safe to show; null when the failure never reached the backend.
  readonly userMessage: string | null;
  readonly details: Record<string, unknown> | null;

  constructor(init: {
    category: ApiErrorCategory;
    status?: number | null;
    retryable?: boolean;
    userMessage?: string | null;
    details?: Record<string, unknown> | null;
  }) {
    super(init.userMessage ?? init.category);
    this.name = 'ApiError';
    this.category = init.category;
    this.status = init.status ?? null;
    this.retryable = init.retryable ?? false;
    this.userMessage = init.userMessage ?? null;
    this.details = init.details ?? null;
  }
}

interface ErrorBody {
  error?: {
    category?: ApiErrorCategory;
    message?: string;
    retryable?: boolean;
    details?: Record<string, unknown>;
  };
}

export async function apiErrorFromResponse(response: Response): Promise<ApiError> {
  const body = (await response.json().catch(() => null)) as ErrorBody | null;
  return new ApiError({
    category: body?.error?.category ?? 'unknown',
    status: response.status,
    retryable: body?.error?.retryable ?? response.status >= 500,
    userMessage: body?.error?.message ?? null,
    details: body?.error?.details ?? null,
  });
}
