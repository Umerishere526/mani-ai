#!/usr/bin/env bash
# ABOUTME: Converts one of the client's WAV recordings to the library's MP3: 64 kbps, mono, 44.1 kHz.
# ABOUTME: Prints the MP3's length in minutes, the value its exercises.json entry holds as durationMinutes.

set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: scripts/convert_audio.sh <recording.wav> <content/exercises/name.mp3>" >&2
  exit 1
fi

for tool in ffmpeg ffprobe; do
  command -v "$tool" >/dev/null || { echo "$tool is not installed (brew install ffmpeg)" >&2; exit 1; }
done

# -n refuses to overwrite: a converted file is replaced only by deleting it first.
ffmpeg -hide_banner -loglevel error -n -i "$1" -codec:a libmp3lame -b:a 64k -ac 1 -ar 44100 "$2"
ffprobe -v error -show_entries format=duration -of csv=p=0 "$2" | awk '{ printf "%.2f\n", $1 / 60 }'
