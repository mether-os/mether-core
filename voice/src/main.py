"""METHER OS — Voice Pipeline Sidecar

Orchestrates: wake-word → STT → METHER agent → TTS → speaker.

Usage:
    cd voice/
    python src/main.py
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from audio import AudioCapture, AudioPlayer
from wake_word import WakeWordDetector
from stt import SpeechToText
from tts import TextToSpeech
from mether_client import METHERClient


def _parse_device(val: str | None):
    """Convert env string to sounddevice device arg (int or None)."""
    if not val or val.strip().lower() in ("", "none", "default"):
        return None
    try:
        return int(val)
    except ValueError:
        return val  # could be a device name string


async def main():
    print("[METHER-VOICE] ═══════════════════════════════════════")
    print("[METHER-VOICE]  METHER OS Voice Pipeline v0.1.0")
    print("[METHER-VOICE] ═══════════════════════════════════════")
    print("[METHER-VOICE] Initializing components...")

    mic_device = _parse_device(os.getenv("MIC_DEVICE"))
    spk_device = _parse_device(os.getenv("SPEAKER_DEVICE"))
    sample_rate = int(os.getenv("SAMPLE_RATE", "16000"))

    # ── Audio I/O ─────────────────────────────────────────────
    capture = AudioCapture(sample_rate=sample_rate, device=mic_device)
    player = AudioPlayer(device=spk_device)
    print("[METHER-VOICE] ✓ Audio I/O ready")

    # ── Wake word ─────────────────────────────────────────────
    wake_word = os.getenv("WAKE_WORD", "hey mether")
    wake = WakeWordDetector(wake_word)
    print(f"[METHER-VOICE] ✓ Wake word detector loaded  ({wake_word})")

    # ── Speech-to-text ────────────────────────────────────────
    whisper_model = os.getenv("WHISPER_MODEL", "base")
    whisper_lang = os.getenv("WHISPER_LANGUAGE", "hi")
    stt = SpeechToText(model_size=whisper_model, language=whisper_lang)
    print(f"[METHER-VOICE] ✓ Whisper STT loaded  (model={whisper_model}, lang={whisper_lang})")

    # ── Text-to-speech ────────────────────────────────────────
    piper_exe = os.getenv("PIPER_EXE", "./bin/piper.exe")
    piper_model = os.getenv("PIPER_MODEL", "./models/en_US-lessac-medium.onnx")
    tts = TextToSpeech(piper_exe=piper_exe, model_path=piper_model)
    print(f"[METHER-VOICE] ✓ Piper TTS ready  (model={os.path.basename(piper_model)})")

    # ── Backend client ────────────────────────────────────────
    backend_url = os.getenv("METHER_BACKEND_URL", "http://localhost:8000")
    ws_url = os.getenv("VOICE_WS_URL", "ws://localhost:8000/ws/voice")
    mether = METHERClient(base_url=backend_url, ws_url=ws_url)

    print(f"[METHER-VOICE] Connecting to METHER backend ({backend_url})...")
    try:
        await mether.connect_ws()
        print("[METHER-VOICE] ✓ WebSocket connected")
    except Exception as e:
        print(f"[METHER-VOICE] ✗ Backend connection failed: {e}")
        print("[METHER-VOICE]   Voice will run in offline mode (no agent responses)")

    # ── Notify backend ────────────────────────────────────────
    await mether.notify("voice.online", {"status": "listening"})

    # ── Background TTS speaker for typed chat responses ───────
    # When the user types in the frontend, the backend sends a
    # "speak" message over the voice WebSocket.  This task picks
    # those up and plays them through Piper so you hear every
    # response, not just voice-triggered ones.
    async def _speak_from_queue():
        while True:
            try:
                msg = await mether.msg_queue.get()
                if msg.get("type") == "speak":
                    text_to_speak = msg.get("text", "")
                    if not text_to_speak:
                        continue
                    print(f"[METHER-VOICE] 🔊 Speaking (from chat): \"{text_to_speak[:80]}{'...' if len(text_to_speak) > 80 else ''}\"")
                    try:
                        audio_data, rate = tts.speak(text_to_speak)
                        player.play(audio_data, rate)
                        print("[METHER-VOICE] ✅ Chat TTS done")
                    except Exception as e:
                        print(f"[METHER-VOICE] ⚠️  Chat TTS error: {e}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[METHER-VOICE] ⚠️  Queue listener error: {e}")
                await asyncio.sleep(0.5)

    speak_task = asyncio.create_task(_speak_from_queue())

    # ── Start mic capture ─────────────────────────────────────
    capture.start()
    print()
    print("[METHER-VOICE] ══════════════════════════════════════════")
    print("[METHER-VOICE]  🎤  Listening for wake word...  Say:")
    print(f"[METHER-VOICE]      \"{wake_word}\"")
    print("[METHER-VOICE]  💬  Typed chat responses will also be spoken!")
    print("[METHER-VOICE] ══════════════════════════════════════════")
    print()

    state = "sleeping"
    response = ""  # holds agent response for TTS

    try:
        while True:
            # ── SLEEPING: detect wake word ────────────────────
            if state == "sleeping":
                chunk = await asyncio.to_thread(capture.read, 0.5)

                if wake.check(chunk):
                    print()
                    print("[METHER-VOICE] ⚡ Wake word detected!")
                    state = "listening"
                    wake.reset()
                    capture.drain()

                    await mether.notify("voice.wake", {})
                    print("[METHER-VOICE] 🎙️  Listening... (speak now, 5s)")

            # ── LISTENING: capture speech ─────────────────────
            elif state == "listening":
                audio = await asyncio.to_thread(capture.read, 5.0)
                state = "processing"
                await mether.notify("voice.listening_done", {})

                # Transcribe
                print("[METHER-VOICE] 🔄 Transcribing...")
                text = await asyncio.to_thread(stt.transcribe, audio)

                if not text or len(text.strip()) < 2:
                    print("[METHER-VOICE] ❌ No speech detected — back to sleep")
                    state = "sleeping"
                    continue

                print(f"[METHER-VOICE] 📝 Heard: \"{text}\"")
                await mether.notify("voice.transcript", {"text": text})

                # Send to METHER agent
                print("[METHER-VOICE] 🧠 Sending to METHER agent...")
                try:
                    response = await mether.send_transcript(text)
                    print(f"[METHER-VOICE] 💬 Response: \"{response[:80]}{'...' if len(response) > 80 else ''}\"")
                except Exception as e:
                    print(f"[METHER-VOICE] ⚠️  Agent error: {e}")
                    response = "Sorry, I couldn't process that right now."

                state = "speaking"

            # ── SPEAKING: TTS playback ────────────────────────
            elif state == "speaking":
                print("[METHER-VOICE] 🔊 Speaking...")
                await mether.notify("voice.speaking", {})

                try:
                    audio_data, rate = await asyncio.to_thread(tts.speak, response)
                    await asyncio.to_thread(player.play, audio_data, rate)
                except Exception as e:
                    print(f"[METHER-VOICE] ⚠️  TTS error: {e}")
                    print(f"[METHER-VOICE]    (text response): {response}")

                await mether.notify("voice.done", {})
                print("[METHER-VOICE] ✅ Done — back to sleep\n")
                state = "sleeping"

            # Small yield to prevent busy-spinning
            await asyncio.sleep(0.01)

    except KeyboardInterrupt:
        print("\n[METHER-VOICE] Shutting down...")
    finally:
        speak_task.cancel()
        capture.stop()
        await mether.notify("voice.offline", {"status": "shutdown"})
        print("[METHER-VOICE] Goodbye.")


if __name__ == "__main__":
    asyncio.run(main())
