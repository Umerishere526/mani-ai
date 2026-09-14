// ABOUTME: Centralized responsive font sizes, keyed to screen-size tier, so screens get
// ABOUTME: consistent type scale without repeating breakpoint logic. See useResponsiveLayout
// ABOUTME: for the sibling hook covering non-typography positioning constants.

import { useMemo } from 'react';
import { pickByScreenSize } from '@/lib/utils';
import { useResponsiveDimensions } from './useResponsiveDimensions';

export function useResponsiveTypography() {
  const { isSmallScreen, isLargeScreen } = useResponsiveDimensions();

  return useMemo(() => {
    const responsive = <T,>(small: T, standard: T, large: T): T =>
      pickByScreenSize(isSmallScreen, isLargeScreen, small, standard, large);

    return {
      // Large headlines (e.g., "mani is here to make...")
      headline: {
        fontSize: responsive(21, 24, 26),
        lineHeight: responsive(30, 34, 38),
      },

      // Section titles (e.g., "We Care.", "Your space is safe...")
      title: {
        fontSize: responsive(18, 20, 22),
        lineHeight: responsive(24, 28, 32),
      },

      // Body text
      body: {
        fontSize: responsive(15, 16, 18),
        lineHeight: responsive(22, 24, 28),
      },

      // Small/caption text
      caption: {
        fontSize: responsive(14, 16, 16),
        lineHeight: responsive(20, 24, 24),
      },

      // Logo sizing
      logo: {
        height: responsive(48, 55, 55),
        width: responsive(115, 130, 130),
        marginBottom: responsive(16, 20, 20),
      },

      // Home screen card values
      homeCard: {
        aspectRatio: responsive(4.5, 4.2, 4.5),
        titleFontSize: responsive(14, 16, 18),
        descriptionFontSize: responsive(13, 14, 15),
        bottomPadding: responsive(12, 16, 20),
        gap: responsive(12, 16, 20),
        sphereSize: responsive(60, 70, 80),
        heroVerticalPadding: responsive(16, 20, 24),
        metaMarginBottom: responsive(6, 12, 12),
        libraryLinkMarginTop: responsive(40, 64, 64),
      },
    };
  }, [isSmallScreen, isLargeScreen]);
}

export type ResponsiveTypography = ReturnType<typeof useResponsiveTypography>;
