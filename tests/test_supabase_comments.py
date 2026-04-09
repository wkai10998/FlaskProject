import unittest
from unittest.mock import patch

import app as app_module


class SupabaseCommentsTestCase(unittest.TestCase):
    def test_list_comments_uses_supabase(self):
        expected_rows = [
            {
                "id": 1,
                "user_name": "Alice",
                "avatar_seed": "sky",
                "content": "Test comment",
                "created_at": "2026-04-09 20:00",
            }
        ]

        with (
            patch.object(app_module, "is_supabase_comments_enabled", return_value=True),
            patch.object(app_module, "list_comments_from_supabase", return_value=expected_rows) as supabase_list,
        ):
            rows = app_module.list_comments("faq", "1")

        self.assertEqual(rows, expected_rows)
        supabase_list.assert_called_once_with("faq", "1")

    def test_list_comments_returns_empty_without_supabase_config(self):
        with patch.object(app_module, "is_supabase_comments_enabled", return_value=False):
            rows = app_module.list_comments("faq", "1")
        self.assertEqual(rows, [])

    def test_create_comment_uses_supabase(self):
        with (
            patch.object(app_module, "is_supabase_comments_enabled", return_value=True),
            patch.object(app_module, "create_comment_in_supabase") as supabase_create,
            patch.object(
                app_module,
                "get_current_user",
                return_value={"name": "Alice", "avatar_seed": "sky", "initial": "A"},
            ),
        ):
            app_module.create_comment("faq", "1", "New comment")

        args = supabase_create.call_args.args
        self.assertEqual(args[0], "faq")
        self.assertEqual(args[1], "1")
        self.assertEqual(args[2], "Alice")
        self.assertEqual(args[3], "sky")
        self.assertEqual(args[4], "New comment")
        self.assertRegex(args[5], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")

    def test_create_comment_raises_when_supabase_not_configured(self):
        with (
            patch.object(app_module, "is_supabase_comments_enabled", return_value=False),
            patch.object(
                app_module,
                "get_current_user",
                side_effect=AssertionError("should fail before reading request-bound user"),
            ),
        ):
            with self.assertRaises(ValueError):
                app_module.create_comment("faq", "1", "New comment")

    def test_create_comment_rejects_empty_content(self):
        with self.assertRaises(ValueError):
            app_module.create_comment("faq", "1", "   ")


if __name__ == "__main__":
    unittest.main()
