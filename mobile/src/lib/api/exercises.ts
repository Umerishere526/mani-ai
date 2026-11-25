// ABOUTME: The library routes: the topics with their blurbs, one topic's exercises, the home screen's and one
// ABOUTME: exercise, each mapped to the screens' shapes.

import type { ExerciseOut, TopicOut } from '@/types/api';
import type { Exercise, Topic } from '@/types/exercise';
import { api } from './index';

export function toExercise(out: ExerciseOut): Exercise {
  return {
    id: out.id,
    title: out.title,
    description: out.description,
    subtitle: out.subtitle,
    type: out.type,
    category: out.category,
    subcategory: out.subcategory,
    durationMinutes: out.duration_minutes,
    recorded: out.recorded,
    audioUrl: out.audio_url,
  };
}

export function getTopics(): Promise<Topic[]> {
  return api.request<TopicOut[]>('GET', '/v1/exercises/topics');
}

/** A topic's own exercises first, then those it lists from other topics, each with its subcategory. */
export async function getTopicExercises(topicId: string): Promise<Exercise[]> {
  const listed = await api.request<ExerciseOut[]>('GET', `/v1/exercises?category=${encodeURIComponent(topicId)}`);
  return listed.map(toExercise);
}

export async function getHomeExercises(): Promise<Exercise[]> {
  return (await api.request<ExerciseOut[]>('GET', '/v1/exercises/home')).map(toExercise);
}

export async function getExercise(id: string): Promise<Exercise> {
  return toExercise(await api.request<ExerciseOut>('GET', `/v1/exercises/${encodeURIComponent(id)}`));
}
