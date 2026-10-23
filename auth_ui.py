"""
auth_ui.py — Backward compatibility wrapper delegating to login_ui.py.
"""
from login_ui import (
    inject_login_css,
    render_auth_header,
    render_login_page,
    render_login_page as render_auth_page,
    main
)

__all__ = [
    "inject_login_css",
    "render_auth_header",
    "render_login_page",
    "render_auth_page",
    "main",
]
