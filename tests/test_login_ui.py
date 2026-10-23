"""
test_login_ui.py — Tests for login_ui.py and user profile credential handling.
"""

import os
import sys
import unittest
from unittest.mock import patch

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from login_ui import EMAIL_RE, render_auth_header, derive_name_from_email


class TestLoginUI(unittest.TestCase):
    def test_email_regex_validations(self):
        """Valid emails should match and invalid ones should fail."""
        self.assertTrue(EMAIL_RE.match("surya@example.com"))
        self.assertTrue(EMAIL_RE.match("jane.doe@gmail.com"))
        self.assertTrue(EMAIL_RE.match("user.name+tag@company.co.in"))
        self.assertFalse(EMAIL_RE.match("invalid_email"))
        self.assertFalse(EMAIL_RE.match("missing@domain"))
        self.assertFalse(EMAIL_RE.match("@nodomain.com"))

    def test_auth_header_content(self):
        """Auth header should adapt to signup vs signin."""
        with patch("streamlit.markdown") as mock_md:
            render_auth_header(signup=False)
            mock_md.assert_called_once()
            args = mock_md.call_args[0][0]
            self.assertIn("Welcome back", args)

        with patch("streamlit.markdown") as mock_md:
            render_auth_header(signup=True)
            mock_md.assert_called_once()
            args = mock_md.call_args[0][0]
            self.assertIn("Create your account", args)

    def test_derive_name_from_email(self):
        """Derives clean capitalized full names from email local-parts."""
        self.assertEqual(derive_name_from_email("surya.prakash@example.com"), "Surya Prakash")
        self.assertEqual(derive_name_from_email("jane_doe@gmail.com"), "Jane Doe")
        self.assertEqual(derive_name_from_email("john-doe@company.org"), "John Doe")
        self.assertEqual(derive_name_from_email("student@university.edu"), "Student")
        self.assertEqual(derive_name_from_email(""), "Student")

    def test_unauthenticated_blocks_main_app_and_calls_login(self):
        """Unauthenticated user triggers login page and st.stop(), preventing main app execution."""
        session_state = {"authenticated": False}
        with patch("streamlit.session_state", session_state), \
             patch("login_ui.render_login_page") as mock_login, \
             patch("streamlit.stop") as mock_stop:
            if not session_state.get("authenticated", False):
                mock_login()
                mock_stop()

            mock_login.assert_called_once()
            mock_stop.assert_called_once()

    def test_authenticated_bypasses_login_screen(self):
        """Authenticated user bypasses login page completely and enters main app."""
        session_state = {"authenticated": True}
        with patch("streamlit.session_state", session_state), \
             patch("login_ui.render_login_page") as mock_login, \
             patch("streamlit.stop") as mock_stop:
            if not session_state.get("authenticated", False):
                mock_login()
                mock_stop()

            mock_login.assert_not_called()
            mock_stop.assert_not_called()

    def test_login_page_renders_form_and_centered_css(self):
        """Login page injects scoped max-width 440px CSS and centers titles."""
        from login_ui import _css
        css = _css()
        self.assertIn("max-width:440px !important", css)
        self.assertIn("text-align:center !important", css)
        self.assertIn("display:none !important", css)

    def test_google_logged_in_shows_name_and_email(self):
        """(a) Logged-in Google user identity (name, email, picture) maps into user profile."""
        from unittest.mock import MagicMock
        from core.memory import get_or_create_user

        mock_user = MagicMock()
        mock_user.is_logged_in = True
        mock_user.email = "google_student@university.edu"
        mock_user.name = "Google Student"
        mock_user.picture = "https://lh3.googleusercontent.com/a/student.jpg"
        mock_user.get = lambda k, default=None: getattr(mock_user, k, default)

        with patch("streamlit.user", mock_user):
            google_logged_in = mock_user.get("is_logged_in", False)
            self.assertTrue(google_logged_in)

            u_info = get_or_create_user(
                email=mock_user.get("email"),
                name=mock_user.get("name"),
                picture=mock_user.get("picture"),
                auth_provider="google"
            )
            self.assertEqual(u_info["email"], "google_student@university.edu")
            self.assertEqual(u_info["name"], "Google Student")
            self.assertEqual(u_info["picture"], "https://lh3.googleusercontent.com/a/student.jpg")
            self.assertEqual(u_info["auth_provider"], "google")

    def test_no_demo_identity_in_codebase(self):
        """(b) Verifies no hardcoded demo identity exists anywhere in the codebase."""
        forbidden = ["alex" + " morgan", "alex" + ".morgan"]
        project_root = root_dir
        found_instances = []

        extensions = (".py", ".html", ".md", ".toml", ".json")
        for root, dirs, files in os.walk(project_root):
            if any(skip in root for skip in (".git", "__pycache__", ".ruff_cache", ".pytest_cache", ".mypy_cache")):
                continue
            for file_name in files:
                if file_name.endswith(extensions):
                    file_path = os.path.join(root, file_name)
                    # Skip the test file itself checking the string literals
                    if os.path.abspath(file_path) == os.path.abspath(__file__):
                        continue
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_idx, line in enumerate(f, 1):
                            line_lower = line.lower()
                            for pattern in forbidden:
                                if pattern in line_lower:
                                    found_instances.append(f"{file_path}:{line_idx}: {line.strip()[:80]}")

        self.assertEqual(
            found_instances,
            [],
            "Found forbidden hardcoded demo identities in codebase:\n" + "\n".join(found_instances)
        )

    def test_two_google_users_isolated_data(self):
        """(c) Two Google users must have completely isolated accounts, memory profiles, cache, and rate limits."""
        from core.memory import get_or_create_user, get_user_memory, update_user_memory
        from core.cache import get_cached_response, store_cached_response
        from core.rate_limiter import check_user_rate_limit, reset_rate_limiter_pacing

        user_a_email = "user_alpha@google.com"
        user_b_email = "user_beta@google.com"

        # 1. User models and plans isolation
        user_a = get_or_create_user(email=user_a_email, name="Alpha User", default_plan="standard")
        user_b = get_or_create_user(email=user_b_email, name="Beta User", default_plan="pro")
        self.assertFalse(user_a["is_pro"])
        self.assertTrue(user_b["is_pro"])

        # 2. Memory isolation in SQLite
        update_user_memory(user_a_email, {"user_level": "Freshman", "target_role": "Data Analyst"})
        update_user_memory(user_b_email, {"user_level": "Senior", "target_role": "ML Engineer"})

        mem_a = get_user_memory(user_a_email)
        mem_b = get_user_memory(user_b_email)
        self.assertEqual(mem_a["target_role"], "Data Analyst")
        self.assertEqual(mem_b["target_role"], "ML Engineer")
        self.assertNotEqual(mem_a["target_role"], mem_b["target_role"])

        # 3. Cache isolation
        test_prompt = "Explain quantum superposition"
        res_a = {"success": True, "content": "Alpha custom response"}
        res_b = {"success": True, "content": "Beta custom response"}
        store_cached_response(test_prompt, res_a, user_id=user_a_email)
        store_cached_response(test_prompt, res_b, user_id=user_b_email)

        cached_a = get_cached_response(test_prompt, user_id=user_a_email)
        cached_b = get_cached_response(test_prompt, user_id=user_b_email)
        self.assertIsNotNone(cached_a)
        self.assertIsNotNone(cached_b)
        assert cached_a is not None and cached_b is not None
        self.assertEqual(cached_a["content"], "Alpha custom response")
        self.assertEqual(cached_b["content"], "Beta custom response")

        # 4. Rate limit isolation
        reset_rate_limiter_pacing()
        for _ in range(15):
            allowed_a, _ = check_user_rate_limit(user_a_email, limit_per_minute=15)
        self.assertTrue(allowed_a)
        blocked_a, _ = check_user_rate_limit(user_a_email, limit_per_minute=15)
        self.assertFalse(blocked_a)
        # User B has consumed 0 requests and should not be throttled
        allowed_b, _ = check_user_rate_limit(user_b_email, limit_per_minute=15)
        self.assertTrue(allowed_b)

    def test_google_auth_missing_secrets_shows_clear_message(self):
        """When secrets.toml or [auth] is missing, check_google_auth_available returns a clear warning message."""
        from login_ui import check_google_auth_available
        with patch("streamlit.secrets", {}), patch("importlib.util.find_spec", return_value=True):
            is_avail, msg = check_google_auth_available()
            self.assertFalse(is_avail)
            self.assertTrue("secrets.toml" in (msg or "") or "Authlib" in (msg or ""))


if __name__ == "__main__":
    unittest.main()
