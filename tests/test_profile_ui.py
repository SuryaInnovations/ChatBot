"""
test_profile_ui.py — Tests for the Eduvyn Student Dashboard Profile Button and Popup.
Verifies all elements, styles, scripts, and interactions required by the user specification.
"""

import os
import sys
import unittest

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from profile_ui import (
    get_profile_widget_html,
    get_profile_widget_css,
    get_profile_widget_script,
    compute_initials
)


class TestProfileUI(unittest.TestCase):
    def setUp(self):
        self.html = get_profile_widget_html(
            user_name="Jane Doe",
            user_email="jane.doe@example.com",
            initials="JD",
            is_pro=True
        )
        self.css = get_profile_widget_css()
        self.js = get_profile_widget_script()

    def test_profile_button_structure(self):
        """Profile button must be small circular button with avatar icon and online-status dot."""
        self.assertIn('id="eduvynProfileBtn"', self.html)
        self.assertIn('class="eduvyn-profile-btn"', self.html)
        # Check avatar icon inside button
        self.assertIn('class="eduvyn-btn-icon-wrap"', self.html)
        # Check green status dot
        self.assertIn('class="eduvyn-btn-status-dot"', self.html)
        self.assertIn('title="Online"', self.html)

    def test_popup_card_elements(self):
        """Popup card must contain top avatar, green dot, name, PRO badge, initials, email, and sign out."""
        # Clean circular profile avatar/icon at top
        self.assertIn('class="eduvyn-card-avatar-wrap"', self.html)
        self.assertIn('class="eduvyn-card-avatar"', self.html)
        # Small green online-status dot
        self.assertIn('class="eduvyn-card-online-dot"', self.html)
        # Profile name: Jane Doe PRO
        self.assertIn('Jane Doe', self.html)
        self.assertIn('PRO', self.html)
        self.assertIn('class="eduvyn-pro-badge"', self.html)
        # User icon + JD
        self.assertIn('JD', self.html)
        self.assertIn('class="eduvyn-details-card"', self.html)
        # Email icon + jane.doe@example.com
        self.assertIn('jane.doe@example.com', self.html)
        # Rounded Sign out button with logout icon
        self.assertIn('id="eduvynSignoutBtn"', self.html)
        self.assertIn('class="eduvyn-signout-btn"', self.html)
        self.assertIn('Sign out', self.html)

    def test_css_styling_and_positioning(self):
        """CSS must ensure bottom-right fixed positioning, flat 2D style, animations, and responsiveness."""
        # Fixed at top-right corner
        self.assertIn('position: fixed', self.css)
        self.assertIn('top: 20px', self.css)
        self.assertIn('right: 24px', self.css)
        # Clean blue border (#2F80ED)
        self.assertIn('#2F80ED', self.css)
        # Small green online-status dot (#10B981)
        self.assertIn('#10B981', self.css)
        # Subtle shadow
        self.assertIn('box-shadow', self.css)
        # Smooth hover effect
        self.assertIn(':hover', self.css)
        self.assertIn('transform: translateY(-2px)', self.css)
        # Subtle fade + slide animation
        self.assertIn('transform: translateY(-10px)', self.css)
        self.assertIn('transform: translateY(0)', self.css)
        self.assertIn('opacity: 0', self.css)
        self.assertIn('opacity: 1', self.css)
        # Responsive rules
        self.assertIn('@media (max-width: 640px)', self.css)
        self.assertIn('calc(100vw - 28px)', self.css)
        # Off-screen interop trigger buttons
        self.assertIn('st-key-btn_edit_profile', self.css)
        self.assertIn('st-key-btn_signout', self.css)

    def test_javascript_interactions(self):
        """JS must handle button toggle, click outside to close, ESC to close, viewport bounds, and signout."""
        # Button toggle
        self.assertIn('openPopup', self.js)
        self.assertIn('closePopup', self.js)
        # Outside click
        self.assertIn('contains(e.target)', self.js)
        # Escape key
        self.assertIn('Escape', self.js)
        # Viewport boundaries
        self.assertIn('fitWithinViewport', self.js)
        self.assertIn('innerWidth', self.js)
        self.assertIn('innerHeight', self.js)
        # Signout & Edit triggers
        self.assertIn('st-key-btn_signout', self.js)
        self.assertIn('st-key-btn_edit_profile', self.js)

    def test_dynamic_username_and_email(self):
        """Card must dynamically display the provided user's username and email."""
        custom_html = get_profile_widget_html(
            user_name="Surya Prakash",
            user_email="surya.prakash@example.com",
            initials="SP",
            is_pro=True
        )
        self.assertIn("Surya Prakash", custom_html)
        self.assertIn("surya.prakash@example.com", custom_html)
        self.assertIn("SP", custom_html)
        self.assertIn("PRO", custom_html)

    def test_image2_reference_icon_presence(self):
        """Top-right button must render the profile avatar icon matching Image 2 reference."""
        self.assertIn('class="eduvyn-btn-icon-wrap"', self.html)
        # Verify image or icon tag inside button
        has_img = 'class="eduvyn-btn-profile-img"' in self.html
        has_svg = 'stroke="#8B5CF6"' in self.html or 'stroke="#2F80ED"' in self.html
        self.assertTrue(has_img or has_svg)

    def test_guaranteed_top_right_visibility(self):
        """CSS must ensure 100% visibility with top-level z-index and pointer-events."""
        self.assertIn('z-index: 999999999', self.css)
        self.assertIn('pointer-events: auto', self.css)
        self.assertIn('visibility: visible', self.css)
        self.assertIn('opacity: 1', self.css)

    def test_edit_profile_action_present(self):
        """Popup card must contain Edit Profile action for changing username and email."""
        self.assertIn('id="eduvynEditProfileBtn"', self.html)
        self.assertIn('Edit Profile', self.html)

    def test_sidebar_toggle_button_script_presence(self):
        """JS must define the sidebar toggle button at the edge with chevron and hamburger icons."""
        self.assertIn('eduvynSidebarToggleBtn', self.js)
        self.assertIn('icon-chevron', self.js)
        self.assertIn('icon-hamburger', self.js)
        self.assertIn('is-open', self.js)
        self.assertIn('is-closed', self.js)

    def test_pro_badge_hidden_when_not_pro(self):
        """When user plan is standard/free (is_pro=False), PRO badge must NOT appear."""
        html = get_profile_widget_html(
            user_name="Free User",
            user_email="free@example.com",
            is_pro=False
        )
        self.assertNotIn('class="eduvyn-pro-badge"', html)
        self.assertNotIn('>PRO<', html)

    def test_picture_renders_in_avatar_and_button(self):
        """When a real picture URL is available, avatar image tags must render."""
        pic_url = "https://lh3.googleusercontent.com/a/test-avatar.jpg"
        html = get_profile_widget_html(
            user_name="Google User",
            user_email="google.user@gmail.com",
            picture=pic_url
        )
        self.assertIn(f'<img src="{pic_url}" class="eduvyn-card-avatar-img"', html)
        self.assertIn(f'<img src="{pic_url}" class="eduvyn-btn-profile-img"', html)

    def test_compute_initials(self):
        """Initials must be accurately computed from full names."""
        self.assertEqual(compute_initials("Jane Doe"), "JD")
        self.assertEqual(compute_initials("Surya Prakash"), "SP")
        self.assertEqual(compute_initials("Alice"), "AL")
        self.assertEqual(compute_initials(""), "U")
        self.assertEqual(compute_initials("   "), "U")


if __name__ == '__main__':
    unittest.main()
