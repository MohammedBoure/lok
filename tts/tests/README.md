# Tests Directory (`tests`)

Unit tests for verifying key rotation, failover mechanics, audio format conversion, and client logic.

## Files
- [`test_key_manager.py`](test_key_manager.py): Validates multi-key loading, deduplication, rotation upon HTTP 429, permanent disablement upon 401/403, and cooldown triggers.
- [`test_client.py`](test_client.py): Validates voice profile catalog lookups, PCM-to-WAV audio conversion, and response payload parsing.
- [`test_cli.py`](test_cli.py): Validates command-line interface arguments, subcommands (`generate`, `list-voices`, `list-models`), `--json` formatting, and exit codes.
