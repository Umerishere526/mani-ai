// ABOUTME: Tests for exercise time formatting: a listed duration shows as the API rounded it, and the running clock
// ABOUTME: shows exact seconds and never a negative time.

import { formatClock, formatDuration } from './format-duration';

describe('formatDuration', () => {
  it('shows the half-minute length the API sends as m:ss', () => {
    expect(formatDuration(3.5)).toBe('3:30');
    expect(formatDuration(0.5)).toBe('0:30');
    expect(formatDuration(10)).toBe('10:00');
  });
});

describe('formatClock', () => {
  it('shows exact remaining seconds without rounding to 30', () => {
    expect(formatClock(237)).toBe('3:57');
    expect(formatClock(59.6)).toBe('1:00');
  });

  it('never shows negative time', () => {
    expect(formatClock(-4)).toBe('0:00');
  });
});
