"""API Key Management, Environment Configuration, and Automatic Failover Rotation."""

import logging
import os
import random
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from .exceptions import ConfigurationError, KeyPoolExhaustedError

try:
    from dotenv import find_dotenv, load_dotenv
except ImportError:
    find_dotenv = None

    def load_dotenv(dotenv_path: Optional[str] = None) -> bool:
        """Lightweight fallback .env loader using standard library."""
        module_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        paths_to_check = (
            [dotenv_path]
            if dotenv_path
            else [
                os.path.join(module_dir, ".env"),
                os.path.join(os.getcwd(), ".env"),
                os.path.join(os.getcwd(), "test_generate_sound", ".env"),
                ".env",
            ]
        )
        for p in paths_to_check:
            if p and os.path.isfile(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        for line in f:
                            cleaned = line.strip()
                            if cleaned and not cleaned.startswith("#") and "=" in cleaned:
                                k, v = cleaned.split("=", 1)
                                k, v = k.strip(), v.strip().strip("\"'")
                                if k not in os.environ:
                                    os.environ[k] = v
                    return True
                except OSError:
                    pass
        return False

logger = logging.getLogger("gemini_speech.key_manager")


@dataclass
class KeyState:
    """Tracks runtime health and cooldown state for an individual API key."""

    key: str
    index: int
    failure_count: int = 0
    cooldown_until: float = 0.0
    is_permanently_disabled: bool = False
    total_requests: int = 0
    successful_requests: int = 0

    @property
    def is_available(self) -> bool:
        """Check if the key is available for making requests."""
        if self.is_permanently_disabled:
            return False
        return time.monotonic() >= self.cooldown_until

    @property
    def remaining_cooldown(self) -> float:
        """Return remaining seconds in cooldown state."""
        remaining = self.cooldown_until - time.monotonic()
        return max(0.0, remaining)

    @property
    def masked_key(self) -> str:
        """Return masked key for safe diagnostic logging."""
        if len(self.key) <= 8:
            return "***"
        return f"{self.key[:4]}...{self.key[-4:]}"


class KeyManager:
    """Manages an elastic pool of API keys with automatic failover, health tracking, and cooldown rotation."""

    def __init__(
        self,
        api_keys: Optional[List[str]] = None,
        base_cooldown_seconds: float = 60.0,
        env_file: Optional[str] = None,
    ) -> None:
        self.base_cooldown_seconds = base_cooldown_seconds
        self._current_index = 0
        raw_keys = api_keys if api_keys is not None else self._discover_keys(env_file)

        # Deduplicate while preserving order
        deduped: List[str] = []
        for k in raw_keys:
            cleaned = k.strip()
            if cleaned and cleaned not in deduped:
                deduped.append(cleaned)

        if not deduped:
            raise ConfigurationError(
                "No Gemini API keys found. Provide them via constructor or set "
                "GEMINI_API_KEY, GEMINI_API_KEYS, or GEMINI_API_KEY_1..N in .env"
            )

        self._pool: List[KeyState] = [
            KeyState(key=k, index=idx) for idx, k in enumerate(deduped)
        ]
        logger.info("Initialized KeyManager with %d API key(s).", len(self._pool))

    @staticmethod
    def _discover_keys(env_file: Optional[str] = None) -> List[str]:
        """Discover API keys from environment and .env files using multiple standard formats."""
        if env_file:
            load_dotenv(env_file)
        else:
            module_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
            if os.path.isfile(module_env):
                load_dotenv(module_env)
            if callable(find_dotenv):
                dotenv_path = find_dotenv(usecwd=True)
                if dotenv_path and dotenv_path != module_env:
                    load_dotenv(dotenv_path)
            else:
                load_dotenv()

        discovered: List[str] = []

        # Format 1: Comma-separated list in GEMINI_API_KEYS
        comma_separated = os.getenv("GEMINI_API_KEYS")
        if comma_separated:
            for item in comma_separated.split(","):
                val = item.strip()
                if val:
                    discovered.append(val)

        # Format 2: Sequentially indexed keys (GEMINI_API_KEY_1, GEMINI_API_KEY_2, ...)
        index = 1
        while True:
            indexed_key = os.getenv(f"GEMINI_API_KEY_{index}")
            if not indexed_key:
                break
            val = indexed_key.strip()
            if val:
                discovered.append(val)
            index += 1

        # Format 3: Single standard key (GEMINI_API_KEY)
        single_key = os.getenv("GEMINI_API_KEY")
        if single_key and single_key.strip():
            discovered.append(single_key.strip())

        return discovered

    def get_active_key(self) -> KeyState:
        """Select the next available healthy key from the pool.

        Raises:
            KeyPoolExhaustedError: When all keys are on active cooldown or permanently disabled.
        """
        pool_size = len(self._pool)
        now = time.monotonic()

        # Check keys starting from current index
        for offset in range(pool_size):
            candidate_idx = (self._current_index + offset) % pool_size
            candidate = self._pool[candidate_idx]
            if candidate.is_available:
                self._current_index = candidate_idx
                candidate.total_requests += 1
                return candidate

        # If no key is immediately available, calculate shortest remaining cooldown
        active_candidates = [k for k in self._pool if not k.is_permanently_disabled]
        if not active_candidates:
            raise KeyPoolExhaustedError("All API keys have been permanently disabled due to authentication errors.")

        min_cooldown = min(k.remaining_cooldown for k in active_candidates)
        raise KeyPoolExhaustedError(
            f"All {len(self._pool)} API keys are currently on cooldown. "
            f"Next key will become available in {min_cooldown:.1f}s."
        )

    def mark_success(self, key_index: int) -> None:
        """Acknowledge successful request on the given key, reducing its failure penalty."""
        if 0 <= key_index < len(self._pool):
            state = self._pool[key_index]
            state.successful_requests += 1
            state.failure_count = max(0, state.failure_count - 1)

    def mark_failure(
        self,
        key_index: int,
        status_code: Optional[int],
        is_permanent: bool = False,
        error_message: str = "",
    ) -> None:
        """Put the key on cooldown and advance rotation index."""
        if not (0 <= key_index < len(self._pool)):
            return

        state = self._pool[key_index]
        state.failure_count += 1

        if is_permanent or status_code in (401, 403) and "invalid" in error_message.lower():
            state.is_permanently_disabled = True
            logger.error(
                "Key #%d (%s) permanently disabled due to authentication failure: %s",
                key_index,
                state.masked_key,
                error_message,
            )
        else:
            # Exponential backoff on repeated failures with slight jitter
            backoff_multiplier = 2 ** min(state.failure_count - 1, 4)
            jitter = random.uniform(0.8, 1.2)
            duration = self.base_cooldown_seconds * backoff_multiplier * jitter
            state.cooldown_until = time.monotonic() + duration
            logger.warning(
                "Key #%d (%s) placed on cooldown for %.1fs (status=%s, failures=%d). Reason: %s",
                key_index,
                state.masked_key,
                duration,
                status_code,
                state.failure_count,
                error_message,
            )

        # Rotate to the next slot
        self._current_index = (key_index + 1) % len(self._pool)

    def reset_cooldowns(self) -> None:
        """Reset temporary cooldowns across all non-permanently disabled keys."""
        for state in self._pool:
            if not state.is_permanently_disabled:
                state.cooldown_until = 0.0
                state.failure_count = 0

    def get_pool_status(self) -> List[Dict[str, object]]:
        """Return diagnostic health status across all keys."""
        return [
            {
                "index": k.index,
                "masked_key": k.masked_key,
                "is_available": k.is_available,
                "remaining_cooldown_sec": round(k.remaining_cooldown, 1),
                "failure_count": k.failure_count,
                "is_permanently_disabled": k.is_permanently_disabled,
                "total_requests": k.total_requests,
                "successful_requests": k.successful_requests,
            }
            for k in self._pool
        ]

    @property
    def total_keys(self) -> int:
        """Total number of configured keys in the pool."""
        return len(self._pool)

