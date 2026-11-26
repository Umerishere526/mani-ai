// ABOUTME: Create/edit form for a prompt — basic info, content, model config, change summary.
// ABOUTME: Ported from mani-app's components/admin/PromptForm.tsx, restyled to Tailwind.

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { promptFormSchema, type PromptFormValues } from "@/lib/schema";
import { createPrompt, updatePrompt } from "@/lib/actions/prompts";
import type { Prompt } from "@/types";
import dictionary from "@/dictionaries/en.json";
import { isModelPrompt } from "./is-model-prompt";
import { PromptBasicFields } from "./prompt-basic-fields";
import { PromptContentField } from "./prompt-content-field";
import { PromptModelFields } from "./prompt-model-fields";
import { PromptChangeSummaryField } from "./prompt-change-summary-field";

const STRINGS = dictionary.admin.forms;
const PROMPT_STRINGS = STRINGS.prompt;

interface PromptFormProps {
  prompt?: Prompt;
  mode: "create" | "edit";
}

export function PromptForm({ prompt, mode }: PromptFormProps) {
  const router = useRouter();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<PromptFormValues>({
    resolver: zodResolver(promptFormSchema),
    defaultValues: {
      name: prompt?.name ?? "",
      description: prompt?.description ?? "",
      content: prompt?.content ?? "",
      modelId: prompt?.modelId ?? "",
      modelParameters: JSON.stringify(prompt?.modelParameters ?? {}, null, 2),
      changeSummary: "",
    },
  });

  const promptName = useWatch({ control, name: "name" });
  const showModelConfig = isModelPrompt(prompt?.name ?? promptName);

  const onSubmit = async (data: PromptFormValues) => {
    setSubmitError(null);
    const result = mode === "create" ? await createPrompt(data) : await updatePrompt(prompt?.id ?? "", data);
    if (result.error) {
      setSubmitError(result.error);
      return;
    }
    router.push("/admin/prompts");
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
      {submitError && (
        <div className="rounded-mani-md border border-mani-error/20 bg-mani-error-light px-5 py-4 text-[0.9375rem] text-mani-error">
          {submitError}
        </div>
      )}

      <PromptBasicFields register={register} errors={errors} mode={mode} />
      <PromptContentField register={register} errors={errors} />

      {showModelConfig && (
        <PromptModelFields register={register} errors={errors} />
      )}

      {mode === "edit" && (
        <PromptChangeSummaryField register={register} errors={errors} />
      )}

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
              ? PROMPT_STRINGS.createSubmit
              : PROMPT_STRINGS.editSubmit}
        </button>
      </div>
    </form>
  );
}
