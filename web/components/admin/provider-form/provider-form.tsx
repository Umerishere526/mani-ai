// ABOUTME: Create/edit form for an LLM provider (name, display name, API key, base URL, config).
// ABOUTME: Ported from mani-app's components/admin/ProviderForm.tsx, restyled to Tailwind.

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { providerFormSchema, type ProviderFormValues } from "@/lib/schema";
import type { Provider } from "@/types";
import dictionary from "@/dictionaries/en.json";
import { ProviderFormFields } from "./provider-form-fields";

const STRINGS = dictionary.admin.forms;
const PROVIDER_STRINGS = STRINGS.provider;

interface ProviderFormProps {
  provider?: Provider;
  mode: "create" | "edit";
}

export function ProviderForm({ provider, mode }: ProviderFormProps) {
  const router = useRouter();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ProviderFormValues>({
    resolver: zodResolver(providerFormSchema),
    defaultValues: {
      name: provider?.name ?? "",
      displayName: provider?.displayName ?? "",
      apiKey: "",
      baseUrl: provider?.baseUrl ?? "",
      config: JSON.stringify(provider?.config ?? {}, null, 2),
    },
  });

  const onSubmit = async (data: ProviderFormValues) => {
    setSubmitError(null);

    try {
      // No backend yet — see Stage 4 plan in the mani-mobile-ui-port journal precedent.
      console.log("provider form submit", { mode, providerId: provider?.id, data });

      router.push("/admin/providers");
      router.refresh();
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : STRINGS.genericError);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
      {submitError && (
        <div className="rounded-mani-md border border-mani-error/20 bg-mani-error-light px-5 py-4 text-[0.9375rem] text-mani-error">
          {submitError}
        </div>
      )}

      <ProviderFormFields register={register} errors={errors} mode={mode} />

      <div className="flex justify-end gap-3 border-t border-mani-border pt-6">
        <button
          type="button"
          onClick={() => router.back()}
          className="inline-flex items-center justify-center gap-2 rounded-mani-md border border-mani-border px-5 py-2.5 text-[0.9375rem] font-medium text-mani-text transition-colors duration-200 hover:border-mani-text-light hover:bg-mani-bg"
        >
          {STRINGS.cancel}
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="inline-flex items-center justify-center gap-2 rounded-mani-md bg-mani-accent px-5 py-2.5 text-[0.9375rem] font-medium text-white shadow-mani-sm transition-colors duration-200 hover:bg-mani-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSubmitting
            ? STRINGS.saving
            : mode === "create"
              ? PROVIDER_STRINGS.createSubmit
              : PROVIDER_STRINGS.editSubmit}
        </button>
      </div>
    </form>
  );
}
