import { useEffect, useRef, useState } from "react";
import { Image, KeyboardAvoidingView, Platform, StatusBar, View } from "react-native";
import { useLocalSearchParams, router } from "expo-router";
import { AppHeader } from "@/components/shared";
import { ChatConversation, ChatOpening, LoadFailed, type ChatInputBarRef } from "@/components/chat";
import { useChat } from "@/hooks/useChat";
import { useChatSafety } from "@/providers";
import type { SmartPrompt } from "@/types/chat";

export default function ChatScreen() {
  const params = useLocalSearchParams<{ threadId?: string; requestNewThread?: string }>();
  const safety = useChatSafety();
  const chatInputRef = useRef<ChatInputBarRef>(null);
  const [inputValue, setInputValue] = useState("");
  // The pause is account-wide: a new chat or another thread starts paused too.
  const paused = safety.pause !== null;
  const chat = useChat(params.threadId, { onTurn: safety.noteTurn, onSendError: safety.noteSendError });
  const isWaitingForReply = chat.state.sending !== null;

  useEffect(() => {
    if (params.requestNewThread === "true") {
      chat.startNewThread();
      router.setParams({ requestNewThread: undefined });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.requestNewThread]);

  const handleSend = () => {
    if (!inputValue.trim() || isWaitingForReply || paused) return;
    chat.send(inputValue);
    setInputValue("");
  };

  const handlePromptPress = (prompt: SmartPrompt) => {
    if (paused) return;
    chat.send(prompt.label);
  };

  const handleNewChat = () => {
    chat.startNewThread();
    setInputValue("");
    chatInputRef.current?.focus();
  };

  const renderBody = () => {
    if (!chat.started) {
      return (
        <ChatOpening
          opening={chat.opening}
          defaultStyle={chat.defaultStyle}
          failed={chat.loadFailed}
          onRetry={chat.reload}
          onSelect={chat.chooseStyle}
        />
      );
    }
    if (chat.loadFailed) return <LoadFailed onRetry={chat.reload} />;
    return (
      <ChatConversation
        messages={chat.state.messages}
        isWaitingForReply={isWaitingForReply}
        paused={paused}
        inputValue={inputValue}
        onChangeInput={setInputValue}
        onSend={handleSend}
        onPromptPress={handlePromptPress}
        onPausedPress={safety.openScreen}
        chatInputRef={chatInputRef}
      />
    );
  };

  return (
    <View className="flex-1 bg-primary-900">
      <StatusBar barStyle="light-content" />
      <KeyboardAvoidingView className="flex-1" behavior={Platform.OS === "ios" ? "padding" : "height"}>
        <AppHeader onNewChatPress={handleNewChat} />
        {renderBody()}
      </KeyboardAvoidingView>
      <View className="absolute inset-0 opacity-50" pointerEvents="none">
        <Image source={require("@/assets/images/noise.png")} className="h-full w-full" resizeMode="repeat" />
      </View>
    </View>
  );
}
