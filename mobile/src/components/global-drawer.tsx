// ABOUTME: Renders the global overlays (nav menu, crisis support drawer, crisis screen) above the
// ABOUTME: route stack. Lives in the root layout so any screen can trigger them.

import { router } from 'expo-router';
import { ChatDrawer } from '@/components/chat';
import { CrisisDrawer, CrisisScreen } from '@/components/crisis';
import { useDrawer } from '@/providers';
import { useThreadList } from '@/hooks/useThreadList';

export function GlobalDrawer() {
  const { isDrawerVisible, isCrisisDrawerVisible, closeDrawer, openCrisisDrawer, closeCrisisDrawer } = useDrawer();
  const threads = useThreadList(isDrawerVisible);

  const handleNewChat = () => {
    closeDrawer();
    router.push({ pathname: '/chat', params: { requestNewThread: 'true' } });
  };

  return (
    <>
      <ChatDrawer
        visible={isDrawerVisible}
        threads={threads}
        onClose={closeDrawer}
        onOpenCrisisDrawer={openCrisisDrawer}
        onNewChat={handleNewChat}
        onNavigateHome={() => {
          closeDrawer();
          router.push('/');
        }}
        onNavigateLibrary={() => {
          closeDrawer();
          router.push('/exercises');
        }}
        onNavigateSettings={() => {
          closeDrawer();
          router.push('/settings');
        }}
        onThreadPress={(threadId) => {
          closeDrawer();
          router.push({ pathname: '/chat', params: { threadId } });
        }}
      />
      <CrisisDrawer visible={isCrisisDrawerVisible} onClose={closeCrisisDrawer} />
      <CrisisScreen />
    </>
  );
}
