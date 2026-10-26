"""Unit tests for test_generate_sound CLI entry point (__main__.py)."""

import io
import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import importlib
import importlib.util

# Load test_generate_sound.__main__ module dynamically
main_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "__main__.py"))
spec = importlib.util.spec_from_file_location("cli_main", main_path)
cli_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli_main)

build_parser = cli_main.build_parser
_handle_list_voices = cli_main._handle_list_voices
_handle_list_models = cli_main._handle_list_models
_handle_generate = cli_main._handle_generate
from gemini_speech.models import SpeechModelInfo, SynthesisResult


class TestCLI(unittest.TestCase):

    def setUp(self) -> None:
        self.parser = build_parser()

    def test_parser_generate_subcommand_defaults(self) -> None:
        args = self.parser.parse_args(["generate", "Hello world"])
        self.assertEqual(args.command, "generate")
        self.assertEqual(args.text, "Hello world")
        self.assertEqual(args.output, "output.wav")
        self.assertEqual(args.voice, "Aoede")
        self.assertEqual(args.model, "gemini-3.8-flash-tts")
        self.assertEqual(args.style, "Natural, expressive speech")
        self.assertIsNone(args.expressions)
        self.assertFalse(args.json)

    def test_parser_generate_custom_flags(self) -> None:
        args = self.parser.parse_args([
            "generate", "Sample dialogue",
            "-o", "custom.wav",
            "-v", "Puck",
            "-m", "gemini-2.5-flash-preview-tts",
            "-s", "Warm and playful",
            "-e", "cheerful",
            "--json"
        ])
        self.assertEqual(args.text, "Sample dialogue")
        self.assertEqual(args.output, "custom.wav")
        self.assertEqual(args.voice, "Puck")
        self.assertEqual(args.model, "gemini-2.5-flash-preview-tts")
        self.assertEqual(args.style, "Warm and playful")
        self.assertEqual(args.expressions, "cheerful")
        self.assertTrue(args.json)

    def test_handle_list_voices_json(self) -> None:
        args = self.parser.parse_args(["list-voices", "--json"])
        captured_stdout = io.StringIO()
        with patch("sys.stdout", captured_stdout):
            exit_code = _handle_list_voices(args)

        self.assertEqual(exit_code, 0)
        output_json = json.loads(captured_stdout.getvalue())
        self.assertTrue(output_json["success"])
        self.assertGreater(output_json["count"], 0)
        self.assertIsInstance(output_json["voices"], list)

    @patch("gemini_speech.client.GeminiSpeechClient.list_speech_models")
    def test_handle_list_models_json(self, mock_list_models: MagicMock) -> None:
        mock_list_models.return_value = [
            SpeechModelInfo(
                model_id="models/gemini-3.8-flash-tts",
                display_name="Gemini 3.8 Flash TTS",
                description="TTS model",
                supported_methods=["generateContent"],
            )
        ]
        args = self.parser.parse_args(["list-models", "--json"])
        captured_stdout = io.StringIO()
        with patch("sys.stdout", captured_stdout):
            exit_code = _handle_list_models(args)

        self.assertEqual(exit_code, 0)
        output_json = json.loads(captured_stdout.getvalue())
        self.assertTrue(output_json["success"])
        self.assertEqual(output_json["count"], 1)
        self.assertEqual(output_json["models"][0]["clean_id"], "gemini-3.8-flash-tts")

    @patch("gemini_speech.client.GeminiSpeechClient.generate_speech")
    def test_handle_generate_json(self, mock_generate: MagicMock) -> None:
        mock_generate.return_value = SynthesisResult(
            audio_bytes=b"RIFF...",
            mime_type="audio/wav",
            model_used="gemini-3.8-flash-tts",
            voice_used="Aoede",
            key_index_used=0,
            output_path="test.wav",
        )
        args = self.parser.parse_args(["generate", "Test phrase", "--json", "-o", "test.wav"])
        captured_stdout = io.StringIO()
        with patch("sys.stdout", captured_stdout):
            exit_code = _handle_generate(args)

        self.assertEqual(exit_code, 0)
        output_json = json.loads(captured_stdout.getvalue())
        self.assertTrue(output_json["success"])
        self.assertEqual(output_json["model"], "gemini-3.8-flash-tts")
        self.assertEqual(output_json["voice"], "Aoede")


if __name__ == "__main__":
    unittest.main()
