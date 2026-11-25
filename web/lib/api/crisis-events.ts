// ABOUTME: Reads the crisis events no admin has resolved yet, for the admin Crisis events page.
// ABOUTME: Newest first; the backend caps the list at 200.

import type { CrisisEvent } from "@/types";
import { adminFetch } from "./admin-fetch";

interface CrisisEventRecord {
  id: string;
  thread_id: string;
  user_id: string;
  reason: string;
  detected_at: string;
  resolution?: string | null;
  resolved_at?: string | null;
}

function toCrisisEvent(record: CrisisEventRecord): CrisisEvent {
  return {
    id: record.id,
    threadId: record.thread_id,
    userId: record.user_id,
    reason: record.reason,
    detectedAt: record.detected_at,
    resolution: record.resolution ?? null,
    resolvedAt: record.resolved_at ?? null,
  };
}

export async function listUnresolvedCrisisEvents(): Promise<CrisisEvent[]> {
  const records = await adminFetch<CrisisEventRecord[]>("/crisis-events?unresolved=true");
  return records.map(toCrisisEvent);
}
