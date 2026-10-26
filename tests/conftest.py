import os
import sys
from pathlib import Path

# Set dummy API key for testing environment if not present
os.environ.setdefault("GEMINI_API_KEY", "dummy_test_key_for_testing")

# Add project root to sys.path so tests can import local modules
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
