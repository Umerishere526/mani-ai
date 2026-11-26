// ABOUTME: Backend request and response bodies the app sends and reads, mirroring
// ABOUTME: backend/mani/models/api.py by structure for the routes the app calls.

import type { ConversationStyle } from './chat';

export interface ProfileOut {
  nickname: string | null;
  topics: string[];
  support_style: ConversationStyle | null;
  age_bracket: string | null;
  chat_paused_from: string | null;
  chat_paused_until: string | null;
}

// Partial by design: a field left out keeps its stored value.
export interface ProfileIn {
  nickname?: string;
  support_style?: ConversationStyle;
}

export interface ExerciseOut {
  id: string;
  title: string;
  subtitle: string | null;
  description: string;
  type: string | null;
  category: string;
  subcategory: string | null;
  duration_minutes: number | null;
  recorded: boolean;
  audio_url: string | null;
}

export interface TopicOut {
  id: string;
  title: string;
  blurb: string;
}
