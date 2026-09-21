// ABOUTME: Renders the two global overlay drawers (nav menu, crisis support) above the
// ABOUTME: route stack. Lives in the root layout so any screen can trigger them via useDrawer.

import { router } from 'expo-router';
import { ChatDrawer } from '@/components/chat';
import { CrisisDrawer } from '@/components/crisis';
import { useDrawer } from '@/providers';
import type { ThreadListItem } from '@/types/chat';

// TODO: remove once threads come from a real backend — lets the drawer's thread list
// (date grouping, row styling) be viewed and tested with no API wired up yet.
const DUMMY_THREADS: ThreadListItem[] = [
  { id: 'dummy-1', title: 'Feeling overwhelmed at work', lastMessageAt: new Date().toISOString() },
  { id: 'dummy-2', title: null, preview: 'Can we talk about my sleep schedule?', lastMessageAt: new Date().toISOString() },
  {
    id: 'dummy-3',
    title: 'Setting boundaries with family',
    lastMessageAt: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 'dummy-4',
    title: 'Anxiety before a big presentation',
    lastMessageAt: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
  },
];

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
        threads={DUMMY_THREADS}
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
