import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gemini_speech.config import KeyManager
from gemini_speech.exceptions import ConfigurationError, KeyPoolExhaustedError


class TestKeyManager(unittest.TestCase):

    def test_explicit_keys_deduplication(self) -> None:
        manager = KeyManager(api_keys=["keyA", "keyB", "keyA", "keyC"])
        self.assertEqual(manager.total_keys, 3)
        self.assertEqual(manager._pool[0].key, "keyA")
        self.assertEqual(manager._pool[1].key, "keyB")
        self.assertEqual(manager._pool[2].key, "keyC")

    def test_empty_keys_raises_configuration_error(self) -> None:
        with self.assertRaises(ConfigurationError):
            KeyManager(api_keys=[])

    def test_key_rotation_on_failure(self) -> None:
        manager = KeyManager(api_keys=["k1", "k2"], base_cooldown_seconds=10.0)
        first_key = manager.get_active_key()
        self.assertEqual(first_key.key, "k1")
        self.assertEqual(first_key.index, 0)

        # Mark failure on k1
        manager.mark_failure(key_index=0, status_code=429, error_message="Rate limit")
        self.assertFalse(first_key.is_available)

        # Next active key should be k2
        second_key = manager.get_active_key()
        self.assertEqual(second_key.key, "k2")
        self.assertEqual(second_key.index, 1)

    def test_all_keys_exhausted_raises_exception(self) -> None:
        manager = KeyManager(api_keys=["k1"], base_cooldown_seconds=10.0)
        manager.mark_failure(key_index=0, status_code=429, error_message="Rate limit")

        with self.assertRaises(KeyPoolExhaustedError):
            manager.get_active_key()

    def test_permanent_auth_failure_disables_key(self) -> None:
        manager = KeyManager(api_keys=["k1", "k2"], base_cooldown_seconds=10.0)
        manager.mark_failure(key_index=0, status_code=401, is_permanent=True, error_message="API key not valid")
        self.assertTrue(manager._pool[0].is_permanently_disabled)

        active = manager.get_active_key()
        self.assertEqual(active.key, "k2")


if __name__ == "__main__":
    unittest.main()
