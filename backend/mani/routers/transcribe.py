# ABOUTME: Voice input - one audio recording in, its text out. No thread, no history.
# ABOUTME: A client sends the text back through POST /v1/threads/{id}/messages as usual.

from fastapi import APIRouter, UploadFile

from mani import stt
from mani.auth.deps import CurrentUser
from mani.models.api import TranscriptionOut

router = APIRouter(prefix="/v1/audio", tags=["audio"])


@router.post("/transcriptions", response_model=TranscriptionOut)
async def transcribe(user: CurrentUser, file: UploadFile) -> TranscriptionOut:
    """Transcribe one recording. Authenticated like every other endpoint, but writes
    nothing - the caller still sends the resulting text as an ordinary chat message."""
    del user  # auth only; transcription itself is not scoped to a user or thread
    audio_bytes = await file.read()
    text = await stt.transcribe(audio_bytes, file.filename or "audio.webm")
    return TranscriptionOut(text=text)
