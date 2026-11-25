// ABOUTME: Onboarding's one step: an optional nickname, then a tap on the default conversation
// ABOUTME: style, which saves both. The style cards are the chat picker's own.

import { View } from 'react-native';
import { ConversationStyleOption } from '@/components/chat';
import { FormError, LabeledField } from '@/components/auth';
import { Text, TextInput } from '@/components/shared';
import en from '@/dictionaries/en.json';
import type { ConversationStyle } from '@/types/chat';

export const NICKNAME_MAX_LENGTH = 40;

const STYLES: ConversationStyle[] = ['directive', 'supportive', 'reflective'];

export interface OnboardingFormProps {
  nickname: string;
  onNicknameChange: (value: string) => void;
  onStyleSelect: (style: ConversationStyle) => void;
  isSaving: boolean;
  errorMessage: string | null;
}

export function OnboardingForm({ nickname, onNicknameChange, onStyleSelect, isSaving, errorMessage }: OnboardingFormProps) {
  return (
    <>
      <Text className="mb-8 text-base leading-6 text-secondary-500/80">{en.onboarding.intro}</Text>

      <LabeledField label={en.onboarding.nicknameLabel}>
        <TextInput
          className="flex-1 px-4 py-4 text-base"
          value={nickname}
          onChangeText={onNicknameChange}
          placeholder={en.onboarding.nicknamePlaceholder}
          placeholderTextColor="rgba(255, 244, 225, 0.4)"
          maxLength={NICKNAME_MAX_LENGTH}
          autoComplete="nickname"
          returnKeyType="done"
          accessibilityLabel={en.onboarding.nicknameLabel}
          accessibilityHint={en.onboarding.nicknameHint}
        />
      </LabeledField>

      <Text className="mb-4 font-sans-medium text-base">{en.onboarding.stylePrompt}</Text>
      <View
        className="gap-4"
        accessibilityLabel={en.chat.styleOptionsLabel}
        accessibilityState={{ busy: isSaving, disabled: isSaving }}
        pointerEvents={isSaving ? 'none' : 'auto'}
      >
        {STYLES.map((style) => (
          <ConversationStyleOption key={style} style={style} onPress={onStyleSelect} />
        ))}
      </View>

      <View className="mt-4">
        {isSaving ? <Text className="text-sm text-secondary-500/80">{en.onboarding.saving}</Text> : null}
        <FormError message={errorMessage} />
      </View>
    </>
  );
}
