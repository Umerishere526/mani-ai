// ABOUTME: Tests the API client against a fake fetch that records requests and answers from a
// ABOUTME: script — token handling, the 401 retry, the error shape, deadlines and offline.

import { createApiClient } from './api-client';
import { ApiError } from './api-error';

type Answer = Response | ((init: RequestInit) => Promise<Response>);

function fakeFetch(answers: Answer[]) {
  const calls: { url: string; init: RequestInit }[] = [];
  const impl = (async (url: string, init: RequestInit) => {
    calls.push({ url, init });
    const answer = answers.shift();
    if (!answer) throw new Error('no scripted answer');
    return typeof answer === 'function' ? answer(init) : answer;
  }) as unknown as typeof fetch;
  return { impl, calls };
}

function json(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

function client(fetchImpl: typeof fetch, refreshed: string | null = 'token-2') {
  const refreshes: number[] = [];
  const api = createApiClient({
    baseUrl: 'https://api.test/',
    getAccessToken: async () => 'token-1',
    refreshAccessToken: async () => {
      refreshes.push(1);
      return refreshed;
    },
    fetchImpl,
  });
  return { api, refreshes };
}

const header = (init: RequestInit, name: string) => (init.headers as Record<string, string>)[name];

it('sends the bearer token and a JSON body, and returns the parsed reply', async () => {
  const fetch = fakeFetch([json(200, { nickname: 'Sam' })]);
  const { api } = client(fetch.impl);

  const profile = await api.request<{ nickname: string }>('PUT', '/v1/profile', { body: { nickname: 'Sam' } });

  expect(profile.nickname).toBe('Sam');
  expect(fetch.calls[0].url).toBe('https://api.test/v1/profile');
  expect(header(fetch.calls[0].init, 'Authorization')).toBe('Bearer token-1');
  expect(fetch.calls[0].init.body).toBe('{"nickname":"Sam"}');
});

it('renews the token once on 401 and repeats the request with it', async () => {
  const fetch = fakeFetch([json(401, { error: { category: 'unauthenticated' } }), new Response(null, { status: 204 })]);
  const { api, refreshes } = client(fetch.impl);

  await expect(api.request('DELETE', '/v1/account')).resolves.toBeUndefined();

  expect(refreshes).toHaveLength(1);
  expect(header(fetch.calls[1].init, 'Authorization')).toBe('Bearer token-2');
});

it('surfaces a 401 when the session cannot be renewed', async () => {
  const fetch = fakeFetch([json(401, { error: { category: 'unauthenticated', message: 'Sign in again.' } })]);
  const { api } = client(fetch.impl, null);

  await expect(api.request('GET', '/v1/profile')).rejects.toMatchObject({ category: 'unauthenticated', status: 401 });
  expect(fetch.calls).toHaveLength(1);
});

it('turns the backend error body into an ApiError', async () => {
  const body = { error: { category: 'chat_paused', message: 'Chat is paused.', retryable: false, details: { until: 'x' } } };
  const { api } = client(fakeFetch([json(423, body)]).impl);

  const error = await api.request('POST', '/v1/threads').catch((e: unknown) => e);

  expect(error).toBeInstanceOf(ApiError);
  expect(error).toMatchObject({ category: 'chat_paused', status: 423, retryable: false, userMessage: 'Chat is paused.' });
  expect((error as ApiError).details).toEqual({ until: 'x' });
});

it('gives up on a request that outlives its deadline', async () => {
  const hang = (init: RequestInit) =>
    new Promise<Response>((_, reject) => init.signal?.addEventListener('abort', () => reject(new Error('aborted'))));
  const { api } = client(fakeFetch([hang]).impl);

  await expect(api.request('GET', '/v1/profile', { timeoutMs: 5 })).rejects.toMatchObject({
    category: 'timeout',
    retryable: true,
  });
});

it('reports an unreachable backend as a retryable network error', async () => {
  const offline = async () => {
    throw new TypeError('Network request failed');
  };
  const { api } = client(fakeFetch([offline]).impl);

  await expect(api.request('GET', '/v1/profile')).rejects.toMatchObject({ category: 'network', retryable: true });
});
