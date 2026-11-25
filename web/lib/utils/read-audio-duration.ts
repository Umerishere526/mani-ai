// ABOUTME: Reads an audio file's length in the browser from its metadata, before it is uploaded.
// ABOUTME: Resolves to minutes rounded to two decimals, the precision the exercise catalog stores.

export function readAudioDurationMinutes(file: File): Promise<number> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const audio = new Audio();
    audio.preload = "metadata";
    audio.onloadedmetadata = () => {
      URL.revokeObjectURL(url);
      if (!Number.isFinite(audio.duration) || audio.duration <= 0) {
        reject(new Error("audio has no readable duration"));
        return;
      }
      resolve(Math.round((audio.duration / 60) * 100) / 100);
    };
    audio.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("audio could not be read"));
    };
    audio.src = url;
  });
}
