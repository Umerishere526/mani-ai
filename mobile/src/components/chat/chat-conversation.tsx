// ABOUTME: The message list + input area of an active chat thread — everything shown once
// ABOUTME: a conversation style has been picked. Swaps the input for CrisisBanner if needed.

import { View, FlatList, type ListRenderItem } from 'react-native';
import en from '@/dictionaries/en.json';
import type { ChatInputBarRef } from './chat-input-bar';
import { ChatInputBar } from './chat-input-bar';
import { CrisisBanner } from './crisis-banner';
import { ChatListFooter } from './chat-list-footer';
import { MessageBubble } from './message-bubble';
import type { Message, SmartPrompt } from '@/types/chat';

export interface ChatConversationProps {
  messages: Message[];
  isWaitingForReply: boolean;
  failed: { error: string | null } | null;
  paused: boolean;
  inputValue: string;
  onChangeInput: (text: string) => void;
  onSend: () => void;
  onPromptPress: (prompt: SmartPrompt) => void;
  onPausedPress: () => void;
  onRetry: () => void;
  chatInputRef: React.RefObject<ChatInputBarRef | null>;
}

const renderMessage: ListRenderItem<Message> = ({ item }) => <MessageBubble message={item} />;
const keyExtractor = (item: Message) => item.id;

export function ChatConversation({
  messages,
  isWaitingForReply,
  failed,
  paused,
  inputValue,
  onChangeInput,
  onSend,
  onPromptPress,
  onPausedPress,
  onRetry,
  chatInputRef,
}: ChatConversationProps) {
  const displayMessages = [...messages].reverse();
  const latestPrompts: SmartPrompt[] = displayMessages.find((m) => m.role === 'mani')?.promptOptions ?? [];

  return (
    <View className="flex-1">
      <FlatList
        data={displayMessages}
        renderItem={renderMessage}
        keyExtractor={keyExtractor}
        inverted
        contentContainerClassName="grow justify-end py-2"
        ListHeaderComponent={
          <ChatListFooter
            isWaitingForReply={isWaitingForReply}
            failed={failed}
            prompts={latestPrompts}
            onPromptPress={onPromptPress}
            onRetry={paused ? undefined : onRetry}
          />
        }
        keyboardShouldPersistTaps="handled"
        accessibilityLabel={en.chat.messagesListLabel}
      />

      {paused ? (
        <CrisisBanner onPress={onPausedPress} />
      ) : (
        <ChatInputBar
          ref={chatInputRef}
          value={inputValue}
          onChangeText={onChangeInput}
          onSend={onSend}
          disabled={isWaitingForReply}
        />
      )}
    </View>
  );
}
