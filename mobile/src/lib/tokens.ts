// ABOUTME: TypeScript mirror of the color/font tokens defined in src/global.css, for
// ABOUTME: values that can't be a className — gradient arrays, SVG strokes, library style props.

/**
 * Keep this in sync with the `@theme` block in src/global.css by hand — there is no
 * codegen step linking them. Prefer Tailwind classNames (`bg-primary-900`, `font-sans-bold`)
 * everywhere a className is possible; reach for these constants only where the API takes a
 * raw value instead of a class (expo-linear-gradient's `colors` prop, react-native-svg
 * `stroke`, Reanimated `interpolateColor` outputs, react-native-marked's `styles` prop).
 */
export const colors = {
  primary: {
    50: '#F2F6F0',
    100: '#E0E9DC',
    200: '#C5D6BC',
    300: '#A5BB88',
    325: '#8BA872',
    350: '#749A5E',
    375: '#5E874C',
    400: '#4D7640',
    500: '#43653A',
    600: '#395631',
    700: '#2E4628',
    800: '#24371F',
    900: '#1A2816',
  },
  secondary: {
    50: '#FFFCF7',
    100: '#FFF9F0',
    200: '#FFF7E9',
    300: '#FFF5E5',
    400: '#FFF4E3',
    500: '#FFF4E1',
    600: '#F5E4CC',
    700: '#E6D1B3',
    800: '#D4BC99',
    900: '#C2A780',
  },
  bg: {
    default: '#FAFAF8',
    card: '#FFFFFF',
    sidebar: '#1C1C1A',
    sidebarHover: '#2A2A28',
    userBubble: '#F0F0ED',
  },
  text: {
    default: '#1C1C1A',
    muted: '#6B6B68',
    light: '#9A9A96',
    inverse: '#FFFFFF',
  },
  border: {
    default: '#E8E8E4',
    sidebar: '#2A2A28',
  },
  accent: {
    default: '#2D5A4A',
    hover: '#3D7A6A',
    light: '#E8F2EE',
  },
  error: {
    default: '#C53030',
    light: '#FED7D7',
    dark: '#A02828',
  },
  success: {
    default: '#2D5A4A',
    light: '#E8F2EE',
  },
} as const;

export const radii = {
  none: 0,
  sm: 6,
  md: 10,
  lg: 16,
  xl: 24,
  full: 9999,
} as const;

export const fonts = {
  regular: 'Montserrat-Regular',
  medium: 'Montserrat-Medium',
  semibold: 'Montserrat-SemiBold',
  bold: 'Montserrat-Bold',
} as const;

export type Colors = typeof colors;
export type Radii = typeof radii;
export type Fonts = typeof fonts;
