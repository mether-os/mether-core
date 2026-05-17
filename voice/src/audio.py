"""Audio capture and playback utilities for METHER voice pipeline."""

import queue
import numpy as np
import sounddevice as sd


SAMPLE_RATE = 16000
CHUNK = 1024


class AudioCapture:
    """Continuous mic capture into a thread-safe queue."""

    def __init__(self, sample_rate: int = SAMPLE_RATE, device=None):
        self.q: queue.Queue[np.ndarray] = queue.Queue()
        self.sample_rate = sample_rate
        self.device = device
        self.stream = None

    def start(self):
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=CHUNK,
            device=self.device,
            callback=self._callback,
        )
        self.stream.start()

    def stop(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()

    def _callback(self, indata, frames, time, status):
        self.q.put(indata.copy().flatten())

    def read(self, seconds: float = 3.0) -> np.ndarray:
        """Read *seconds* worth of audio from the queue (blocking)."""
        chunks_needed = int(self.sample_rate * seconds / CHUNK)
        chunks = []
        for _ in range(chunks_needed):
            chunks.append(self.q.get())
        return np.concatenate(chunks)

    def drain(self):
        """Clear the queue so stale audio is discarded."""
        while not self.q.empty():
            try:
                self.q.get_nowait()
            except queue.Empty:
                break


class AudioPlayer:
    """Play audio through the default (or chosen) speaker."""

    def __init__(self, sample_rate: int = 22050, device=None):
        self.sample_rate = sample_rate
        self.device = device

    def play(self, audio: np.ndarray, rate: int | None = None):
        sd.play(audio, rate or self.sample_rate, device=self.device)
        sd.wait()

    def play_file(self, path: str):
        import scipy.io.wavfile as wav

        rate, data = wav.read(path)
        if data.dtype != np.float32:
            data = data.astype(np.float32) / 32768.0
        sd.play(data, rate, device=self.device)
        sd.wait()
