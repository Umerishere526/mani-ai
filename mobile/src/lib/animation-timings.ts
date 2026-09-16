// ABOUTME: Centralized animation timing constants for consistent UX across the app —
// ABOUTME: mainly the "let the close animation start before navigating" delays.

export const ANIMATION_TIMINGS = {
  /** Delay before navigating after closing drawer */
  DRAWER_NAVIGATION_DELAY: 150,
  /** Delay before opening secondary drawer after closing primary */
  DRAWER_CHAIN_DELAY: 300,
  /** Content fade out duration for transitions */
  CONTENT_FADE_OUT: 200,
  /** Content fade in duration for transitions */
  CONTENT_FADE_IN: 300,
  /** Drawer slide in duration */
  DRAWER_SLIDE_IN: 400,
  /** Drawer overlay fade in duration */
  DRAWER_OVERLAY_IN: 450,
  /** Drawer slide/overlay out duration */
  DRAWER_SLIDE_OUT: 280,
  /** Crisis drawer slide in duration */
  CRISIS_DRAWER_IN: 350,
  /** Crisis drawer slide out duration */
  CRISIS_DRAWER_OUT: 300,
} as const;
