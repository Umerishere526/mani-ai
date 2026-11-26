// ABOUTME: Tests the layout of a topic's listing: its own exercises first, then each subcategory's group in the order
// ABOUTME: the backend listed them, even when the backend interleaves two subcategories.

import type { Exercise } from '@/types/exercise';
import { groupBySubcategory } from './library';

function exercise(id: string, subcategory: string | null): Exercise {
  return { id, title: id, description: '', subtitle: null, type: 'Breathing', category: 'Stress', subcategory,
    durationMinutes: 3.5, recorded: true, audioUrl: null };
}

describe('groupBySubcategory', () => {
  it('keeps the topic’s own exercises first and gathers each subcategory under one heading', () => {
    const listed = [exercise('own', null), exercise('a', 'Stress & Pressure'), exercise('b', 'Boundaries at Work'),
      exercise('c', 'Stress & Pressure')];
    expect(groupBySubcategory(listed).map((g) => [g.subcategory, g.exercises.map((e) => e.id)])).toEqual([
      [null, ['own']],
      ['Stress & Pressure', ['a', 'c']],
      ['Boundaries at Work', ['b']],
    ]);
  });

  it('has no groups for an empty topic', () => {
    expect(groupBySubcategory([])).toEqual([]);
  });
});
