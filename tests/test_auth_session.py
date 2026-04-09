import unittest
from unittest.mock import patch

from werkzeug.security import generate_password_hash

import app as app_module


class AuthSessionTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()

    def test_login_route_redirects_to_modal(self):
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/?open_login=1&auth_tab=login", response.location)

    def test_login_success_sets_session(self):
        fake_user = {
            "id": "11111111-1111-1111-1111-111111111111",
            "name": "Alice",
            "email": "alice@example.com",
            "password_hash": generate_password_hash("secret123"),
            "avatar_seed": "sky",
        }

        with (
            patch.object(app_module, "is_supabase_comments_enabled", return_value=True),
            patch.object(app_module, "get_user_by_email_from_supabase", return_value=fake_user),
        ):
            response = self.client.post(
                "/auth/login",
                data={"email": "alice@example.com", "password": "secret123"},
            )

        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as session:
            self.assertEqual(session.get("user_id"), fake_user["id"])
            self.assertEqual(session.get("user_name"), fake_user["name"])
            self.assertEqual(session.get("avatar_seed"), fake_user["avatar_seed"])

    def test_comment_requires_login(self):
        response = self.client.post(
            "/faq/1/comment",
            data={"content": "test comment"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/faq/1?open_login=1&auth_tab=login", response.location)

    def test_update_profile_persists_to_supabase(self):
        with self.client.session_transaction() as session:
            session["user_id"] = "11111111-1111-1111-1111-111111111111"
            session["user_name"] = "Alice"
            session["user_email"] = "alice@example.com"
            session["avatar_seed"] = "sky"

        with patch.object(
            app_module,
            "update_user_profile_in_supabase",
            return_value={"name": "Alice New", "avatar_seed": "rose"},
        ) as update_profile:
            response = self.client.post(
                "/profile",
                data={"user_name": "Alice New", "avatar_seed": "rose"},
            )

        self.assertEqual(response.status_code, 302)
        update_profile.assert_called_once_with(
            "11111111-1111-1111-1111-111111111111",
            "Alice New",
            "rose",
        )
        with self.client.session_transaction() as session:
            self.assertEqual(session.get("user_name"), "Alice New")
            self.assertEqual(session.get("avatar_seed"), "rose")

    def test_update_profile_shows_error_when_supabase_fails(self):
        with self.client.session_transaction() as session:
            session["user_id"] = "11111111-1111-1111-1111-111111111111"
            session["user_name"] = "Alice"
            session["user_email"] = "alice@example.com"
            session["avatar_seed"] = "sky"

        with patch.object(
            app_module,
            "update_user_profile_in_supabase",
            side_effect=RuntimeError("更新资料失败"),
        ):
            response = self.client.post(
                "/profile",
                data={"user_name": "Alice New", "avatar_seed": "rose"},
                follow_redirects=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("更新资料失败", response.get_data(as_text=True))

    def test_auth_login_error_redirects_with_modal_flag(self):
        with patch.object(app_module, "is_supabase_comments_enabled", return_value=True):
            response = self.client.post(
                "/auth/login",
                data={"email": "", "password": ""},
                headers={"Referer": "http://localhost/guide/prep?step=1"},
            )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/guide/prep?step=1&open_login=1&auth_tab=login", response.location)

    def test_auth_register_error_redirects_with_register_tab(self):
        with patch.object(app_module, "is_supabase_comments_enabled", return_value=True):
            response = self.client.post(
                "/auth/register",
                data={"name": "", "email": "bad", "password": "123"},
                headers={"Referer": "http://localhost/programs"},
            )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/programs?open_login=1&auth_tab=register", response.location)


if __name__ == "__main__":
    unittest.main()
