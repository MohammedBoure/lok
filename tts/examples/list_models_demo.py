"""Example: Discover and filter speech/TTS capable models in Google AI Studio / Gemini."""

import os
import sys

# Ensure library can be imported from parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gemini_speech import GeminiSpeechClient, GeminiSpeechError


def main() -> None:
    print("=" * 70)
    print("Gemini Speech Models Discovery")
    print("=" * 70)

    try:
        # Client automatically loads keys from .env
        client = GeminiSpeechClient()
        print(f"Discovered {client.key_manager.total_keys} API key(s) in pool.\n")

        print("Fetching and filtering speech-capable models from Gemini API...")
        speech_models = client.list_speech_models()

        print(f"\nFound {len(speech_models)} Speech-Capable Model(s):\n")
        for idx, model in enumerate(speech_models, 1):
            print(f"[{idx}] Model ID:    {model.model_id}")
            print(f"    Display:     {model.display_name}")
            print(f"    Methods:     {', '.join(model.supported_methods) if model.supported_methods else 'N/A'}")
            print(f"    Description: {model.description}")
            print("-" * 70)

    except GeminiSpeechError as err:
        print(f"\n[Error] {err}")
    except Exception as exc:
        print(f"\n[Unexpected Error] {exc}")


if __name__ == "__main__":
    main()
