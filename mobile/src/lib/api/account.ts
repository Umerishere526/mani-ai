// ABOUTME: Account deletion: the backend removes the auth user, and every table the person
// ABOUTME: owns cascades from it.

import { api } from './index';

export function deleteAccount(): Promise<void> {
  return api.request<void>('DELETE', '/v1/account');
}
