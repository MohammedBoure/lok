"""Example: Inspect available preset voice profiles and tone characteristics."""

import os
import sys

# Ensure library can be imported from parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gemini_speech import GeminiSpeechClient


def main() -> None:
    print("=" * 70)
    print("Gemini Voice Catalog & Personas")
    print("=" * 70)

    # Initialize client (can be initialized without live API keys just to inspect catalog)
    client = GeminiSpeechClient(api_keys=["mock_key_for_catalog_inspection"])
    voices = client.list_available_voices()

    print(f"Total Available Voices: {len(voices)}\n")
    for v in voices:
        print(f"Name:            {v.name}")
        print(f"Gender / Tone:   {v.gender} | {v.tone}")
        print(f"Description:     {v.description}")
        print(f"Recommended For: {', '.join(v.recommended_for)}")
        print("-" * 70)


if __name__ == "__main__":
    main()
