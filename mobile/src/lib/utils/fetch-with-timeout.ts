// ABOUTME: fetch with a deadline: aborts the request once timeoutMs passes and rejects with
// ABOUTME: FetchTimeoutError, so callers can tell a slow server from an unreachable one.

export class FetchTimeoutError extends Error {
  constructor(timeoutMs: number) {
    super(`request timed out after ${timeoutMs} ms`);
    this.name = 'FetchTimeoutError';
  }
}

export async function fetchWithTimeout(
  fetchImpl: typeof fetch,
  url: string,
  init: RequestInit,
  timeoutMs: number,
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetchImpl(url, { ...init, signal: controller.signal });
  } catch (error) {
    if (controller.signal.aborted) throw new FetchTimeoutError(timeoutMs);
    throw error;
  } finally {
    clearTimeout(timer);
  }
}
