// ABOUTME: Picks a value from three screen-size tiers (small/standard/large).
// ABOUTME: Shared by useResponsiveTypography so each screen doesn't repeat the branch.

/**
 * Screen tiers:
 * - Small: iPhone SE and similar (height < 700)
 * - Standard: iPhone 16 and similar
 * - Large: iPhone Pro Max and similar (height > 900)
 */
export function pickByScreenSize<T>(
  isSmallScreen: boolean,
  isLargeScreen: boolean,
  small: T,
  standard: T,
  large: T,
): T {
  if (isSmallScreen) return small;
  if (isLargeScreen) return large;
  return standard;
}
