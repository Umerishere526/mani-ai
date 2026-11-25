// ABOUTME: Server action that asks the backend for a signed Storage upload URL for one exercise audio file.
// ABOUTME: The browser then uploads the file straight to Storage, so it never passes through this server.

"use server";

import { adminFetch, AdminApiError } from "@/lib/api/admin-fetch";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.forms.exercise;

const AUDIO_CONTENT_TYPE = "audio/mpeg";

interface UploadUrlRecord {
  path: string;
  upload_url: string;
}

export type ExerciseUploadTarget =
  | { error: null; path: string; uploadUrl: string }
  | { error: string; path: null; uploadUrl: null };

export async function createExerciseUpload(fileName: string, contentType: string): Promise<ExerciseUploadTarget> {
  const name = fileName.trim();
  if (!name || contentType !== AUDIO_CONTENT_TYPE) return { error: STRINGS.audioTypeError, path: null, uploadUrl: null };

  try {
    const target = await adminFetch<UploadUrlRecord>("/exercises/upload-url", {
      method: "POST",
      body: { filename: name, content_type: contentType },
    });
    return { error: null, path: target.path, uploadUrl: target.upload_url };
  } catch (error) {
    if (error instanceof AdminApiError) return { error: error.message, path: null, uploadUrl: null };
    throw error;
  }
}
