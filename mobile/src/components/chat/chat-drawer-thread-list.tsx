// ABOUTME: The scrollable, date-grouped conversation history inside ChatDrawer.

import { FlatList, View } from 'react-native';
import type { ThreadListItem } from '@/types/chat';
import { groupThreadsByDate, type GroupedThreadRow } from '@/lib/utils';
import en from '@/dictionaries/en.json';
import { Text } from '@/components/shared';
import { DrawerActionRow } from './drawer-action-row';

export interface ChatDrawerThreadListProps {
  threads: ThreadListItem[];
  onThreadPress: (threadId: string) => void;
  contentBottomPadding: number;
}

function renderRow(item: GroupedThreadRow, onThreadPress: (threadId: string) => void) {
  if (item.type === 'header') {
    return (
      <View className="mt-2 py-2">
        <Text className="font-sans-semibold text-xs uppercase tracking-[0.5px] text-secondary-400">
          {en.chat.dateGroups[item.group]}
        </Text>
      </View>
    );
  }

  const title = item.thread.title ?? item.thread.preview ?? en.chat.newConversationFallbackTitle;
  return (
    <DrawerActionRow
      onPress={() => onThreadPress(item.thread.id)}
      accessibilityLabel={`Thread: ${title}`}
      className="mb-1"
    >
      <Text className="text-sm" numberOfLines={1}>
        {title}
      </Text>
    </DrawerActionRow>
  );
}

export function ChatDrawerThreadList({ threads, onThreadPress, contentBottomPadding }: ChatDrawerThreadListProps) {
  const rows = groupThreadsByDate(threads);

  return (
    <FlatList
      data={rows}
      renderItem={({ item }) => renderRow(item, onThreadPress)}
      keyExtractor={(item, index) => (item.type === 'header' ? `header-${item.group}` : `thread-${item.thread.id ?? index}`)}
      className="flex-1"
      contentContainerClassName="px-4"
      style={{ paddingBottom: contentBottomPadding }}
      showsVerticalScrollIndicator={false}
    />
  );
}
