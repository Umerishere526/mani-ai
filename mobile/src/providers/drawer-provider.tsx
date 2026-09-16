// ABOUTME: Context for the two global overlay drawers (main nav menu, crisis support) so
// ABOUTME: any screen can open/close them without prop-drilling through the route tree.

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';

interface DrawerContextValue {
  /** Whether the main navigation drawer is visible */
  isDrawerVisible: boolean;
  /** Whether the crisis help drawer is visible */
  isCrisisDrawerVisible: boolean;
  /** Open the main navigation drawer */
  openDrawer: () => void;
  /** Close the main navigation drawer */
  closeDrawer: () => void;
  /** Open the crisis help drawer */
  openCrisisDrawer: () => void;
  /** Close the crisis help drawer */
  closeCrisisDrawer: () => void;
}

const DrawerContext = createContext<DrawerContextValue | null>(null);

export function DrawerProvider({ children }: { children: ReactNode }) {
  const [isDrawerVisible, setIsDrawerVisible] = useState(false);
  const [isCrisisDrawerVisible, setIsCrisisDrawerVisible] = useState(false);

  const openDrawer = useCallback(() => setIsDrawerVisible(true), []);
  const closeDrawer = useCallback(() => setIsDrawerVisible(false), []);
  const openCrisisDrawer = useCallback(() => setIsCrisisDrawerVisible(true), []);
  const closeCrisisDrawer = useCallback(() => setIsCrisisDrawerVisible(false), []);

  const contextValue = useMemo(
    (): DrawerContextValue => ({
      isDrawerVisible,
      isCrisisDrawerVisible,
      openDrawer,
      closeDrawer,
      openCrisisDrawer,
      closeCrisisDrawer,
    }),
    [isDrawerVisible, isCrisisDrawerVisible, openDrawer, closeDrawer, openCrisisDrawer, closeCrisisDrawer],
  );

  return <DrawerContext.Provider value={contextValue}>{children}</DrawerContext.Provider>;
}

export function useDrawer(): DrawerContextValue {
  const context = useContext(DrawerContext);
  if (!context) {
    throw new Error('useDrawer must be used within a DrawerProvider');
  }
  return context;
}
