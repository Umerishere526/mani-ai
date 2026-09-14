// ABOUTME: Sets the status bar style whenever the screen using it comes into focus —
// ABOUTME: needed because multiple screens share one status bar and can disagree on style.

import { useCallback } from 'react';
import { useFocusEffect } from 'expo-router';
import { setStatusBarStyle } from 'expo-status-bar';

export function useStatusBarStyle(style: 'light' | 'dark' = 'light') {
  useFocusEffect(
    useCallback(() => {
      setStatusBarStyle(style);
    }, [style]),
  );
}
