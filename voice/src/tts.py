"""Text-to-speech using Piper TTS (subprocess-based)."""

import os
import subprocess
import tempfile

import numpy as np
import scipy.io.wavfile as wav


class TextToSpeech:
    """Convert text → audio via Piper TTS binary."""

    def __init__(self, piper_exe: str, model_path: str):
        self.piper_exe = piper_exe
        self.model_path = model_path

    def speak(self, text: str) -> tuple[np.ndarray, int]:
        """Convert *text* to audio.

        Returns ``(audio_float32, sample_rate)``.
        """
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            out_path = f.name

        try:
            result = subprocess.run(
                [
                    self.piper_exe,
                    "--model", self.model_path,
                    "--output_file", out_path,
                ],
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=15,
            )

            if result.returncode != 0:
                raise RuntimeError(f"Piper failed: {result.stderr.decode()}")

            rate, data = wav.read(out_path)
            if data.dtype != np.float32:
                data = data.astype(np.float32) / 32768.0

            return data, rate

        finally:
            if os.path.exists(out_path):
                os.unlink(out_path)

    def speak_and_save(self, text: str, output_path: str):
        """Render TTS and save directly to *output_path*."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp = f.name

        try:
            subprocess.run(
                [self.piper_exe, "--model", self.model_path, "--output_file", tmp],
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=15,
            )
            os.replace(tmp, output_path)
        except Exception:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
