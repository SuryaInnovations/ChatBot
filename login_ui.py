"""
Polished login / sign-up page for a Streamlit app.

Run the demo:   streamlit run login_ui.py

To use in your app:
    from login_ui import inject_login_css, render_auth_header
    inject_login_css()          # once, at the top of your login page
    ... keep YOUR existing auth logic, just keep the widget keys below ...

Widget keys the CSS relies on (keep them):
    auth_mode (radio), auth_name, auth_email, auth_pw (text inputs),
    google_btn (button)
"""
import base64
import re
from typing import Optional, Dict, Any

import streamlit as st


# ------------------------------------------------------------------ icons
def _svg_uri(inner: str, stroke: str = "#9AA9C2") -> str:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        f'stroke="{stroke}" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round">{inner}</svg>'
    )
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


ICON_USER = _svg_uri('<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0116 0"/>')
ICON_MAIL = _svg_uri('<rect x="3" y="5" width="18" height="14" rx="3"/><path d="M3 8l9 6 9-6"/>')
ICON_LOCK = _svg_uri('<rect x="4" y="10" width="16" height="11" rx="3"/><path d="M8 10V7a4 4 0 018 0v3"/>')

_GOOGLE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">'
    '<path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9.1 3.6l6.8-6.8C35.8 2.4 30.3 0 24 0 '
    '14.6 0 6.5 5.4 2.6 13.2l7.9 6.1C12.4 13.6 17.7 9.5 24 9.5z"/>'
    '<path fill="#4285F4" d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.7c-.6 3-2.3 5.5-4.8 '
    '7.2l7.5 5.8c4.4-4.1 7.1-10.1 7.1-17.5z"/>'
    '<path fill="#FBBC05" d="M10.5 28.7c-.5-1.4-.8-3-.8-4.7s.3-3.3.8-4.7l-7.9-6.1C.9 16.4 '
    '0 20.1 0 24s.9 7.6 2.6 10.8l7.9-6.1z"/>'
    '<path fill="#34A853" d="M24 48c6.3 0 11.6-2.1 15.5-5.7l-7.5-5.8c-2.1 1.4-4.8 2.3-8 '
    '2.3-6.3 0-11.6-4.1-13.5-9.8l-7.9 6.1C6.5 42.6 14.6 48 24 48z"/></svg>'
)
ICON_GOOGLE = "data:image/svg+xml;base64," + base64.b64encode(_GOOGLE_SVG.encode()).decode()


