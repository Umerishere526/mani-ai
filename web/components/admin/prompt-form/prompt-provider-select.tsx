// ABOUTME: Provider <select> for PromptModelFields — loading state, empty state, and the
// ABOUTME: "currently selected provider is not configured" warning branch.

import type { FieldErrors, UseFormRegister } from "react-hook-form";
import type { PromptFormValues } from "@/lib/schema";
import type { ProviderListItem } from "@/types";
import dictionary from "@/dictionaries/en.json";
import { FORM_INPUT_CLASSES, FORM_LABEL_CLASSES, FORM_HELPER_CLASSES, FORM_ERROR_CLASSES } from "../form-field-classes";

const STRINGS = dictionary.admin.forms.prompt;

interface PromptProviderSelectProps {
  register: UseFormRegister<PromptFormValues>;
  errors: FieldErrors<PromptFormValues>;
  providers: ProviderListItem[];
  loadingProviders: boolean;
  selectedProvider: string | undefined;
  isProviderValid: boolean;
}

export function PromptProviderSelect({
  register,
  errors,
  providers,
  loadingProviders,
  selectedProvider,
  isProviderValid,
}: PromptProviderSelectProps) {
  return (
    <div>
      <label htmlFor="provider" className={FORM_LABEL_CLASSES}>
        {STRINGS.providerLabel}
      </label>
      <select
        id="provider"
        {...register("provider")}
        disabled={loadingProviders}
        className={FORM_INPUT_CLASSES}
      >
        {loadingProviders ? (
          <option>{STRINGS.providerLoading}</option>
        ) : providers.length === 0 && !selectedProvider ? (
          <option value="">{STRINGS.providerNoneConfigured}</option>
        ) : (
          <>
            {selectedProvider && !isProviderValid && (
              <option value={selectedProvider} disabled>
                {STRINGS.providerNotConfigured.replace("{provider}", selectedProvider)}
              </option>
            )}
            {!isProviderValid && providers.length > 0 && (
              <option value="">{STRINGS.providerSelectPrompt}</option>
            )}
            {providers.map((p) => (
              <option key={p.id} value={p.name}>
                {p.displayName || p.name}
              </option>
            ))}
          </>
        )}
      </select>
      {errors.provider && <p className={FORM_ERROR_CLASSES}>{errors.provider.message}</p>}
      {providers.length === 0 && !loadingProviders && (
        <p className={`${FORM_HELPER_CLASSES} text-mani-error`}>
          {STRINGS.providerMissingHelper}
        </p>
      )}
      {!isProviderValid && !loadingProviders && providers.length > 0 && (
        <p className={`${FORM_HELPER_CLASSES} text-yellow-600`}>
          {STRINGS.providerInvalidHelper.replace("{provider}", selectedProvider ?? "")}
        </p>
      )}
    </div>
  );
}
