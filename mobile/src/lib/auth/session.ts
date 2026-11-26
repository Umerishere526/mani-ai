// ABOUTME: The signed-in session the app keeps, and the auth service contract it is
// ABOUTME: obtained from — sign up, sign in, refresh, sign out — as plain types.

export interface Session {
  accessToken: string;
  refreshToken: string;
  // Seconds since the epoch, as GoTrue reports it.
  expiresAt: number;
  user: { id: string; email: string | null };
}

export type AuthErrorCode =
  | 'invalid_credentials'
  | 'email_not_confirmed'
  | 'user_already_exists'
  | 'weak_password'
  | 'session_expired'
  | 'rate_limited'
  | 'network'
  | 'config'
  | 'unknown';

export class AuthError extends Error {
  readonly code: AuthErrorCode;

  constructor(code: AuthErrorCode, message?: string) {
    super(message ?? code);
    this.name = 'AuthError';
    this.code = code;
  }
}

export interface AuthService {
  // Null when the account was created but its email must be confirmed before signing in.
  signUp(email: string, password: string): Promise<Session | null>;
  signIn(email: string, password: string): Promise<Session>;
  refresh(refreshToken: string): Promise<Session>;
  signOut(accessToken: string): Promise<void>;
}
