// ABOUTME: Tests for exercise time formatting — listed durations round to the nearest 30 s
// ABOUTME: and never show a seconds field of 60; the running clock shows exact seconds.

import { formatClock, formatDuration } from './format-duration';

describe('formatDuration', () => {
  it('rounds a listed duration to the nearest 30 seconds', () => {
    expect(formatDuration(2.64)).toBe('2:30');
    expect(formatDuration(3.5)).toBe('3:30');
    expect(formatDuration(3.8)).toBe('4:00');
  });

  it('carries into the next minute instead of showing 60 seconds', () => {
    expect(formatDuration(3.95)).toBe('4:00');
    expect(formatDuration(2.995)).toBe('3:00');
  });

  it('never shows a duration shorter than 0:30', () => {
    expect(formatDuration(0.1)).toBe('0:30');
    expect(formatDuration(0)).toBe('0:30');
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
