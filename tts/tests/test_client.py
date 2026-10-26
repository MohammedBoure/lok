import base64
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gemini_speech.client import GeminiSpeechClient, _pcm_to_wav
from gemini_speech.models import SpeechModelInfo
from gemini_speech.voices import list_preset_voices, get_voice_profile


class TestGeminiSpeechClient(unittest.TestCase):

    def setUp(self) -> None:
        self.client = GeminiSpeechClient(api_keys=["dummy_test_key"])

    def test_preset_voices_catalog(self) -> None:
        voices = self.client.list_available_voices()
        self.assertGreaterEqual(len(voices), 5)
        names = [v.name for v in voices]
        self.assertIn("Puck", names)
        self.assertIn("Charon", names)
        self.assertIn("Kore", names)

    def test_voice_lookup_case_insensitive(self) -> None:
        puck = get_voice_profile("puck")
        self.assertIsNotNone(puck)
        self.assertEqual(puck.name, "Puck")

    def test_pcm_to_wav_header_generation(self) -> None:
        raw_pcm = b"\x00\x00" * 480  # 480 samples of 16-bit silence
        wav_data = _pcm_to_wav(audio_bytes=raw_pcm, mime_type="audio/pcm;rate=24000")

        self.assertTrue(wav_data.startswith(b"RIFF"))
        self.assertIn(b"WAVE", wav_data[:16])
        self.assertGreater(len(wav_data), len(raw_pcm))

    def test_extract_audio_payload_success(self) -> None:
        fake_pcm = b"FAKE_AUDIO_BYTES"
        b64_audio = base64.b64encode(fake_pcm).decode("ascii")

        response_payload = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "inlineData": {
                                    "mimeType": "audio/wav",
                                    "data": b64_audio,
                                }
                            }
                        ]
                    }
                }
            ]
        }

        extracted_bytes, mime = self.client._extract_audio_payload(response_payload)
        self.assertEqual(extracted_bytes, fake_pcm)
        self.assertEqual(mime, "audio/wav")


if __name__ == "__main__":
    unittest.main()
