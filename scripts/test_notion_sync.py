"""Unit tests for the pure sync-decision helpers (no network)."""
import unittest

from notion_sync import decide_action, notion_needs_fetch


class DecideActionTests(unittest.TestCase):
    def test_neither_changed_is_insync(self):
        self.assertEqual(decide_action(False, False, False, False), "insync")

    def test_repo_only_pushes(self):
        self.assertEqual(decide_action(True, False, False, False), "push")

    def test_notion_only_pulls(self):
        self.assertEqual(decide_action(False, True, False, False), "pull")

    def test_both_changed_is_conflict(self):
        self.assertEqual(decide_action(True, True, False, False), "conflict")

    def test_force_repo_resolves_conflict_to_push(self):
        self.assertEqual(decide_action(True, True, True, False), "push")

    def test_force_notion_resolves_conflict_to_pull(self):
        self.assertEqual(decide_action(True, True, False, True), "pull")


class NeedsFetchTests(unittest.TestCase):
    def test_timestamp_equal_repo_unchanged_skips_fetch(self):
        self.assertFalse(notion_needs_fetch(True, False))

    def test_timestamp_differs_forces_fetch(self):
        self.assertTrue(notion_needs_fetch(False, False))

    def test_repo_changed_forces_fetch_even_if_timestamp_equal(self):
        self.assertTrue(notion_needs_fetch(True, True))


if __name__ == "__main__":
    unittest.main()
