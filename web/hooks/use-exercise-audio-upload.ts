// ABOUTME: State and steps for uploading one exercise audio file: read its length, get a signed URL, PUT the file.
// ABOUTME: On success it holds the Storage path and the duration the exercise form saves.

"use client";

import { useState } from "react";
import { createExerciseUpload } from "@/lib/actions/exercise-upload";
import { readAudioDurationMinutes } from "@/lib/utils";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.forms.exercise;

interface UploadedAudio {
  audioPath: string | null;
  durationMinutes: number | null;
}

export function useExerciseAudioUpload(initial: UploadedAudio) {
  const [audio, setAudio] = useState<UploadedAudio>(initial);
  const [fileName, setFileName] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const upload = async (file: File) => {
    setIsUploading(true);
    setUploadError(null);
    try {
      const durationMinutes = await readAudioDurationMinutes(file).catch(() => null);
      if (durationMinutes === null) {
        setUploadError(STRINGS.audioReadError);
        return;
      }

      const target = await createExerciseUpload(file.name, file.type);
      if (target.error !== null) {
        setUploadError(target.error);
        return;
      }

      const response = await fetch(target.uploadUrl, {
        method: "PUT",
        headers: { "Content-Type": file.type },
        body: file,
      }).catch(() => null);
      if (!response?.ok) {
        setUploadError(STRINGS.audioUploadError);
        return;
      }

      setAudio({ audioPath: target.path, durationMinutes });
      setFileName(file.name);
    } finally {
      setIsUploading(false);
    }
  };

  return { ...audio, fileName, isUploading, uploadError, upload };
}
