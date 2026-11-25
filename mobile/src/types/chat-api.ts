// ABOUTME: The backend chat routes' bodies (backend/mani/models/api.py, mani/chat/crisis.py), snake_case as sent.
// ABOUTME: Only the fields the app reads; lib/chat maps them to the UI's shapes.

import type { ConversationStyle } from './chat';

export interface PromptOut {
  label: string;
  library?: string | null;
  technique?: string | null;
  decline?: boolean | null;
}

export interface ThreadOut {
  id: string;
  title?: string | null;
  crisis_detected?: boolean;
  created_at: string;
  last_message_at: string;
  conversation_style?: ConversationStyle | null;
}

export interface ThreadListOut {
  threads: ThreadOut[];
  next_cursor?: string | null;
}

export interface MessageOut {
  id: string;
  thread_id: string;
  role: 'user' | 'mani';
  content: string;
  prompts?: PromptOut[];
  created_at: string;
}

export interface MessageListOut {
  messages: MessageOut[];
  next_cursor?: string | null;
}

export interface SendMessageIn {
  content: string;
  client_message_id: string;
}

export interface ThreadStartIn extends SendMessageIn {
  style?: ConversationStyle | null;
}

export interface TurnOut {
  id?: string | null;
  content: string;
  created_at?: string | null;
  prompts?: PromptOut[];
  title?: string | null;
  crisis_detected?: boolean;
  paused_from?: string | null;
  paused_until?: string | null;
  // What the pause is for, set with paused_*; "overdose" puts emergency services first (R90).
  paused_for?: string | null;
  follow_up_pending?: boolean;
}

export interface ThreadStartedOut {
  thread: ThreadOut;
  turn: TurnOut;
}

export interface StyleOption {
  label: string;
  style: ConversationStyle;
}

export interface OpeningOut {
  greeting: string;
  style_options: StyleOption[];
  openers: Partial<Record<ConversationStyle, string>>;
  chat_paused_from?: string | null;
  chat_paused_until?: string | null;
  chat_paused_for?: string | null;
}

export interface CrisisResource {
  country: string;
  kind: 'emergency' | 'support' | 'directory';
  name: string;
  description?: string;
  phone?: string | null;
  sms?: string | null;
  url?: string | null;
  hours?: string | null;
}
