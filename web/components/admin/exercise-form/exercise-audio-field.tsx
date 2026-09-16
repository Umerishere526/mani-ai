// ABOUTME: Field group for ExerciseForm — MP3 upload, current-file display, upload state.
// ABOUTME: Split out from exercise-form.tsx to keep the parent component under the line cap.

import type { AdminExercise } from "@/types";
import dictionary from "@/dictionaries/en.json";
import { FORM_INPUT_CLASSES, FORM_LABEL_CLASSES } from "../form-field-classes";

const STRINGS = dictionary.admin.forms.exercise;

interface ExerciseAudioFieldProps {
  exercise?: AdminExercise;
  audioUrl: string | null;
  durationMinutes: number | null;
  fileName: string | null;
  isUploading: boolean;
  uploadError: string | null;
  onFileChange: (file: File) => void;
}

export function ExerciseAudioField({
  exercise,
  audioUrl,
  durationMinutes,
  fileName,
  isUploading,
  uploadError,
  onFileChange,
}: ExerciseAudioFieldProps) {
  return (
    <div>
      <label className={FORM_LABEL_CLASSES}>{STRINGS.audioLabel}</label>

      {audioUrl && (
        <div className="mb-2 rounded-mani-sm border border-mani-border bg-mani-bg-card p-3">
          <p className="text-sm text-mani-text">
            {STRINGS.audioCurrentPrefix}
            {fileName ?? audioUrl.split("/").pop()}
          </p>
          <p className="text-sm text-mani-text-muted">
            {STRINGS.audioDurationPrefix}
            {durationMinutes}
            {durationMinutes === 1 ? STRINGS.audioDurationSuffix : STRINGS.audioDurationSuffixPlural}
          </p>
        </div>
      )}

      <input
        type="file"
        accept="audio/mpeg,.mp3"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onFileChange(file);
        }}
        disabled={isUploading}
        className={FORM_INPUT_CLASSES}
      />

      {isUploading && <p className="mt-1 text-sm text-mani-text-muted">{STRINGS.audioUploading}</p>}
      {uploadError && <p className="mt-1 text-sm text-mani-error">{uploadError}</p>}
      {!exercise && !audioUrl && (
        <p className="mt-1 text-xs text-mani-text-muted">{STRINGS.audioHelper}</p>
      )}
    </div>
  );
}
