// ABOUTME: Tests how GoTrue's REST replies become sessions and AuthError codes, using a fake
// ABOUTME: fetch that answers the way GoTrue does for each case.

import { createGoTrueAuth } from './gotrue';

function answering(status: number, body: unknown) {
  return (async () => new Response(JSON.stringify(body), { status })) as unknown as typeof fetch;
}

function gotrue(fetchImpl: typeof fetch) {
  return createGoTrueAuth({ url: 'https://x.supabase.co', publishableKey: 'pk', fetchImpl });
}

it('returns no session for a sign-up that waits on email confirmation', async () => {
  const auth = gotrue(answering(200, { id: 'u1', email: 'a@b.co', confirmation_sent_at: 'now' }));

  await expect(auth.signUp('a@b.co', 'password1')).resolves.toBeNull();
});

it('reads a password sign-in into a session', async () => {
  const body = { access_token: 'at', refresh_token: 'rt', expires_at: 123, user: { id: 'u1', email: 'a@b.co' } };

  await expect(gotrue(answering(200, body)).signIn('a@b.co', 'pw')).resolves.toEqual({
    accessToken: 'at',
    refreshToken: 'rt',
    expiresAt: 123,
    user: { id: 'u1', email: 'a@b.co' },
  });
});

it.each([
  [{ error_code: 'invalid_credentials', msg: 'Invalid login credentials' }, 'invalid_credentials'],
  [{ error: 'invalid_grant', error_description: 'Invalid login credentials' }, 'invalid_credentials'],
  [{ error_code: 'refresh_token_not_found' }, 'session_expired'],
  [{ error_code: 'email_not_confirmed' }, 'email_not_confirmed'],
])('maps the GoTrue error %j to %s', async (body, code) => {
  await expect(gotrue(answering(400, body)).signIn('a@b.co', 'pw')).rejects.toMatchObject({ code });
});

it('refuses to call without its configuration', async () => {
  const auth = createGoTrueAuth({ url: undefined, publishableKey: 'pk' });

  await expect(auth.signIn('a@b.co', 'pw')).rejects.toMatchObject({ code: 'config' });
});