# -------------------------------------------------------------------- css
def _css() -> str:
    css = """
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

:root{
  --accent:#2F80ED; --accent2:#7C5CFF; --border:#DCE7FA; --text:#14233B;
  --muted:#8A99B2; --field:#F7FAFF; --soft:rgba(47,128,237,.14);
}
/* font for everything EXCEPT Streamlit's icon glyphs (overriding those shows words like "visibility") */
.stApp, .stApp :not([data-testid="stIconMaterial"]){ font-family:'Plus Jakarta Sans','Segoe UI',system-ui,sans-serif; }

/* page background + remove Streamlit chrome */
[data-testid="stAppViewContainer"]{
  background:
    radial-gradient(560px 360px at 8% 6%, rgba(79,195,247,.30), transparent 70%),
    radial-gradient(560px 360px at 94% 96%, rgba(124,92,255,.22), transparent 70%),
    #F4F8FF;
}
[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stSidebar"], section[data-testid="stSidebar"], footer{ display:none !important; }

/* the card = main container, centered, max-width 440px */
div[data-testid="stAppViewContainer"] section.main div[data-testid="stMainBlockContainer"],
div[data-testid="stAppViewContainer"] section.main .block-container,
div.stMainBlockContainer,
.stApp [data-testid="stMainBlockContainer"],
.stApp .block-container,
[data-testid="stMainBlockContainer"],
.block-container{
  max-width:440px !important;
  width:100% !important;
  margin:6vh auto 4vh auto !important;
  padding:34px 28px 26px 28px !important;
  background:#fff !important;
  border:1.5px solid var(--border) !important;
  border-radius:26px !important;
  box-shadow:0 30px 60px -26px rgba(40,80,200,.40) !important;
  box-sizing:border-box !important;
}
[data-testid="stVerticalBlock"]{ gap:.85rem; }

/* header (rendered by render_auth_header) */
.auth-head{ text-align:center !important; margin-bottom:18px !important; }
.auth-logo{
  width:56px; height:56px; margin:0 auto 14px auto; border-radius:18px; display:grid; place-items:center; color:#fff;
  background:linear-gradient(135deg,var(--accent),var(--accent2));
  box-shadow:0 14px 24px -8px rgba(70,90,240,.6);
}
.auth-logo svg{ width:28px; height:28px; }
.auth-title{ margin:0; padding:0; font-size:26px; font-weight:800; letter-spacing:-.02em; color:var(--text); line-height:1.2; text-align:center !important; }
.auth-head p{ margin:8px 0 0; font-size:14px; color:var(--muted); text-align:center !important; }

/* auth mode switch link button at bottom - full width */
.st-key-switch_auth_mode button{
  width:100% !important;
  background:#F8FAFD !important;
  border:1.5px solid var(--border) !important;
  border-radius:15px !important;
  box-shadow:none !important;
  color:var(--text) !important;
  font-size:13.5px !important;
  font-weight:600 !important;
  margin:4px 0 0 0 !important;
  padding:10px 0 !important;
  height:44px !important;
  display:flex !important;
  align-items:center !important;
  justify-content:center !important;
  cursor:pointer !important;
  transition:all .2s ease !important;
}
.st-key-switch_auth_mode button:hover{
  background:#EEF4FE !important;
  border-color:var(--accent) !important;
  color:var(--accent) !important;
  transform:translateY(-1px) !important;
}
.st-key-switch_auth_mode button p{
  font-size:13.5px !important;
  color:inherit !important;
  font-weight:600 !important;
}

/* labels */
[data-testid="stWidgetLabel"] p{ font-size:12.5px; font-weight:700; color:#41536F; margin-bottom:2px; }

/* text inputs (newer Streamlit: stTextInputRootElement, older: BaseWeb input) */
[data-testid="stTextInputRootElement"], [data-testid="stTextInput"] [data-baseweb="input"]{
  height:48px; background:var(--field) !important; border:1.5px solid var(--border) !important;
  border-radius:14px !important; box-shadow:none; transition:border-color .2s, box-shadow .2s, background .2s;
}
[data-testid="stTextInputRootElement"]:focus-within, [data-testid="stTextInput"] [data-baseweb="input"]:focus-within{
  background:#fff !important; border-color:var(--accent) !important; box-shadow:0 0 0 4px var(--soft) !important;
}
[data-testid="stTextInput"] [data-baseweb="base-input"]{ background:transparent !important; }
[data-testid="stTextInput"] input{
  height:44px; font-size:15px; font-weight:500; color:var(--text);
  background-color:transparent !important; background-repeat:no-repeat; background-position:14px center; background-size:18px;
  padding-left:44px !important;
}
[data-testid="stTextInput"] input::placeholder{ color:#B0BCD0; font-weight:400; }
.st-key-auth_name input{ background-image:url("__USER__"); }
.st-key-auth_email input{ background-image:url("__MAIL__"); }
.st-key-auth_pw input{ background-image:url("__LOCK__"); }
/* show/hide eye button */
[data-testid="stTextInputRootElement"] button, [data-testid="stTextInput"] [data-baseweb="input"] button{ color:#8A99B2; background:transparent; border:0; }
[data-testid="stTextInputRootElement"] button:hover{ color:var(--accent); background:transparent; }
/* remove the overlapping "Press Enter to submit form" hint */
[data-testid="InputInstructions"]{ display:none !important; }

/* form: no extra box */
[data-testid="stForm"]{ border:0 !important; padding:0 !important; background:transparent; }

/* primary button */
[data-testid="stFormSubmitButton"] button, .st-key-auth_submit button{
  width:100% !important; height:50px !important; border:0 !important; border-radius:15px !important; color:#fff !important;
  background:linear-gradient(135deg,var(--accent),var(--accent2)) !important;
  box-shadow:0 14px 24px -10px rgba(70,90,240,.65) !important;
  transition:transform .15s, box-shadow .15s !important;
}
[data-testid="stFormSubmitButton"]{ margin-top:12px; }
[data-testid="stFormSubmitButton"] button p{ color:#fff !important; font-size:15px !important; font-weight:700 !important; }
[data-testid="stFormSubmitButton"] button:hover{ transform:translateY(-1px) !important; color:#fff !important; border:0 !important; }
[data-testid="stFormSubmitButton"] button:active{ transform:scale(.99) !important; }

/* google button - full width */
.st-key-google_btn button{
  width:100% !important; height:48px !important; border-radius:15px !important; background:#fff !important; border:1.5px solid var(--border) !important;
  display:flex !important; align-items:center !important; justify-content:center !important; gap:10px !important; transition:border-color .2s, transform .15s, background .2s !important;
}
.st-key-google_btn button > div{ width:auto !important; flex:0 0 auto; }
.st-key-google_btn button::before{
  content:""; width:18px; height:18px; flex:none;
  background:url("__GOOGLE__") no-repeat center / contain;
}
.st-key-google_btn button p{ font-size:14px !important; font-weight:700 !important; color:var(--text) !important; }
.st-key-google_btn button:hover{ border-color:var(--accent) !important; background:#FAFCFF !important; transform:translateY(-1px) !important; }

/* guest developer button */
.st-key-guest_btn button, .st-key-guest_notice_btn button{
  width:100% !important; height:44px !important; border-radius:15px !important; background:#EEF4FF !important; border:1.5px dashed var(--accent) !important;
  display:flex !important; align-items:center !important; justify-content:center !important; gap:8px !important;
  transition:all .15s ease !important;
}
.st-key-guest_btn button p, .st-key-guest_notice_btn button p{ font-size:13.5px !important; font-weight:700 !important; color:var(--accent) !important; }
.st-key-guest_btn button:hover, .st-key-guest_notice_btn button:hover{ background:#E0EBFF !important; border-style:solid !important; transform:translateY(-1px) !important; }

/* divider, helper text, alerts */
.auth-or{ display:flex; align-items:center; gap:12px; margin:2px 0; color:var(--muted); font-size:12.5px; font-weight:600; }
.auth-or::before, .auth-or::after{ content:""; flex:1; height:1px; background:var(--border); }
.auth-forgot{ text-align:right !important; margin:2px 0 6px auto !important; max-width:max-content !important; font-size:13px !important; }
.auth-forgot a{ color:var(--accent) !important; font-weight:700 !important; text-decoration:none !important; }
.auth-forgot a:hover{ text-decoration:underline !important; }
.auth-foot{ text-align:center; font-size:12px; color:var(--muted); line-height:1.5; margin:4px 0 0; }
[data-testid="stAlert"]{ border-radius:12px; font-size:13.5px; }

/* focus rings + small screens + reduced motion */
button:focus-visible, a:focus-visible{ outline:3px solid var(--soft) !important; outline-offset:2px; }
@media (max-width:480px){
  div[data-testid="stAppViewContainer"] section.main div[data-testid="stMainBlockContainer"],
  div[data-testid="stAppViewContainer"] section.main .block-container,
  div.stMainBlockContainer,
  .stApp [data-testid="stMainBlockContainer"],
  .stApp .block-container,
  [data-testid="stMainBlockContainer"],
  .block-container{ margin:0 auto !important; border-radius:0 !important; border-width:0 !important; box-shadow:none !important; padding:26px 20px !important; min-height:100vh; }
}
@media (prefers-reduced-motion:reduce){ *{ transition:none !important; animation:none !important; } }
"""
    return (css.replace("__USER__", ICON_USER).replace("__MAIL__", ICON_MAIL)
               .replace("__LOCK__", ICON_LOCK).replace("__GOOGLE__", ICON_GOOGLE))


