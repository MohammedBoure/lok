# Keyframes Output Directory (`outputs/keyframes/`)

## Architectural Role & Scope
This directory hosts extracted visual keyframe image assets (in JPEG format with visual quality `-q:v 2`) and the master JSON extraction index (`frame_index.json`). These assets are utilized by downstream editorial agents (`agy51`) for visual pacing, scene alignment, and video assembly, as well as verification agents (`agy100`).

## Itemized File Breakdown
- [`frame_index.json`](frame_index.json): Aggregate structured index containing complete technical metadata (duration, frame rate, resolution, codec, scene cut timestamps) and itemized lists of all extracted frames across processed source footage.
- `source_fox_cub_frame_*.jpg`: High-fidelity keyframes extracted from `inputs/source_fox_cub.mp4` sampled at 1.0 fps plus detected scene transitions (0.00s, 1.00s, 1.46s, 2.00s, 3.00s, 4.00s, 4.58s, 5.00s, 5.96s, 6.00s, 7.00s, 7.46s, 8.00s, 9.00s).
- `source_squirrel_frame_*.jpg`: High-fidelity keyframes extracted from `inputs/source_squirrel.mp4` sampled at 1.0 fps plus detected scene transitions (0.00s, 1.00s, 1.46s, 2.00s, 3.00s, 4.00s, 5.00s, 6.00s, 7.00s, 7.42s, 8.00s, 9.00s).

## Data Schema (`frame_index.json`)
```json
{
  "generated_at": "ISO-8601 timestamp",
  "output_dir": "outputs/keyframes",
  "videos": {
    "<video_id>": {
      "metadata": {
        "total_duration": 10.0,
        "frame_rate": 24.0,
        "resolution": "1280x720",
        "codec": "h264",
        "scene_timestamps": [0.0, 1.458, ...],
        "keyframe_timestamps": [...]
      },
      "frames": [
        {
          "frame_index": 0,
          "timestamp": 0.0,
          "file_path": "outputs/keyframes/source_fox_cub_frame_0000_000.00s.jpg",
          "resolution": "1280x720",
          "is_scene_transition": true,
          "file_size_bytes": 137028
        }
      ]
    }
  },
  "total_videos": 2,
  "total_frames": 26
}
```

## Regeneration Instructions
To regenerate or re-extract keyframes:
```bash
python3 -m frame_extractor --batch inputs/source_fox_cub.mp4 inputs/source_squirrel.mp4 --fps-sample 1.0 --output-dir outputs/keyframes --index-file outputs/keyframes/frame_index.json
```
