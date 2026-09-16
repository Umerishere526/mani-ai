// ABOUTME: Circular SVG progress ring wrapping arbitrary children — used as the audio
// ABOUTME: player's play/pause control with a progress arc drawn around it.

import { View } from 'react-native';
import Svg, { Circle } from 'react-native-svg';
import type { ReactNode } from 'react';

export interface CircularProgressButtonProps {
  /** Progress value between 0 and 1 */
  progress: number;
  /** Total size of the button */
  size: number;
  /** Width of the progress stroke */
  strokeWidth: number;
  progressColor: string;
  trackColor: string;
  children: ReactNode;
}

export function CircularProgressButton({
  progress,
  size,
  strokeWidth,
  progressColor,
  trackColor,
  children,
}: CircularProgressButtonProps) {
  const clampedProgress = Math.max(0, Math.min(1, progress));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference * (1 - clampedProgress);

  return (
    <View style={{ width: size, height: size }}>
      <Svg width={size} height={size} style={{ position: "absolute", top: 0, left: 0 }}>
        <Circle cx={size / 2} cy={size / 2} r={radius} stroke={trackColor} strokeWidth={strokeWidth} fill="none" />
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={progressColor}
          strokeWidth={strokeWidth}
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          rotation={-90}
          origin={`${size / 2}, ${size / 2}`}
        />
      </Svg>
      <View style={{ position: "absolute", top: 0, left: 0, width: size, height: size, alignItems: "center", justifyContent: "center" }}>
        {children}
      </View>
    </View>
  );
}
