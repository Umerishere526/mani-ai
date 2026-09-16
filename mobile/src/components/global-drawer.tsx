// ABOUTME: Renders the two global overlay drawers (nav menu, crisis support) above the
// ABOUTME: route stack. Lives in the root layout so any screen can trigger them via useDrawer.

import { router } from 'expo-router';
import { ChatDrawer } from '@/components/chat';
import { CrisisDrawer } from '@/components/crisis';
import { useDrawer } from '@/providers';

export function GlobalDrawer() {
  const { isDrawerVisible, isCrisisDrawerVisible, closeDrawer, openCrisisDrawer, closeCrisisDrawer } = useDrawer();

  const handleNewChat = () => {
    closeDrawer();
    router.push({ pathname: '/chat', params: { requestNewThread: 'true' } });
  };

  return (
    <>
      <ChatDrawer
        visible={isDrawerVisible}
        threads={[]}
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
    </>
  );
}
