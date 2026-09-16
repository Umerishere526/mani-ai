import { useEffect, useRef, useState } from "react";
import {
  FlatList,
  Image,
  KeyboardAvoidingView,
  Platform,
  StatusBar,
  View,
  type ListRenderItem,
} from "react-native";
import { useLocalSearchParams, router } from "expo-router";
import { AppHeader } from "@/components/shared";
import {
  ChatInputBar,
  type ChatInputBarRef,
  CrisisBanner,
  MessageBubble,
  SmartPromptRow,
  TypingIndicator,
} from "@/components/chat";
import { useChatSimulation } from "@/hooks/useChatSimulation";
import { useDrawer } from "@/providers";
import en from "@/dictionaries/en.json";
import type { Message, SmartPrompt } from "@/types/chat";

const renderMessage: ListRenderItem<Message> = ({ item }) => <MessageBubble message={item} />;
const keyExtractor = (item: Message) => item.id;

export default function ChatScreen() {
  const params = useLocalSearchParams<{ threadId?: string; requestNewThread?: string }>();
  const { openCrisisDrawer } = useDrawer();
  const chatInputRef = useRef<ChatInputBarRef>(null);
  const [inputValue, setInputValue] = useState("");
  const { messages, isWaitingForReply, crisisDetected, sendMessage, startNewThread } = useChatSimulation(
    params.threadId,
  );

  useEffect(() => {
    if (params.requestNewThread === "true") {
      startNewThread();
      router.setParams({ requestNewThread: undefined });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.requestNewThread]);

  const displayMessages = [...messages].reverse();
  const latestPrompts: SmartPrompt[] = displayMessages.find((m) => m.role === "mani")?.promptOptions ?? [];

  const handleSend = () => {
    if (!inputValue.trim() || isWaitingForReply || crisisDetected) return;
    sendMessage(inputValue);
    setInputValue("");
  };

  const handlePromptPress = (prompt: SmartPrompt) => {
    if (crisisDetected) return;
    sendMessage(prompt.label);
  };

  const handleNewChat = () => {
    startNewThread();
    setInputValue("");
    chatInputRef.current?.focus();
  };

  return (
    <View className="flex-1 bg-primary-900">
      <StatusBar barStyle="light-content" />
      <KeyboardAvoidingView className="flex-1" behavior={Platform.OS === "ios" ? "padding" : "height"}>
        <AppHeader onNewChatPress={handleNewChat} />
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
                <SmartPromptRow prompts={latestPrompts} onPromptPress={handlePromptPress} />
              )
            }
            keyboardShouldPersistTaps="handled"
            accessibilityLabel={en.chat.messagesListLabel}
          />

          {crisisDetected ? (
            <CrisisBanner onPress={openCrisisDrawer} />
          ) : (
            <ChatInputBar
              ref={chatInputRef}
              value={inputValue}
              onChangeText={setInputValue}
              onSend={handleSend}
              disabled={isWaitingForReply}
            />
          )}
        </View>
      </KeyboardAvoidingView>
      <View className="absolute inset-0 opacity-50" pointerEvents="none">
        <Image source={require("@/assets/images/noise.png")} className="h-full w-full" resizeMode="repeat" />
      </View>
    </View>
  );
}
