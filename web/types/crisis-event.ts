// ABOUTME: Types for the admin Crisis events section — one flagged moment in a conversation.
// ABOUTME: The shape the backend's /v1/admin/crisis-events endpoint returns, in camelCase.

export interface CrisisEvent {
  id: string;
  threadId: string;
  userId: string;
  reason: string;
  detectedAt: string;
  resolution: string | null;
  resolvedAt: string | null;
}
