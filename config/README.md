# Configuration & Production Principles (`config/`)

This directory manages persistent configurations and customizable production principles for the AI video creation engine.

## Files
- `production_principles.json`: Persistent JSON store containing voiceover guidelines, architectural narrative rules, audio ducking levels, and video overlay preferences.
- `production_principles_manager.py`: Python module providing thread-safe reading, writing, resetting, and prompt-injection helpers (`load_principles`, `save_principles`, `reset_principles`, `build_vision_prompt_principles`, `build_tts_style_principles`).
