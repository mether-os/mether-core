"""Wake word detection using openWakeWord (ONNX runtime)."""

import numpy as np
from openwakeword.model import Model


class WakeWordDetector:
    """Detects a wake phrase (e.g. 'hey jarvis') in streaming audio."""

    def __init__(self, wake_word: str = "hey_jarvis"):
        # openWakeWord uses underscore-separated, lowercase model names
        self.wake_word = wake_word.replace(" ", "_").lower()
        self.model = Model(
            wakeword_models=[self.wake_word]
        )
        self.threshold = 0.5

    def check(self, audio_chunk: np.ndarray) -> bool:
        """Pass a float32 16 kHz audio chunk. Returns True if wake word fired."""
        # openWakeWord expects int16 samples
        audio_int16 = (audio_chunk * 32768).astype(np.int16)
        pred = self.model.predict(audio_int16)
        score = pred.get(self.wake_word, 0)
        return score > self.threshold

    def reset(self):
        """Reset internal state after a detection."""
        self.model.reset()
