// ABOUTME: Create/edit form for a guided exercise — basic info, category, audio upload, status.
// ABOUTME: Ported from mani-app's components/admin/ExerciseForm.tsx, restyled to Tailwind.

"use client";

import { useState, useTransition, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import type { AdminExercise } from "@/types";
import dictionary from "@/dictionaries/en.json";
import { ExerciseBasicFields } from "./exercise-basic-fields";
import { ExerciseAudioField } from "./exercise-audio-field";

const STRINGS = dictionary.admin.forms.exercise;
const COMMON = dictionary.admin.forms;

interface ExerciseFormProps {
  exercise?: AdminExercise;
  onSubmit: (formData: FormData) => Promise<AdminExercise>;
  submitLabel?: string;
}

export function ExerciseForm({ exercise, onSubmit, submitLabel = STRINGS.defaultSubmit }: ExerciseFormProps) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [showOnHomeScreen, setShowOnHomeScreen] = useState(exercise?.showOnHomeScreen ?? false);
  const [audioUrl, setAudioUrl] = useState<string | null>(exercise?.audioUrl ?? null);
  const [durationMinutes, setDurationMinutes] = useState<number | null>(
    exercise?.durationMinutes ?? null,
  );
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  const isLibraryExercise = !showOnHomeScreen;

  const handleFileChange = (file: File) => {
    setIsUploading(true);
    setUploadError(null);

    // No backend yet — a real upload extracts duration via music-metadata server-side.
    // Fakes a plausible result so the form flow is reachable end-to-end.
    window.setTimeout(() => {
      setAudioUrl(`https://cdn.example.com/audio/${encodeURIComponent(file.name)}`);
      setDurationMinutes(Math.round((3 + Math.random() * 5) * 10) / 10);
      setFileName(file.name);
      setIsUploading(false);
    }, 600);
  };

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);

    startTransition(async () => {
      const result = await onSubmit(formData);
      router.push(`/admin/exercises/${result.id}`);
    });
  };

  return (
    <form onSubmit={handleSubmit} className="max-w-2xl space-y-6">
      <ExerciseBasicFields
        exercise={exercise}
        showOnHomeScreen={showOnHomeScreen}
        onShowOnHomeScreenChange={setShowOnHomeScreen}
        isLibraryExercise={isLibraryExercise}
      />

      {isLibraryExercise && (
        <ExerciseAudioField
          exercise={exercise}
          audioUrl={audioUrl}
          durationMinutes={durationMinutes}
          fileName={fileName}
          isUploading={isUploading}
          uploadError={uploadError}
          onFileChange={handleFileChange}
        />
      )}

      <input type="hidden" name="audioUrl" value={audioUrl ?? ""} />
      <input type="hidden" name="durationMinutes" value={durationMinutes ?? "0"} />

      <div>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            name="isActive"
            value="true"
            defaultChecked={exercise?.isActive ?? true}
            className="h-4 w-4 rounded border-mani-border text-mani-accent focus:ring-mani-accent-light"
          />
          <span className="mb-0 text-[0.9375rem] font-medium text-mani-text">
            {STRINGS.activeLabel}
          </span>
        </label>
        <p className="mt-1 text-xs text-mani-text-muted">{STRINGS.activeHelper}</p>
      </div>

      <div className="flex items-center gap-3 pt-4">
        <button
          type="submit"
          disabled={isPending || isUploading || (!exercise && isLibraryExercise && !audioUrl)}
          className="inline-flex items-center justify-center gap-2 rounded-mani-md bg-mani-accent px-5 py-2.5 text-[0.9375rem] font-medium text-white shadow-mani-sm transition-colors duration-200 hover:bg-mani-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isPending ? COMMON.saving : submitLabel}
        </button>
        <button
          type="button"
          onClick={() => router.back()}
          className="inline-flex items-center justify-center gap-2 rounded-mani-md border border-mani-border px-5 py-2.5 text-[0.9375rem] font-medium text-mani-text transition-colors duration-200 hover:border-mani-text-light hover:bg-mani-bg"
        >
          {COMMON.cancel}
        </button>
      </div>
    </form>
  );
}
