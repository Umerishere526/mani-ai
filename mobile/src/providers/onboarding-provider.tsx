// ABOUTME: Knows whether the signed-in person has finished onboarding (chosen a default
// ABOUTME: conversation style), read from GET /v1/profile, so the route guard can send them there.

import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { getProfile } from '@/lib/api/profile';
import { useSession } from '@/hooks/useSession';

export type OnboardingStatus = 'signedOut' | 'checking' | 'needed' | 'done' | 'error';

interface OnboardingContextValue {
  status: OnboardingStatus;
  retry: () => void;
  complete: () => void;
}

type CheckedStatus = Extract<OnboardingStatus, 'needed' | 'done' | 'error'>;

const OnboardingContext = createContext<OnboardingContextValue | null>(null);

export function OnboardingProvider({ children }: { children: ReactNode }) {
  const { session } = useSession();
  const userId = session?.user?.id ?? null;
  const [checked, setChecked] = useState<{ userId: string; status: CheckedStatus } | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!userId) return;
    let isCurrent = true;
    getProfile()
      .then((profile) => {
        if (isCurrent) setChecked({ userId, status: profile?.support_style ? 'done' : 'needed' });
      })
      .catch(() => {
        if (isCurrent) setChecked({ userId, status: 'error' });
      });
    return () => {
      isCurrent = false;
    };
  }, [userId, attempt]);

  let status: OnboardingStatus = 'signedOut';
  if (userId) status = checked?.userId === userId ? checked.status : 'checking';

  const value: OnboardingContextValue = {
    status,
    retry: () => {
      setChecked(null);
      setAttempt((count) => count + 1);
    },
    complete: () => {
      if (userId) setChecked({ userId, status: 'done' });
    },
  };

  return <OnboardingContext.Provider value={value}>{children}</OnboardingContext.Provider>;
}

export function useOnboarding(): OnboardingContextValue {
  const context = useContext(OnboardingContext);
  if (!context) throw new Error('useOnboarding must be used within an OnboardingProvider');
  return context;
}
