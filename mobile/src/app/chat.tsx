import { useEffect, useRef, useState } from "react";
import { Image, KeyboardAvoidingView, Platform, StatusBar, View } from "react-native";
import { useLocalSearchParams, router } from "expo-router";
import { AppHeader } from "@/components/shared";
import { ChatConversation, ConversationStylePicker, type ChatInputBarRef } from "@/components/chat";
import { useChatSimulation } from "@/hooks/useChatSimulation";
import { useDrawer } from "@/providers";
import type { SmartPrompt } from "@/types/chat";

export default function ChatScreen() {
  const params = useLocalSearchParams<{ threadId?: string; requestNewThread?: string }>();
  const { openCrisisDrawer } = useDrawer();
  const chatInputRef = useRef<ChatInputBarRef>(null);
  const [inputValue, setInputValue] = useState("");
  const {
    messages,
    isWaitingForReply,
    crisisDetected,
    conversationStyle,
    selectConversationStyle,
    sendMessage,
    startNewThread,
  } = useChatSimulation(params.threadId);

  useEffect(() => {
    if (params.requestNewThread === "true") {
      startNewThread();
      router.setParams({ requestNewThread: undefined });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.requestNewThread]);

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
        {conversationStyle === null ? (
          <ConversationStylePicker onSelect={selectConversationStyle} />
        ) : (
          <ChatConversation
            messages={messages}
            isWaitingForReply={isWaitingForReply}
            crisisDetected={crisisDetected}
            inputValue={inputValue}
            onChangeInput={setInputValue}
            onSend={handleSend}
            onPromptPress={handlePromptPress}
            onCrisisPress={openCrisisDrawer}
            chatInputRef={chatInputRef}
          />
        )}
      </KeyboardAvoidingView>
      <View className="absolute inset-0 opacity-50" pointerEvents="none">
        <Image source={require("@/assets/images/noise.png")} className="h-full w-full" resizeMode="repeat" />
      </View>
    </View>
  );
}
