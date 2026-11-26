// ABOUTME: Tests where each kind of button under a reply leads: library topics, the library's front page, and
// ABOUTME: technique offers and plain replies sent as their label.

import { promptAction } from './prompt-action';

describe('promptAction', () => {
  it('opens the library section a library button names', () => {
    expect(promptAction({ label: 'Try a breathing exercise', library: 'Anxiety' })).toEqual({ kind: 'library', section: 'Anxiety' });
  });

  it('opens the library front page for "home"', () => {
    expect(promptAction({ label: 'Visit library', library: 'home' })).toEqual({ kind: 'library', section: null });
  });

  it('sends a technique offer and a plain reply as their label', () => {
    expect(promptAction({ label: 'Show me how', technique: 'abcde' })).toEqual({ kind: 'send', text: 'Show me how' });
    expect(promptAction({ label: 'Continue chatting' })).toEqual({ kind: 'send', text: 'Continue chatting' });
  });
});
