# Video Production Request

## Overview
Create an engaging, polished cinematic short featuring woodland wildlife.

## Source Footage
- `inputs/source_fox_cub.mp4`: Young fox exploring the woodland.
- `inputs/source_squirrel.mp4`: Energetic squirrel foraging among autumn leaves.

## Narration & Story
**Tone**: Warm, curious, documentary style.
**Script**:
> "Deep in the heart of the golden autumn forest, a young fox cub takes his first adventurous steps into the quiet wild. Nearby, a spirited baby squirrel dashes through the fallen leaves, celebrating another bright morning in nature's sanctuary."

## Post-Production Requirements
1. Extract visual keyframes using `mcp_get_image_from_video` tool to analyze visual pacing and timestamps.
2. Generate professional voiceover narration using the local `tts` module (`python -m tts generate`).
3. Select and splice optimal segments from the source footage matching the narration pacing.
4. Duck background music or ambiance under the voiceover.
5. Export final video to `outputs/final_cut.mp4`.
6. Provide execution summary with timestamps, frame indices, and audio parameters.
