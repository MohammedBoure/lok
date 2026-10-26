"""Script to generate two expressive story voices using the Gemini Speech library:

1. Emotional Arabic voice for children's stories.
2. Animated English voice for children's stories.
"""

import os
import sys

# Ensure gemini_speech can be imported
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from gemini_speech import GeminiSpeechClient, GeminiSpeechError


def main() -> None:
    print("=" * 80)
    print("Gemini Speech Synthesis: Arabic & English Children's Story Voices")
    print("=" * 80)

    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)

    client = GeminiSpeechClient(
        default_model="gemini-3.8-flash-tts",
        key_cooldown_seconds=45.0,
    )

    print(f"Loaded {client.key_manager.total_keys} Gemini API key(s) from environment.\n")

    # --------------------------------------------------------------------------
    # Voice 1: Emotional Arabic Voice for Children's Stories
    # --------------------------------------------------------------------------
    arabic_story = (
        "كانَ يا ما كانَ، في قديمِ الزَّمانِ، في غابةٍ خضراءَ هادئة، عاشَ عصفورٌ صغيرٌ لطيفٌ يُدعى شادٍ. "
        "وفي صباحٍ مُشرقٍ، وجدَ زهرةً ذابلةً تبكي بحزن، فاقتربَ منها برفقٍ وهمسَ بحنان: "
        "'لا تحزني يا زهرتي الجميلة، سأطيرُ بعيداً لأحضرَ لكِ قطراتِ النَّدى الصافية، لتبتسمي من جديد!'"
    )

    arabic_output_path = os.path.join(output_dir, "arabic_children_story.wav")

    print("[1/2] Generating Emotional Arabic Children's Story Voice...")
    print("  Language:       Arabic (العربية)")
    print("  Model:          gemini-3.8-flash-tts")
    print("  Voice Persona:  Kore (Warm, tender, gentle storyteller)")
    print("  Style Prompt:   صوت دافئ ومؤثر ومليء بالحنان، حكواتي للأطفال بنبرة هادئة ورقيقة")
    print("  Expressions:    تعاطف كبير، همسات لطيفة، مشاعر حنونة ومطمئنة للطفل")
    print(f"  Target File:    {arabic_output_path}")

    try:
        arabic_result = client.generate_speech(
            text=arabic_story,
            model="gemini-3.8-flash-tts",
            voice_name="Kore",
            voice_style_prompt="صوت دافئ ومؤثر ومليء بالحنان، حكواتي للأطفال بنبرة هادئة ورقيقة وواضحة النطق",
            expressions="تعاطف كبير، همسات لطيفة، مشاعر حنونة ومطمئنة للطفل",
            output_path=arabic_output_path,
        )
        print(f"  --> Success! Size: {arabic_result.size_bytes:,} bytes | MIME: {arabic_result.mime_type}")
    except GeminiSpeechError as exc:
        print(f"  --> Failed to generate Arabic voice: {exc}")

    print("\n" + "-" * 80 + "\n")

    # --------------------------------------------------------------------------
    # Voice 2: Expressive English Voice for Children's Stories
    # --------------------------------------------------------------------------
    english_story = (
        "Deep within the Whispering Valley, where the stars danced like little golden lanterns, "
        "a tiny owl named Barnaby fluttered his soft wings. "
        "'Tonight,' he hooted with bright, sparkling eyes, 'we are going on a grand adventure "
        "to discover where the lost moonbeams hide! Hold on tight, my little friends!'"
    )

    english_output_path = os.path.join(output_dir, "english_children_story.wav")

    print("[2/2] Generating Expressive English Children's Story Voice...")
    print("  Language:       English")
    print("  Model:          gemini-3.8-flash-tts")
    print("  Voice Persona:  Puck (Playful, animated, cheerful narrator)")
    print("  Style Prompt:   Whimsical, enchanted fairytale narrator with playful curiosity")
    print("  Expressions:    Excitement, wide-eyed wonder, warm welcoming tone for young listeners")
    print(f"  Target File:    {english_output_path}")

    try:
        english_result = client.generate_speech(
            text=english_story,
            model="gemini-3.8-flash-tts",
            voice_name="Puck",
            voice_style_prompt="Whimsical, enchanted bedtime fairytale narrator with cheerful, playful pacing",
            expressions="Excitement, wide-eyed wonder, warm welcoming cadence",
            output_path=english_output_path,
        )
        print(f"  --> Success! Size: {english_result.size_bytes:,} bytes | MIME: {english_result.mime_type}")
    except GeminiSpeechError as exc:
        print(f"  --> Failed to generate English voice: {exc}")

    print("\n" + "=" * 80)
    print("Voice Generation Complete!")
    print(f"Audio files saved to: {output_dir}")
    print("=" * 80)


if __name__ == "__main__":
    main()
