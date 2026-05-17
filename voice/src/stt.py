"""Speech-to-text using faster-whisper (CTranslate2 backend)."""

import numpy as np
from faster_whisper import WhisperModel


class SpeechToText:
    """Transcribe audio with Whisper. Supports Hindi + English code-switching."""

    def __init__(self, model_size: str = "base", language: str = "hi"):
        # "hi" lets Whisper handle Hindi + English naturally
        self.model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",  # CPU-optimized quantisation
        )
        self.language = language

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcribe a numpy float32 audio array → text string."""
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        segments, info = self.model.transcribe(
            audio,
            language=self.language,
            beam_size=5,
            vad_filter=True,  # skip silence
            vad_parameters={"min_silence_duration_ms": 500},
        )

        text = " ".join(s.text.strip() for s in segments)
        return text.strip()
