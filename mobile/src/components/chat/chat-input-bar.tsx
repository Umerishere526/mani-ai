// ABOUTME: The message composer at the bottom of the chat screen — multiline input, send
// ABOUTME: button, and an optional "Get Help" pill shown alongside it (not inside it).

import { forwardRef, useCallback, useImperativeHandle, useRef } from 'react';
import { Pressable, View, type TextInput as RNTextInput } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { colors } from '@/lib/tokens';
import en from '@/dictionaries/en.json';
import { Text, TextInput, SendButton } from '@/components/shared';

export interface ChatInputBarProps {
  value: string;
  onChangeText: (text: string) => void;
  onSend: () => void;
  onGetHelp?: () => void;
  placeholder?: string;
  disabled?: boolean;
}

export interface ChatInputBarRef {
  focus: () => void;
}

export const ChatInputBar = forwardRef<ChatInputBarRef, ChatInputBarProps>(function ChatInputBar(
  { value, onChangeText, onSend, onGetHelp, placeholder = en.chat.messagePlaceholder, disabled = false },
  ref,
) {
  const inputRef = useRef<RNTextInput>(null);
  const insets = useSafeAreaInsets();
  const canSend = value.trim().length > 0 && !disabled;

  useImperativeHandle(ref, () => ({
    focus: () => inputRef.current?.focus(),
  }));

  const handleSubmit = useCallback(() => {
    if (canSend) onSend();
  }, [canSend, onSend]);

  return (
    <View className="px-4 pt-2" style={{ paddingBottom: insets.bottom || 12 }}>
      <View className="flex-row items-end gap-2">
        <View className="flex-1 flex-row rounded-xl bg-primary-600 py-1.5 pl-4 pr-1">
          <TextInput
            ref={inputRef}
            className="max-h-37.5 min-h-9 flex-1 py-2 text-base"
            value={value}
            onChangeText={onChangeText}
            placeholder={placeholder}
            placeholderTextColor={colors.primary[300]}
            onSubmitEditing={handleSubmit}
            returnKeyType="send"
            editable={!disabled}
            multiline
            keyboardAppearance="dark"
            accessibilityLabel={en.chat.messageInputLabel}
            accessibilityHint={en.chat.messageInputHint}
            style={{ textAlignVertical: 'center' }}
          />
          <View className="justify-end self-end pb-0.5">
            <SendButton onPress={handleSubmit} disabled={!canSend} filled={canSend} />
          </View>
        </View>
        {onGetHelp && (
          <Pressable
            onPress={onGetHelp}
            className="h-12 justify-center rounded-full bg-primary-600 px-5 opacity-90 active:opacity-70"
            accessibilityLabel={en.chat.getHelpLabel}
            accessibilityRole="button"
          >
            <Text className="font-sans-medium text-sm">{en.chat.getHelp}</Text>
          </Pressable>
        )}
      </View>
    </View>
  );
});
