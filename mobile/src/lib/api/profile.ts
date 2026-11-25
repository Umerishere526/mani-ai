// ABOUTME: The onboarding profile routes: read it, and save the nickname and default
// ABOUTME: conversation style chosen at onboarding.

import type { ProfileIn, ProfileOut } from '@/types/api';
import { api } from './index';

export function getProfile(): Promise<ProfileOut> {
  return api.request<ProfileOut>('GET', '/v1/profile');
}

export function updateProfile(profile: ProfileIn): Promise<ProfileOut> {
  return api.request<ProfileOut>('PUT', '/v1/profile', { body: profile });
}
