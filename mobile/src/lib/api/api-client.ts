// ABOUTME: Typed requests to the FastAPI backend: base URL, bearer token, a deadline per call,
// ABOUTME: one retry with a refreshed token on 401, and every failure thrown as an ApiError.

import { FetchTimeoutError, fetchWithTimeout } from '@/lib/utils/fetch-with-timeout';
import { ApiError, apiErrorFromResponse } from './api-error';

export const DEFAULT_TIMEOUT_MS = 15_000;

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

export interface RequestOptions {
  body?: unknown;
  timeoutMs?: number;
}

export interface ApiClientOptions {
  baseUrl: string | undefined;
  getAccessToken: () => Promise<string | null>;
  // Called once after a 401; returns the renewed token, or null when the session is gone.
  refreshAccessToken: () => Promise<string | null>;
  fetchImpl?: typeof fetch;
  defaultTimeoutMs?: number;
}

export interface ApiClient {
  request<T>(method: HttpMethod, path: string, options?: RequestOptions): Promise<T>;
}

export function createApiClient({
  baseUrl,
  getAccessToken,
  refreshAccessToken,
  fetchImpl = fetch,
  defaultTimeoutMs = DEFAULT_TIMEOUT_MS,
}: ApiClientOptions): ApiClient {
  async function send(method: HttpMethod, url: string, token: string | null, options: RequestOptions) {
    const headers: Record<string, string> = { Accept: 'application/json' };
    if (token) headers.Authorization = `Bearer ${token}`;
    if (options.body !== undefined) headers['Content-Type'] = 'application/json';
    const timeoutMs = options.timeoutMs ?? defaultTimeoutMs;
    try {
      return await fetchWithTimeout(
        fetchImpl,
        url,
        { method, headers, body: options.body === undefined ? undefined : JSON.stringify(options.body) },
        timeoutMs,
      );
    } catch (error) {
      if (error instanceof FetchTimeoutError) throw new ApiError({ category: 'timeout', retryable: true });
      throw new ApiError({ category: 'network', retryable: true });
    }
  }

  return {
    async request<T>(method: HttpMethod, path: string, options: RequestOptions = {}): Promise<T> {
      if (!baseUrl) throw new ApiError({ category: 'config_error' });
      const url = `${baseUrl.replace(/\/+$/, '')}${path}`;

      let response = await send(method, url, await getAccessToken(), options);
      if (response.status === 401) {
        const renewed = await refreshAccessToken();
        if (renewed) response = await send(method, url, renewed, options);
      }
      if (!response.ok) throw await apiErrorFromResponse(response);
      if (response.status === 204) return undefined as T;
      return (await response.json()) as T;
    },
  };
}
