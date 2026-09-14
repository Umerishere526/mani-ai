// ABOUTME: Reports window size and safe-area insets, plus scale helpers relative to a
// ABOUTME: reference device, so layouts can size proportionally across screen sizes.

import { useWindowDimensions } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

// Reference device: iPhone Pro Max (430x932)
// All scaling is relative to this device so Pro Max layout remains unchanged
const REFERENCE_WIDTH = 430;
const REFERENCE_HEIGHT = 932;

export function useResponsiveDimensions() {
  const { width, height } = useWindowDimensions();
  const insets = useSafeAreaInsets();

  // Scale factors relative to reference device
  // On Pro Max: ~1.0, on iPhone SE: ~0.72-0.87
  const widthScale = width / REFERENCE_WIDTH;
  const heightScale = height / REFERENCE_HEIGHT;

  const isSmallScreen = height < 700; // iPhone SE territory
  const isLargeScreen = height > 900; // iPhone Pro Max / Plus territory

  return {
    width,
    height,
    safeAreaTop: insets.top,
    safeAreaBottom: insets.bottom,
    isSmallScreen,
    isLargeScreen,
    // Scale a pixel value proportionally by width
    scaleWidth: (px: number) => px * widthScale,
    // Scale a pixel value proportionally by height
    scaleHeight: (px: number) => px * heightScale,
    // Scale uniformly (uses smaller scale to prevent overflow)
    scale: (px: number) => px * Math.min(widthScale, heightScale),
  };
}
