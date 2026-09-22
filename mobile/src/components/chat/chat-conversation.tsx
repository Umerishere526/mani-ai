// ABOUTME: The message list + input area of an active chat thread — everything shown once
// ABOUTME: a conversation style has been picked. Swaps the input for CrisisBanner if needed.

import { View, FlatList, type ListRenderItem } from 'react-native';
import en from '@/dictionaries/en.json';
import type { ChatInputBarRef } from './chat-input-bar';
import { ChatInputBar } from './chat-input-bar';
import { CrisisBanner } from './crisis-banner';
import { MessageBubble } from './message-bubble';
import { SmartPromptRow } from './smart-prompt-row';
import { TypingIndicator } from './typing-indicator';
import type { Message, SmartPrompt } from '@/types/chat';

export interface ChatConversationProps {
  messages: Message[];
  isWaitingForReply: boolean;
  crisisDetected: boolean;
  inputValue: string;
  onChangeInput: (text: string) => void;
  onSend: () => void;
  onPromptPress: (prompt: SmartPrompt) => void;
  onCrisisPress: () => void;
  chatInputRef: React.RefObject<ChatInputBarRef | null>;
}

const renderMessage: ListRenderItem<Message> = ({ item }) => <MessageBubble message={item} />;
const keyExtractor = (item: Message) => item.id;

export function ChatConversation({
  messages,
  isWaitingForReply,
  crisisDetected,
  inputValue,
  onChangeInput,
  onSend,
  onPromptPress,
  onCrisisPress,
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
          isWaitingForReply ? (
            <TypingIndicator />
          ) : (
            <SmartPromptRow prompts={latestPrompts} onPromptPress={onPromptPress} />
          )
        }
        keyboardShouldPersistTaps="handled"
        accessibilityLabel={en.chat.messagesListLabel}
      />

      {crisisDetected ? (
        <CrisisBanner onPress={onCrisisPress} />
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
