// ABOUTME: Persists the user's notification toggle to on-device storage — purely local
// ABOUTME: preference state, no backend involved.

import { useCallback, useEffect, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

const STORAGE_KEY = '@mani/notifications_enabled';

export function useNotificationPreference() {
  const [isEnabled, setIsEnabled] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    AsyncStorage.getItem(STORAGE_KEY)
      .then((value) => {
        if (isMounted) setIsEnabled(value === 'true');
      })
      .catch(() => {
        if (isMounted) setIsEnabled(false);
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const toggle = useCallback(async (enable: boolean) => {
    try {
      await AsyncStorage.setItem(STORAGE_KEY, enable ? 'true' : 'false');
      setIsEnabled(enable);
    } catch {
      // Silently fail
    }
  }, []);

  return { isEnabled, isLoading, toggle };
}
