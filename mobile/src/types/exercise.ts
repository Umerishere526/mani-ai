// ABOUTME: The exercise library's shapes as the screens use them, mapped from the backend's ExerciseOut and TopicOut
// ABOUTME: by lib/api/exercises.ts.

export interface Exercise {
  id: string;
  title: string;
  description: string;
  subtitle: string | null;
  type: string | null;
  category: string;
  /** Set when a topic lists this exercise from another topic: the group it is shown under there. */
  subcategory: string | null;
  /** Rounded by the API to the nearest 30 seconds; null when it has no length yet. */
  durationMinutes: number | null;
  /** False until the client records it: listed as coming soon, with no audio. */
  recorded: boolean;
  audioUrl: string | null;
}

/** A library topic; its id is the `category` its own exercises carry. */
export interface Topic {
  id: string;
  title: string;
  blurb: string;
}

/** A topic's exercises under one subcategory heading; `subcategory` null is the topic's own. */
export interface ExerciseGroup {
  subcategory: string | null;
  exercises: Exercise[];
}
