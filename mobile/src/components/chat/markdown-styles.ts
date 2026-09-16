// ABOUTME: Style object passed to react-native-marked's `styles` prop for Mani's chat
// ABOUTME: responses — the library takes raw style values, not classNames, by design.

import { colors, fonts } from '@/lib/tokens';

export const markdownStyles = {
  container: {
    backgroundColor: 'transparent',
  },
  text: {
    fontFamily: fonts.regular,
    fontSize: 16,
    lineHeight: 24,
    color: colors.secondary[500],
    backgroundColor: 'transparent',
  },
  paragraph: {
    marginTop: 0,
    marginBottom: 8,
    backgroundColor: 'transparent',
  },
  strong: {
    fontFamily: fonts.bold,
    fontSize: 16,
    color: colors.secondary[500],
  },
  em: {
    fontFamily: fonts.regular,
    fontSize: 16,
    fontStyle: 'italic' as const,
    color: colors.secondary[500],
  },
  heading1: {
    fontFamily: fonts.bold,
    fontSize: 29,
    marginBottom: 8,
    color: colors.secondary[500],
    backgroundColor: 'transparent',
  },
  heading2: {
    fontFamily: fonts.bold,
    fontSize: 23,
    marginBottom: 8,
    color: colors.secondary[500],
    backgroundColor: 'transparent',
  },
  listItem: {
    fontFamily: fonts.regular,
    marginBottom: 4,
    color: colors.secondary[500],
    backgroundColor: 'transparent',
  },
};
