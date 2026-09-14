// ABOUTME: Responsive positioning constants (content offsets, notification stack sizing)
// ABOUTME: that don't belong to the type scale in useResponsiveTypography.

import { useMemo } from 'react';
import { DimensionValue } from 'react-native';
import { pickByScreenSize } from '@/lib/utils';
import { useResponsiveDimensions } from './useResponsiveDimensions';

export function useResponsiveLayout() {
  const { isSmallScreen, isLargeScreen } = useResponsiveDimensions();

  return useMemo(() => {
    const responsive = <T,>(small: T, standard: T, large: T): T =>
      pickByScreenSize(isSmallScreen, isLargeScreen, small, standard, large);

    return {
      horizontalPadding: responsive(32, 40, 40),
      // Content position from top (as percentage)
      contentTop: responsive('42%', '44%', '44%') as DimensionValue,
      // Tighter content position for screens with more content
      contentTopCompact: responsive('38%', '40%', '40%') as DimensionValue,
      // Max width for greeting text on home screen
      greetingMaxWidth: responsive(240, 240, 280),

      // Notification stack (for NotificationsStep)
      notificationStack: {
        scale: responsive(0.75, 0.9, 1.0),
        marginBottom: responsive(8, 16, 24),
        headerTopMargin: responsive(40, 0, 0),
      },
    };
  }, [isSmallScreen, isLargeScreen]);
}

export type ResponsiveLayout = ReturnType<typeof useResponsiveLayout>;
