// ABOUTME: Absolute-fill gradient background used behind card content (home exercise
// ABOUTME: cards, category cards) — the gradient prop can't take a className.

import { StyleSheet } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { colors } from '@/lib/tokens';

export function CardGradient() {
  return <LinearGradient colors={[colors.primary[600], colors.primary[800]]} style={StyleSheet.absoluteFill} />;
}
