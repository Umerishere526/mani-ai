// ABOUTME: A labeled password input with a show/hide toggle, used by sign-in, sign-up
// ABOUTME: and change-password.

import { forwardRef, useState } from 'react';
import { Pressable, type TextInput as RNTextInput, type TextInputProps as RNTextInputProps } from 'react-native';
import { Ionicons } from '@react-native-vector-icons/ionicons';
import { TextInput } from '@/components/shared';
import en from '@/dictionaries/en.json';
import { LabeledField } from './labeled-field';

export interface PasswordFieldProps
  extends Pick<RNTextInputProps, 'value' | 'onChangeText' | 'placeholder' | 'returnKeyType' | 'onSubmitEditing' | 'autoComplete'> {
  label: string;
  accessibilityLabel: string;
  accessibilityHint?: string;
}

export const PasswordField = forwardRef<RNTextInput, PasswordFieldProps>(function PasswordField(
  { label, accessibilityLabel, accessibilityHint, ...inputProps },
  ref,
) {
  const [isVisible, setIsVisible] = useState(false);

  return (
    <LabeledField label={label}>
      <TextInput
        ref={ref}
        className="flex-1 px-4 py-4 text-base"
        placeholderTextColor="rgba(255, 244, 225, 0.4)"
        secureTextEntry={!isVisible}
        autoCapitalize="none"
        autoCorrect={false}
        accessibilityLabel={accessibilityLabel}
        accessibilityHint={accessibilityHint}
        {...inputProps}
      />
      <Pressable
        onPress={() => setIsVisible((visible) => !visible)}
        className="px-4 py-4"
        hitSlop={8}
        accessibilityLabel={isVisible ? en.changePassword.hidePassword : en.changePassword.showPassword}
        accessibilityRole="button"
      >
        <Ionicons name={isVisible ? 'eye-off-outline' : 'eye-outline'} size={22} color="rgba(255, 244, 225, 0.6)" />
      </Pressable>
    </LabeledField>
  );
});
