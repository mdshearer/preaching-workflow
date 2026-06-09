"""Unit tests for in-place push + dispatch, using a recording fake for the
Notion API so no network is touched."""
import unittest
from unittest import mock

import notion_push


class InPlaceUpdateTests(unittest.TestCase):
    def test_update_issues_title_clear_then_append_and_never_creates(self):
        calls = []

        def fake_api(token, method, path, body=None, max_retries=5):
            calls.append((method, path.split("?")[0], body))
            if method == "GET" and "/children" in path:
                return {"results": [{"id": "blk1"}, {"id": "blk2"}],
                        "has_more": False}
            return {}

        with mock.patch.object(notion_push, "api_call", fake_api), \
             mock.patch.object(notion_push.time, "sleep", lambda *a, **k: None):
            notion_push.update_page_in_place(
                "tok", "page9", "05 — Homiletical", "# Hi\n\nBody text.")

        methods = [(m, p) for m, p, _ in calls]
        self.assertEqual(methods[0], ("PATCH", "/pages/page9"))      # title first
        self.assertIn(("GET", "/blocks/page9/children"), methods)    # list children
        self.assertIn(("DELETE", "/blocks/blk1"), methods)           # delete each
        self.assertIn(("DELETE", "/blocks/blk2"), methods)
        self.assertIn(("PATCH", "/blocks/page9/children"), methods)  # append new
        self.assertNotIn("POST", [m for m, _ in methods])            # never recreates


class PushStageDispatchTests(unittest.TestCase):
    def test_existing_title_updates_in_place(self):
        with mock.patch.object(notion_push, "update_page_in_place") as upd, \
             mock.patch.object(notion_push, "create_page") as crt:
            pid = notion_push.push_stage(
                "tok", "parent", "05 — Homiletical", "md",
                {"05 — Homiletical": {"id": "p5"}})
        upd.assert_called_once()
        crt.assert_not_called()
        self.assertEqual(pid, "p5")

    def test_absent_title_creates(self):
        with mock.patch.object(notion_push, "update_page_in_place") as upd, \
             mock.patch.object(notion_push, "create_page",
                               return_value="newid") as crt:
            pid = notion_push.push_stage("tok", "parent", "05 — Homiletical",
                                         "md", {})
        crt.assert_called_once()
        upd.assert_not_called()
        self.assertEqual(pid, "newid")


class ApiRetryTests(unittest.TestCase):
    def test_api_call_retries_on_connection_reset(self):
        class FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return b'{"ok": true}'

        calls = {"n": 0}

        def fake_urlopen(req, context=None, timeout=None):
            calls["n"] += 1
            if calls["n"] == 1:
                raise ConnectionResetError(54, "Connection reset by peer")
            return FakeResp()

        with mock.patch.object(notion_push.urllib.request, "urlopen",
                               fake_urlopen), \
             mock.patch.object(notion_push.time, "sleep", lambda *a, **k: None):
            result = notion_push.api_call("tok", "GET", "/x")

        self.assertEqual(result, {"ok": True})
        self.assertEqual(calls["n"], 2)  # one reset, one success


if __name__ == "__main__":
    unittest.main()
