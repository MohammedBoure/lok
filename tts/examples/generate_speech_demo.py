"""Example: Synthesizing speech with rich acoustic style and expression prompts."""

import logging
import os
import sys

# Configure logging to see key rotation and status in real-time
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Ensure library can be imported from parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gemini_speech import GeminiSpeechClient, GeminiSpeechError


def main() -> None:
    print("=" * 75)
    print("Gemini Text-to-Speech Synthesis Demo")
    print("=" * 75)

    # 1. Initialize client (loads from .env automatically)
    try:
        client = GeminiSpeechClient(
            default_model="gemini-3.8-flash-tts",
            default_voice="Puck",
            key_cooldown_seconds=45.0,
        )
    except GeminiSpeechError as exc:
        print(f"\n[Configuration Error] {exc}")
        print("Please set your GEMINI_API_KEY or GEMINI_API_KEYS in .env file (see .env.example).")
        return

    # 2. Text to synthesize
    story_excerpt = (
        "Once upon a time in a whispering willow grove, a tiny blue sparrow named Pip "
        "discovered a glowing, golden acorn nestled beneath the moss. 'Oh goodness!' Pip gasped softly, "
        "'Could this be the legendary acorn of the Sun Queen?'"
    )

    output_audio_path = os.path.join(os.path.dirname(__file__), "pip_story_sample.wav")

    print("\nSynthesizing with:")
    print("  Model:               gemini-3.8-flash-tts")
    print("  Voice:               Puck")
    print("  Style Prompt:        Gentle, warm, enchanting bedtime fairytale narrator")
    print("  Expressions:         Wide-eyed wonder, soft gasps of astonishment, soothing cadence")
    print(f"  Target Destination:  {output_audio_path}\n")

    try:
        result = client.generate_speech(
            text=story_excerpt,
            model="gemini-3.8-flash-tts",
            voice_name="Puck",
            voice_style_prompt="Gentle, warm, enchanting bedtime fairytale narrator with relaxed pacing",
            expressions="Wide-eyed wonder, soft gasps of astonishment, soothing cadence",
            output_path=output_audio_path,
        )

        print("\n" + "=" * 75)
        print(" Synthesis Succeeded!")
        print(f"  Saved File:     {result.output_path}")
        print(f"  Payload Size:   {result.size_bytes} bytes")
        print(f"  MIME Type:      {result.mime_type}")
        print(f"  Voice Persona:  {result.voice_used}")
        print(f"  Active Key Slot:{result.key_index_used}")
        print("=" * 75)

    except GeminiSpeechError as err:
        print(f"\n[Synthesis Error] {err}")


if __name__ == "__main__":
    main()
