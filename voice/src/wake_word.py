"""Wake word detection using openWakeWord (ONNX runtime).

openWakeWord ships a fixed set of bundled/pretrained models:
    alexa, hey_mycroft, hey_jarvis, hey_rhasspy, current_time, ...

Custom wake words (e.g. 'hey_mether') must be trained separately and
loaded as a local .onnx file via the ``wakeword_models`` path argument.

This class handles both cases and degrades gracefully when neither is
available so the rest of the voice pipeline can still run.
"""

import os
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# Built-in models that ship with openWakeWord (partial list — the library
# itself is the authority; we use these as safe fallbacks).
_BUILTIN_MODELS = [
    "alexa",
    "hey_mycroft",
    "hey_jarvis",
    "hey_rhasspy",
    "current_time",
    "timer",
    "weather",
]


def _resolve_model(wake_word: str) -> tuple[list, str]:
    """Return (wakeword_models kwarg, resolved_name) or raise RuntimeError.

    Resolution order:
    1. Custom .onnx file path pointed to by WAKE_WORD_MODEL env var.
    2. Exact name as a built-in openWakeWord model.
    3. First available built-in model as a safe fallback (logs a warning).
    4. Raises RuntimeError so the caller can disable wake detection.
    """
    # 1. Explicit custom model path
    custom_path = os.getenv("WAKE_WORD_MODEL", "")
    if custom_path and Path(custom_path).exists():
        print(f"[WAKE] Loading custom model from: {custom_path}")
        return [custom_path], wake_word

    # 2. Try exact name
    try:
        from openwakeword.model import Model as _Model
        _Model(wakeword_models=[wake_word])
        return [wake_word], wake_word
    except (ValueError, Exception):
        pass

    # 3. Fallback to first available built-in
    for fallback in _BUILTIN_MODELS:
        try:
            from openwakeword.model import Model as _Model
            _Model(wakeword_models=[fallback])
            print(
                f"[WAKE] ⚠  Model '{wake_word}' not found — falling back to '{fallback}'.\n"
                f"[WAKE]    To use a custom wake word, train an openWakeWord model and set:\n"
                f"[WAKE]    WAKE_WORD_MODEL=/path/to/hey_mether.onnx"
            )
            return [fallback], fallback
        except Exception:
            continue

    raise RuntimeError(
        f"No openWakeWord model found for '{wake_word}' and no built-in fallback loaded."
    )


class WakeWordDetector:
    """Detects a wake phrase in streaming audio.

    If no suitable model is available the detector runs in *disabled* mode:
    ``check()`` always returns False so the pipeline can still be used via
    typed chat without crashing.
    """

    def __init__(self, wake_word: str = "hey mether"):
        self.wake_word = wake_word.replace(" ", "_").lower()
        self.threshold = float(os.getenv("WAKE_WORD_THRESHOLD", "0.5"))
        self._disabled = False
        self.model = None
        self._active_name = self.wake_word

        try:
            models_arg, self._active_name = _resolve_model(self.wake_word)
            from openwakeword.model import Model
            self.model = Model(wakeword_models=models_arg)
            print(f"[WAKE] ✓ Wake word detector ready  (listening for: '{self._active_name}')")
        except RuntimeError as exc:
            print(f"[WAKE] ✗ Wake word disabled — {exc}")
            self._disabled = True

    @property
    def active_wake_word(self) -> str:
        """The actual model name being used (may differ from requested name)."""
        return self._active_name

    def check(self, audio_chunk: np.ndarray) -> bool:
        """Pass a float32 16 kHz audio chunk. Returns True if wake word fired."""
        if self._disabled or self.model is None:
            return False
        # openWakeWord expects int16 samples
        audio_int16 = (audio_chunk * 32768).astype(np.int16)
        pred = self.model.predict(audio_int16)
        score = pred.get(self._active_name, 0)
        return bool(score > self.threshold)

    def reset(self):
        """Reset internal state after a detection."""
        if self.model is not None:
            self.model.reset()
