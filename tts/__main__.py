"""CLI entry point for test_generate_sound module execution (python -m test_generate_sound)."""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

# Support both package and direct script execution
try:
    from .gemini_speech import (
        GeminiSpeechClient,
        GeminiSpeechError,
        SpeechModelInfo,
        VoiceProfile,
        list_preset_voices,
    )
except ImportError:
    module_dir = os.path.dirname(os.path.abspath(__file__))
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)
    from gemini_speech import (  # type: ignore
        GeminiSpeechClient,
        GeminiSpeechError,
        SpeechModelInfo,
        VoiceProfile,
        list_preset_voices,
    )


def _handle_list_voices(args: argparse.Namespace) -> int:
    """Handle list-voices subcommand."""
    try:
        voices = list_preset_voices()

        if args.json:
            result = {
                "success": True,
                "count": len(voices),
                "voices": [
                    {
                        "name": v.name,
                        "gender": v.gender,
                        "tone": v.tone,
                        "description": v.description,
                        "language": v.language,
                        "recommended_for": v.recommended_for,
                    }
                    for v in voices
                ],
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0

        print(f"\nAvailable Voices ({len(voices)}):")
        print("=" * 70)
        for v in voices:
            print(f"• {v.name:<8} [{v.gender}] - {v.tone}")
            print(f"  Description: {v.description}")
            print(f"  Best For:    {', '.join(v.recommended_for)}")
            print("-" * 70)
        return 0

    except Exception as exc:
        if args.json:
            print(json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False))
        else:
            print(f"Error listing voices: {exc}", file=sys.stderr)
        return 1


def _handle_list_models(args: argparse.Namespace) -> int:
    """Handle list-models subcommand."""
    try:
        client = GeminiSpeechClient()
        models = client.list_speech_models()

        if args.json:
            result = {
                "success": True,
                "count": len(models),
                "models": [
                    {
                        "model_id": m.model_id,
                        "clean_id": m.clean_id,
                        "display_name": m.display_name,
                        "description": m.description,
                        "supported_methods": m.supported_methods,
                    }
                    for m in models
                ],
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0

        print(f"\nAvailable Speech Models ({len(models)}):")
        print("=" * 70)
        for m in models:
            print(f"• {m.model_id} ({m.display_name})")
            if m.description:
                print(f"  {m.description}")
            print(f"  Supported: {', '.join(m.supported_methods) if m.supported_methods else 'N/A'}")
            print("-" * 70)
        return 0

    except Exception as exc:
        if args.json:
            print(json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False))
        else:
            print(f"Error listing models: {exc}", file=sys.stderr)
        return 1


def _handle_generate(args: argparse.Namespace) -> int:
    """Handle generate subcommand."""
    try:
        client = GeminiSpeechClient(
            default_model=args.model,
            default_voice=args.voice,
        )

        res = client.generate_speech(
            text=args.text,
            model=args.model,
            voice_name=args.voice,
            voice_style_prompt=args.style,
            expressions=args.expressions,
            output_path=args.output,
        )

        if args.json:
            result = {
                "success": True,
                "output_path": os.path.abspath(res.output_path or args.output),
                "size_bytes": res.size_bytes,
                "mime_type": res.mime_type,
                "model": res.model_used,
                "voice": res.voice_used,
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0

        print("\nSpeech Synthesis Successful!")
        print(f"  Output Path: {os.path.abspath(res.output_path or args.output)}")
        print(f"  File Size:   {res.size_bytes:,} bytes")
        print(f"  Model:       {res.model_used}")
        print(f"  Voice:       {res.voice_used}")
        return 0

    except Exception as exc:
        if args.json:
            print(json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False))
        else:
            print(f"Synthesis failed: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser with all required subcommands."""
    parser = argparse.ArgumentParser(
        prog="python -m tts",
        description="High-quality Text-to-Speech CLI powered by Google AI Studio / Gemini APIs.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Subcommand: generate
    gen_parser = subparsers.add_parser(
        "generate",
        help="Synthesize speech from input text.",
        description="Synthesize speech from text and save output audio.",
    )
    gen_parser.add_argument(
        "text",
        type=str,
        help="Target text or dialogue to synthesize.",
    )
    gen_parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="output.wav",
        help="Path to output audio file destination (default: output.wav).",
    )
    gen_parser.add_argument(
        "-v",
        "--voice",
        type=str,
        default="Aoede",
        help="Voice persona name (default: Aoede).",
    )
    gen_parser.add_argument(
        "-m",
        "--model",
        type=str,
        default="gemini-3.8-flash-tts",
        help="Target Gemini speech model ID (default: gemini-3.8-flash-tts).",
    )
    gen_parser.add_argument(
        "-s",
        "--style",
        type=str,
        default="Natural, expressive speech",
        help="Voice style prompt describing tone, mood, and pacing.",
    )
    gen_parser.add_argument(
        "-e",
        "--expressions",
        type=str,
        default=None,
        help="Emotion or delivery cues (e.g. 'warm, cheerful').",
    )
    gen_parser.add_argument(
        "--json",
        action="store_true",
        help="Output result strictly in clean JSON format for automated agents/tools.",
    )

    # Subcommand: list-voices
    voices_parser = subparsers.add_parser(
        "list-voices",
        help="List available preset voice personas and profiles.",
        description="List supported preset voice identities with tone characteristics.",
    )
    voices_parser.add_argument(
        "--json",
        action="store_true",
        help="Output voices catalog strictly in clean JSON format.",
    )

    # Subcommand: list-models
    models_parser = subparsers.add_parser(
        "list-models",
        help="List speech/TTS-capable models from Gemini API.",
        description="Query Gemini API and filter for speech-generation models.",
    )
    models_parser.add_argument(
        "--json",
        action="store_true",
        help="Output models list strictly in clean JSON format.",
    )

    return parser


def main() -> None:
    """Main execution function."""
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "generate":
        sys.exit(_handle_generate(args))
    elif args.command == "list-voices":
        sys.exit(_handle_list_voices(args))
    elif args.command == "list-models":
        sys.exit(_handle_list_models(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
