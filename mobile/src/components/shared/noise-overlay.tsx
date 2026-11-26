// ABOUTME: The film-grain texture laid over a whole screen's dark background, behind no touches,
// ABOUTME: sized to the screen it covers rather than to the texture image.

import { Image, View } from 'react-native';

// The size goes in style, not className: on the web react-native-web gives the image its file's
// pixel size as an inline style, which a class cannot override, and the 880px-wide texture would
// widen the page past the phone's width.
const FILL = { width: '100%', height: '100%' } as const;

export function NoiseOverlay() {
  return (
    <View className="absolute inset-0 opacity-50" pointerEvents="none" aria-hidden>
      <Image source={require('@/assets/images/noise.png')} style={FILL} resizeMode="repeat" />
    </View>
  );
}
