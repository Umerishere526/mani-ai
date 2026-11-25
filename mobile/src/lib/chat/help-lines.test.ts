// ABOUTME: Tests which crisis lines the app shows from the backend's resource list, and that an empty or unread
// ABOUTME: list still yields 988, 911 and the helpline directory.

import type { CrisisResource } from '@/types/chat-api';
import { helpLines, siteName } from './help-lines';

describe('helpLines', () => {
  it('takes the first line of each kind that has the number or link it needs', () => {
    const resources: CrisisResource[] = [
      { country: 'US', kind: 'support', name: 'Crisis Text Line', sms: '741741' },
      { country: 'US', kind: 'support', name: '988 Suicide & Crisis Lifeline', phone: '988', sms: '988' },
      { country: 'US', kind: 'emergency', name: 'Emergency services', phone: '911' },
      { country: 'US', kind: 'directory', name: 'Find a helpline', url: 'https://findahelpline.com' },
    ];
    const lines = helpLines(resources);
    expect(lines.support?.phone).toBe('988');
    expect(lines.emergency?.phone).toBe('911');
    expect(siteName(lines.directory?.url ?? '')).toBe('findahelpline.com');
  });

  it('falls back to 988, 911 and findahelpline.com when the list could not be read', () => {
    for (const unread of [null, []]) {
      const lines = helpLines(unread);
      expect([lines.support?.phone, lines.support?.sms, lines.emergency?.phone]).toEqual(['988', '988', '911']);
      expect(lines.directory?.url).toBe('https://findahelpline.com');
    }
  });
});