def inject_login_css() -> None:
    st.markdown(f"<style>{_css()}</style>", unsafe_allow_html=True)


_LOGO = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a8 8 0 01-11.6 '
    '7.1L4 20l1-4.6A8 8 0 1121 12z"/><path d="M9 11h6M9 14h3"/></svg>'
)


def render_auth_header(signup: bool) -> None:
    title = "Create your account" if signup else "Welcome back"
    sub = ("Start learning, coding and building in minutes" if signup
           else "Sign in to continue to your assistant")
    st.markdown(
        f'<div class="auth-head" style="text-align:center; margin-bottom:18px;"><div class="auth-logo">{_LOGO}</div>'
        f'<div class="auth-title" role="heading" aria-level="1" style="text-align:center;">{title}</div>'
        f'<p style="text-align:center;">{sub}</p></div>',
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------------- demo
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def derive_name_from_email(email_str: str) -> str:
    """Derives a clean capitalized user display name from an email local-part."""
    if not email_str:
        return "Student"
    local_part = email_str.split("@")[0] if "@" in email_str else email_str
    tokens = re.split(r"[._\-+]+", local_part)
    clean_tokens = [t.capitalize() for t in tokens if t]
    return " ".join(clean_tokens) if clean_tokens else "Student"


def check_google_auth_available() -> tuple[bool, Optional[str]]:
    """
    Checks if Streamlit native OIDC auth is available and configured.
    Returns (is_available, error_or_warning_message).
    """
    try:
        v_parts = [int(p) for p in re.findall(r'\d+', st.__version__)[:2]]
        if len(v_parts) >= 2 and (v_parts[0] < 1 or (v_parts[0] == 1 and v_parts[1] < 42)):
            return False, "Google Sign-In requires Streamlit 1.42+ with native OIDC support."
        if not hasattr(st, "login") or not hasattr(st, "user"):
            return False, "Streamlit OIDC authentication is not supported in this runtime."
    except Exception:
        return False, "Unable to verify Streamlit version for Google authentication."

    try:
        import importlib.util
        if importlib.util.find_spec("authlib") is None:
            return False, "Google Sign-In requires Authlib (pip install Authlib)."
    except Exception:
        return False, "Google Sign-In requires Authlib (pip install Authlib)."

    try:
        sec = getattr(st, "secrets", None)
        if sec is None:
            return False, "Google Sign-In is not configured. Add [auth] credentials in .streamlit/secrets.toml."
        if "auth" not in sec:
            return False, "Google Sign-In is not configured: missing [auth] section in .streamlit/secrets.toml."
        auth_conf = sec["auth"]
        client_id = auth_conf.get("client_id", "")
        client_secret = auth_conf.get("client_secret", "")
        if not client_id or not client_secret or "your-google-client-id" in str(client_id):
            return False, "Google OAuth client credentials incomplete in .streamlit/secrets.toml."
        return True, None
    except Exception:
        return False, "Google Sign-In is not configured: missing .streamlit/secrets.toml [auth] credentials."


def render_login_page() -> Optional[Dict[str, Any]]:
    """Renders the login/signup page and handles authentication state."""
    inject_login_css()

    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "Sign in"
    signup = st.session_state.auth_mode == "Create account"

    header = st.container()
    with header:
        render_auth_header(signup)

    with st.form("auth_form"):
        name = st.text_input("Username / Full name", placeholder="e.g. Jane Doe or your name", key="auth_name")
        email = st.text_input("Email address", placeholder="name@company.com", key="auth_email")
        pw = st.text_input("Password", type="password",
                           placeholder="At least 6 characters" if signup else "Enter your password",
                           key="auth_pw")
        submitted = st.form_submit_button("Create account" if signup else "Sign in",
                                          use_container_width=True)

    if not signup:
        st.markdown(
            '<div class="auth-forgot" style="text-align:right; margin:2px 0 8px auto; max-width:max-content;">'
            '<a href="#" style="font-size:13px; font-weight:700; color:var(--accent); text-decoration:none;" onclick="return false;">Forgot password?</a>'
            '</div>',
            unsafe_allow_html=True
        )

    if submitted:
        clean_name = (name or "").strip()
        clean_email = (email or "").strip()
        clean_pw = (pw or "").strip()

        if signup and not clean_name:
            st.error("Please enter your username or full name.")
        elif not clean_email or not EMAIL_RE.match(clean_email):
            st.error("Please enter a valid email address.")
        elif not clean_pw or (signup and len(clean_pw) < 6):
            st.error("Password must be at least 6 characters." if signup else "Please enter your password.")
        else:
            final_user_name = clean_name if clean_name else derive_name_from_email(clean_email)
            from core.memory import get_or_create_user
            u_info = get_or_create_user(
                email=clean_email,
                name=final_user_name,
                auth_provider="email"
            )
            st.session_state.authenticated = True
            st.session_state.user_email = u_info["email"]
            st.session_state.user_name = u_info["name"]
            st.session_state.user_picture = u_info.get("picture")
            st.session_state.user_plan = u_info["plan"]
            st.session_state.is_pro = u_info["is_pro"]
            st.session_state.auth_method = "email"
            st.rerun()
            st.stop()

    st.markdown('<div class="auth-or">OR</div>', unsafe_allow_html=True)
    google_clicked = st.button("Continue with Google", key="google_btn", use_container_width=True)
    guest_clicked = st.button("⚡ Continue as Guest Developer", key="guest_btn", use_container_width=True, help="Instant 1-click access for local testing without OAuth setup")

    if guest_clicked:
        from core.memory import get_or_create_user
        u_info = get_or_create_user(
            email="developer@sparkai.local",
            name="Developer",
            auth_provider="guest"
        )
        st.session_state.authenticated = True
        st.session_state.user_email = u_info["email"]
        st.session_state.user_name = u_info["name"]
        st.session_state.user_picture = u_info.get("picture")
        st.session_state.user_plan = u_info["plan"]
        st.session_state.is_pro = u_info["is_pro"]
        st.session_state.auth_method = "guest"
        st.session_state.pop("google_auth_notice", None)
        st.rerun()
        st.stop()

    if google_clicked:
        is_avail, notice = check_google_auth_available()
        if not is_avail:
            st.session_state["google_auth_notice"] = (
                notice or "Google Sign-In is not configured. Add [auth] credentials in .streamlit/secrets.toml."
            )
            st.rerun()
            st.stop()
        else:
            try:
                st.session_state.pop("google_auth_notice", None)
                st.login()
            except Exception as e:
                st.session_state["google_auth_notice"] = (
                    f"Could not initiate Google Sign-In: {type(e).__name__}. Check .streamlit/secrets.toml."
                )
                st.rerun()
                st.stop()

    if st.session_state.get("google_auth_notice"):
        st.warning(st.session_state["google_auth_notice"])
        with st.expander("🛠️ How to configure Google Sign-In or bypass", expanded=True):
            st.markdown(
                "**Local Bypass:**\n"
                "- Click **⚡ Continue as Guest Developer** above, or enter any email/password to sign in immediately.\n\n"
                "**To enable official Google Sign-In:**\n"
                "1. Open [Google Cloud Console Credentials](https://console.cloud.google.com/apis/credentials).\n"
                "2. Create an **OAuth 2.0 Client ID** (Application type: *Web application*).\n"
                "3. Set Authorized redirect URIs to: `http://localhost:8501/oauth2callback`\n"
                "4. In `.streamlit/secrets.toml`, replace placeholders with your real credentials:\n"
                "   ```toml\n"
                "   [auth]\n"
                "   redirect_uri = \"http://localhost:8501/oauth2callback\"\n"
                "   client_id = \"your-client-id.apps.googleusercontent.com\"\n"
                "   client_secret = \"your-client-secret\"\n"
                "   ```\n"
                "5. Restart Streamlit server."
            )
            if st.button("🚀 Enter immediately as Guest Developer", key="guest_notice_btn", use_container_width=True):
                from core.memory import get_or_create_user
                u_info = get_or_create_user(
                    email="developer@sparkai.local",
                    name="Developer",
                    auth_provider="guest"
                )
                st.session_state.authenticated = True
                st.session_state.user_email = u_info["email"]
                st.session_state.user_name = u_info["name"]
                st.session_state.user_picture = u_info.get("picture")
                st.session_state.user_plan = u_info["plan"]
                st.session_state.is_pro = u_info["is_pro"]
                st.session_state.auth_method = "guest"
                st.session_state.pop("google_auth_notice", None)
                st.rerun()
                st.stop()

    if signup:
        if st.button("Already have an account? Sign in", key="switch_auth_mode", use_container_width=True):
            st.session_state.auth_mode = "Sign in"
            st.rerun()
            st.stop()
    else:
        if st.button("Don't have an account? Create account", key="switch_auth_mode", use_container_width=True):
            st.session_state.auth_mode = "Create account"
            st.rerun()
            st.stop()

    st.markdown('<p class="auth-foot">By continuing, you agree to the Terms and Privacy Policy.</p>',
                unsafe_allow_html=True)

    return None


def main() -> None:
    st.set_page_config(page_title="Sign in", page_icon="💬", layout="centered")
    render_login_page()


if __name__ == "__main__":
    main()
