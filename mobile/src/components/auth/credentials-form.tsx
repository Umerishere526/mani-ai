// ABOUTME: Email and password fields with one submit button, shared by sign-in and sign-up;
// ABOUTME: the screen decides what submitting does and how long a password must be.

import { useRef, useState } from 'react';
import type { TextInput as RNTextInput } from 'react-native';
import { PrimaryButton, TextInput } from '@/components/shared';
import en from '@/dictionaries/en.json';
import { isValidEmail } from '@/lib/utils';
import { FormError } from './form-error';
import { LabeledField } from './labeled-field';
import { PasswordField } from './password-field';

export interface CredentialsFormProps {
  submitLabel: string;
  busyLabel: string;
  isBusy: boolean;
  errorMessage: string | null;
  minPasswordLength: number;
  isNewPassword: boolean;
  passwordHint: string;
  onSubmit: (email: string, password: string) => void;
}

export function CredentialsForm({
  submitLabel,
  busyLabel,
  isBusy,
  errorMessage,
  minPasswordLength,
  isNewPassword,
  passwordHint,
  onSubmit,
}: CredentialsFormProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const passwordRef = useRef<RNTextInput>(null);

  const trimmedEmail = email.trim();
  const isValid = isValidEmail(trimmedEmail) && password.length >= minPasswordLength;
  const submit = () => {
    if (isValid && !isBusy) onSubmit(trimmedEmail, password);
  };

  return (
    <>
      <LabeledField label={en.auth.emailLabel}>
        <TextInput
          className="flex-1 px-4 py-4 text-base"
          value={email}
          onChangeText={setEmail}
          placeholder={en.auth.emailPlaceholder}
          placeholderTextColor="rgba(255, 244, 225, 0.4)"
          keyboardType="email-address"
          autoCapitalize="none"
          autoCorrect={false}
          autoComplete="email"
          returnKeyType="next"
          onSubmitEditing={() => passwordRef.current?.focus()}
          accessibilityLabel={en.auth.emailLabel}
        />
      </LabeledField>

      <PasswordField
        ref={passwordRef}
        label={en.auth.passwordLabel}
        value={password}
        onChangeText={setPassword}
        placeholder={en.auth.passwordPlaceholder}
        autoComplete={isNewPassword ? 'new-password' : 'current-password'}
        returnKeyType="done"
        onSubmitEditing={submit}
        accessibilityLabel={en.auth.passwordLabel}
        accessibilityHint={passwordHint}
      />

      <FormError message={errorMessage} />

      <PrimaryButton
        label={isBusy ? busyLabel : submitLabel}
        onPress={submit}
        disabled={!isValid || isBusy}
        className="mt-2 self-stretch"
      />
    </>
  );
}
