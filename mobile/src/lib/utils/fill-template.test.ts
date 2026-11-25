// ABOUTME: Tests for dictionary placeholder filling — every named placeholder is replaced,
// ABOUTME: and one with no value stays visible rather than silently disappearing.

import { fillTemplate } from './fill-template';

describe('fillTemplate', () => {
  it('replaces each named placeholder with its value', () => {
    expect(fillTemplate('{who}: {message}', { who: 'Mani', message: 'Hello' })).toBe('Mani: Hello');
  });

  it('leaves a placeholder with no value in place', () => {
    expect(fillTemplate('Conversation: {title}', {})).toBe('Conversation: {title}');
  });
});
