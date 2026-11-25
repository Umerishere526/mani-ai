// ABOUTME: Picks the sentence to show for a failed auth or backend call: the backend's own
// ABOUTME: safe sentence when it sent one, else a dictionary line for the kind of failure.

import en from '@/dictionaries/en.json';
import { ApiError } from '@/lib/api/api-error';
import { AuthError, type AuthErrorCode } from '@/lib/auth/session';

const AUTH_MESSAGES: Partial<Record<AuthErrorCode, string>> = {
  invalid_credentials: en.errors.invalidCredentials,
  email_not_confirmed: en.errors.emailNotConfirmed,
  user_already_exists: en.errors.userAlreadyExists,
  weak_password: en.errors.weakPassword,
  rate_limited: en.errors.rateLimited,
  network: en.errors.network,
};

export function errorMessage(error: unknown): string {
  if (error instanceof AuthError) return AUTH_MESSAGES[error.code] ?? en.common.error;
  if (error instanceof ApiError) {
    if (error.category === 'network') return en.errors.network;
    if (error.category === 'timeout') return en.errors.timeout;
    return error.userMessage ?? en.common.error;
  }
  return en.common.error;
}
