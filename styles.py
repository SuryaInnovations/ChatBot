"""
styles.py — Centralized Theme and UI Stylesheet for All-in-One AI Assistant.
Implements unified light theme default with dark theme support, Inter typography,
crisp 4.5:1+ contrast on every surface, responsive capability cards with colored icon tiles,
and polished chat/dock aesthetics.
"""

def get_custom_css() -> str:
    """Returns the complete, cohesive stylesheet for the application."""
    return """
<style>
/* Streamlit header bar: keep transparent and zero-height, but allow sidebar expand button */
header[data-testid="stHeader"] {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    height: 0 !important;
    overflow: visible !important;
    pointer-events: none !important;
    z-index: 1000 !important;
}

/* ====================================================
   WCAG 2.2 AA Accessibility & Universal Focus Rings
   ==================================================== */
button:focus-visible,
input:focus-visible,
select:focus-visible,
textarea:focus-visible,
a:focus-visible,
div[role="button"]:focus-visible,
[tabindex="0"]:focus-visible {
    outline: 2.5px solid #2F80ED !important;
    outline-offset: 2px !important;
    box-shadow: 0 0 0 4px rgba(47, 128, 237, 0.20) !important;
}

.sr-only, .visually-hidden {
    position: absolute !important;
    width: 1px !important;
    height: 1px !important;
    padding: 0 !important;
    margin: -1px !important;
    overflow: hidden !important;
    clip: rect(0, 0, 0, 0) !important;
    white-space: nowrap !important;
    border: 0 !important;
}

/* Toolbar container: keep transparent and non-blocking, but allow expand button */
header[data-testid="stHeader"] div[data-testid="stToolbar"],
div[data-testid="stToolbar"] {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    overflow: visible !important;
    pointer-events: none !important;
}

/* Hide decoration line and top-right action elements (Deploy, Running status, etc.) */
header[data-testid="stHeader"] div[data-testid="stDecoration"],
header[data-testid="stHeader"] div[data-testid="stHeaderActionElements"],
div[data-testid="stDecoration"],
div[data-testid="stHeaderActionElements"] {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    width: 0 !important;
    pointer-events: none !important;
}

/* ----------------------------------------------------
   Small Sidebar Toggle Button (At Edge of Sidebar)
   - When OPEN: Left chevron ‹ (closes/collapses sidebar)
   - When CLOSED: Hamburger menu icon ☰ (opens sidebar)
   - Clean 2D icon, blue accent color (#2F80ED), rounded button,
     subtle shadow, smooth rotation/transition animation, desktop & mobile
   ---------------------------------------------------- */
.eduvyn-sidebar-toggle-btn,
.eduvyn-open-sidebar-btn {
    position: fixed !important;
    top: 18px !important;
    width: 38px !important;
    height: 38px !important;
    background: #FFFFFF !important;
    border: 1.5px solid #DCE7FA !important;
    border-radius: 12px !important;
    box-shadow: 0 2px 8px rgba(47, 128, 237, 0.12), 0 1px 3px rgba(20, 35, 59, 0.06) !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    cursor: pointer !important;
    z-index: 99999999 !important;
    outline: none !important;
    box-sizing: border-box !important;
    padding: 0 !important;
    margin: 0 !important;
    color: #2F80ED !important;
    transition: left 0.28s cubic-bezier(0.16, 1, 0.3, 1),
                transform 0.22s cubic-bezier(0.16, 1, 0.3, 1),
                background 0.2s ease,
                border-color 0.2s ease,
                box-shadow 0.2s ease !important;
    pointer-events: auto !important;
}

.eduvyn-sidebar-toggle-btn:hover,
.eduvyn-open-sidebar-btn:hover {
    background: #F8FAFD !important;
    border-color: #2F80ED !important;
    color: #2F80ED !important;
    box-shadow: 0 4px 16px rgba(47, 128, 237, 0.24), 0 2px 4px rgba(20, 35, 59, 0.08) !important;
    transform: translateY(-1px) scale(1.04) !important;
}

.eduvyn-sidebar-toggle-btn:active,
.eduvyn-open-sidebar-btn:active {
    transform: scale(0.95) !important;
}

.eduvyn-sidebar-toggle-btn:focus-visible {
    box-shadow: 0 0 0 3px rgba(47, 128, 237, 0.25) !important;
}

/* Icons container and smooth rotation/transition animation */
.eduvyn-sidebar-toggle-btn .toggle-icon-wrap {
    width: 22px !important;
    height: 22px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    position: relative !important;
}

.eduvyn-sidebar-toggle-btn svg {
    width: 20px !important;
    height: 20px !important;
    stroke: #2F80ED !important;
    color: #2F80ED !important;
    position: absolute !important;
    transition: transform 0.26s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.22s ease !important;
    pointer-events: none !important;
}

/* When CLOSED: Show hamburger menu icon ☰ */
.eduvyn-sidebar-toggle-btn.is-closed .icon-hamburger {
    opacity: 1 !important;
    transform: rotate(0deg) scale(1) !important;
    visibility: visible !important;
}
.eduvyn-sidebar-toggle-btn.is-closed .icon-chevron {
    opacity: 0 !important;
    transform: rotate(90deg) scale(0.7) !important;
    visibility: hidden !important;
}

/* When OPEN: Show left chevron ‹ */
.eduvyn-sidebar-toggle-btn.is-open .icon-chevron {
    opacity: 1 !important;
    transform: rotate(0deg) scale(1) !important;
    visibility: visible !important;
}
.eduvyn-sidebar-toggle-btn.is-open .icon-hamburger {
    opacity: 0 !important;
    transform: rotate(-90deg) scale(0.7) !important;
    visibility: hidden !important;
}

/* Native Expand Button (When Closed): Hamburger menu icon ☰ */
div[data-testid="stSidebarCollapsedControl"],
div[data-testid="collapsedControl"] {
    display: block !important;
    visibility: visible !important;
    position: fixed !important;
    top: 18px !important;
    left: 18px !important;
    z-index: 9999999 !important;
    pointer-events: auto !important;
}

button[data-testid="stExpandSidebarButton"],
div[data-testid="stSidebarCollapsedControl"] button,
div[data-testid="collapsedControl"] button {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    position: fixed !important;
    top: 18px !important;
    left: 18px !important;
    width: 38px !important;
    height: 38px !important;
    background: #FFFFFF !important;
    border: 1.5px solid #DCE7FA !important;
    border-radius: 12px !important;
    box-shadow: 0 2px 8px rgba(47, 128, 237, 0.12), 0 1px 3px rgba(20, 35, 59, 0.06) !important;
    color: #2F80ED !important;
    cursor: pointer !important;
    z-index: 9999999 !important;
    transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1) !important;
    outline: none !important;
    pointer-events: auto !important;
}

button[data-testid="stExpandSidebarButton"]:hover,
div[data-testid="stSidebarCollapsedControl"] button:hover {
    background: #F8FAFD !important;
    border-color: #2F80ED !important;
    box-shadow: 0 4px 16px rgba(47, 128, 237, 0.24) !important;
    transform: translateY(-1px) scale(1.04) !important;
}

button[data-testid="stExpandSidebarButton"]::before,
div[data-testid="stSidebarCollapsedControl"] button::before {
    content: "" !important;
    display: block !important;
    width: 20px !important;
    height: 20px !important;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%232F80ED' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cline x1='4' y1='6' x2='20' y2='6'/%3E%3Cline x1='4' y1='12' x2='20' y2='12'/%3E%3Cline x1='4' y1='18' x2='20' y2='18'/%3E%3C/svg%3E") !important;
    background-size: contain !important;
    background-repeat: no-repeat !important;
    background-position: center !important;
}

button[data-testid="stExpandSidebarButton"] > span,
button[data-testid="stExpandSidebarButton"] > div,
button[data-testid="stExpandSidebarButton"] svg {
    display: none !important;
}

/* Native Collapse Button (When Open): Left chevron ‹ at edge of sidebar */
button[data-testid="stSidebarCollapseButton"],
div[data-testid="stSidebarHeader"] button {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 36px !important;
    height: 36px !important;
    border-radius: 10px !important;
    border: 1.5px solid #DCE7FA !important;
    background: #FFFFFF !important;
    color: #2F80ED !important;
    box-shadow: 0 2px 8px rgba(47, 128, 237, 0.10), 0 1px 3px rgba(20, 35, 59, 0.04) !important;
    transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1) !important;
    cursor: pointer !important;
    pointer-events: auto !important;
    outline: none !important;
}

button[data-testid="stSidebarCollapseButton"]:hover,
div[data-testid="stSidebarHeader"] button:hover {
    background: #F8FAFD !important;
    border-color: #2F80ED !important;
    box-shadow: 0 4px 14px rgba(47, 128, 237, 0.22) !important;
    transform: translateY(-1px) scale(1.04) !important;
}

button[data-testid="stSidebarCollapseButton"]::before,
div[data-testid="stSidebarHeader"] button::before {
    content: "" !important;
    display: block !important;
    width: 20px !important;
    height: 20px !important;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%232F80ED' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='15 18 9 12 15 6'/%3E%3C/svg%3E") !important;
    background-size: contain !important;
    background-repeat: no-repeat !important;
    background-position: center !important;
}

button[data-testid="stSidebarCollapseButton"] > span,
button[data-testid="stSidebarCollapseButton"] > div,
button[data-testid="stSidebarCollapseButton"] svg {
    display: none !important;
}

/* Responsive Rules for Mobile */
@media (max-width: 640px) {
    .eduvyn-sidebar-toggle-btn,
    .eduvyn-open-sidebar-btn {
        width: 36px !important;
        height: 36px !important;
        top: 14px !important;
    }
    .eduvyn-sidebar-toggle-btn svg {
        width: 18px !important;
        height: 18px !important;
    }
}

/* ----------------------------------------------------
   1. Google Fonts Import (Plus Jakarta Sans, Inter & JetBrains Mono)
   ---------------------------------------------------- */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ----------------------------------------------------
   2. Design Tokens & CSS Variables (:root)
      Default: Light Palette (Crisp, modern, high contrast)
   ---------------------------------------------------- */
:root {
    --font-sans: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    --font-mono: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;

    /* Light Theme (Default) */
    --bg-app: #F4F8FF;
    --bg-surface: #FFFFFF;
    --bg-sidebar: #F4F8FF;
    --bg-card: #FFFFFF;
    --bg-card-hover: #F1F5F9;
    --bg-input-card: #FFFFFF;
    --bg-code: #0F172A;
    
    --border-subtle: #DCE7FA;
    --border-card: #DCE7FA;
    --border-hover: #CBD5E1;
    --border-focus: #2F80ED;
    
    --text-primary: #14233B;
    --text-secondary: #475569;
    --text-muted: #8A99B2;
    --text-inverse: #FFFFFF;
    
    --accent-primary: #2F80ED;
    --accent-hover: #1D4ED8;
    --accent-gradient: linear-gradient(135deg, #2F80ED 0%, #7C5CFF 100%);
    --accent-soft: rgba(47, 128, 237, 0.08);
    --accent-glow: rgba(47, 128, 237, 0.15);
    
    --user-bubble-bg: linear-gradient(135deg, #2F80ED 0%, #7C5CFF 100%);
    --user-bubble-text: #FFFFFF;
    --assistant-bubble-bg: #FFFFFF;
    --assistant-bubble-border: #E2E8F0;
    --assistant-bubble-text: #0F172A;
    
    --button-bg: #FFFFFF;
    --button-border: #CBD5E1;
    --button-text: #1E293B;
    --button-hover-bg: #F1F5F9;
    --button-hover-border: #6366F1;
    
    --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.05), 0 1px 2px rgba(0, 0, 0, 0.03);
    --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
    --shadow-float: 0 12px 30px rgba(15, 23, 42, 0.08), 0 4px 12px rgba(15, 23, 42, 0.04);
    
    --radius-sm: 6px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --radius-xl: 20px;
    --radius-full: 9999px;
    --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
    
    /* Tile icon tints (Light Mode) */
    --tile-blue-bg: #EFF6FF;
    --tile-blue-text: #2563EB;
    --tile-blue-border: rgba(37, 99, 235, 0.2);
    
    --tile-purple-bg: #F5F3FF;
    --tile-purple-text: #7C3AED;
    --tile-purple-border: rgba(124, 58, 237, 0.2);
    
    --tile-green-bg: #ECFDF5;
    --tile-green-text: #059669;
    --tile-green-border: rgba(5, 150, 105, 0.2);
    
    --tile-orange-bg: #FFF7ED;
    --tile-orange-text: #EA580C;
    --tile-orange-border: rgba(234, 88, 12, 0.2);
    
    --tile-pink-bg: #FDF2F8;
    --tile-pink-text: #DB2777;
    --tile-pink-border: rgba(219, 39, 119, 0.2);
    
    --tile-yellow-bg: #FEFCE8;
    --tile-yellow-text: #CA8A04;
    --tile-yellow-border: rgba(202, 138, 4, 0.2);
}

/* ----------------------------------------------------
   2b. Dark Theme Tokens
   Triggered by prefers-color-scheme: dark OR [data-theme="dark"]
   ---------------------------------------------------- */
@media (prefers-color-scheme: dark) {
    :root {
        --bg-app: #0B1020;
        --bg-surface: #121A30;
        --bg-sidebar: #0E1528;
        --bg-card: #121A30;
        --bg-card-hover: #1A2440;
        --bg-input-card: #121A30;
        --bg-code: #080C18;
        
        --border-subtle: rgba(255, 255, 255, 0.09);
        --border-card: rgba(255, 255, 255, 0.12);
        --border-hover: rgba(255, 255, 255, 0.2);
        --border-focus: #818CF8;
        
        --text-primary: #F3F4F6;
        --text-secondary: #CBD5E1;
        --text-muted: #94A3B8;
        --text-inverse: #0B1020;
        
        --accent-primary: #6366F1;
        --accent-hover: #818CF8;
        --accent-gradient: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%);
        --accent-soft: rgba(99, 102, 241, 0.15);
        --accent-glow: rgba(99, 102, 241, 0.3);
        
        --user-bubble-bg: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%);
        --user-bubble-text: #FFFFFF;
        --assistant-bubble-bg: #121A30;
        --assistant-bubble-border: rgba(255, 255, 255, 0.1);
        --assistant-bubble-text: #F3F4F6;
        
        --button-bg: #1A2440;
        --button-border: rgba(255, 255, 255, 0.14);
        --button-text: #F3F4F6;
        --button-hover-bg: #222E52;
        --button-hover-border: #818CF8;
        
        --shadow-sm: 0 2px 6px rgba(0, 0, 0, 0.3);
        --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.4);
        --shadow-float: 0 12px 32px rgba(0, 0, 0, 0.55);
        
        /* Tile icon tints (Dark Mode) */
        --tile-blue-bg: rgba(37, 99, 235, 0.18);
        --tile-blue-text: #60A5FA;
        --tile-blue-border: rgba(96, 165, 250, 0.25);
        
        --tile-purple-bg: rgba(124, 58, 237, 0.18);
        --tile-purple-text: #A78BFA;
        --tile-purple-border: rgba(167, 139, 250, 0.25);
        
        --tile-green-bg: rgba(5, 150, 105, 0.18);
        --tile-green-text: #34D399;
        --tile-green-border: rgba(52, 211, 153, 0.25);
        
        --tile-orange-bg: rgba(234, 88, 12, 0.18);
        --tile-orange-text: #FB923C;
        --tile-orange-border: rgba(251, 146, 60, 0.25);
        
        --tile-pink-bg: rgba(219, 39, 119, 0.18);
        --tile-pink-text: #F472B6;
        --tile-pink-border: rgba(244, 114, 182, 0.25);
        
        --tile-yellow-bg: rgba(202, 138, 4, 0.18);
        --tile-yellow-text: #FACC15;
        --tile-yellow-border: rgba(250, 204, 21, 0.25);
    }
}

[data-theme="dark"] {
    --bg-app: #0B1020;
    --bg-surface: #121A30;
    --bg-sidebar: #0E1528;
    --bg-card: #121A30;
    --bg-card-hover: #1A2440;
    --bg-input-card: #121A30;
    --bg-code: #080C18;
    
    --border-subtle: rgba(255, 255, 255, 0.09);
    --border-card: rgba(255, 255, 255, 0.12);
    --border-hover: rgba(255, 255, 255, 0.2);
    --border-focus: #818CF8;
    
    --text-primary: #F3F4F6;
    --text-secondary: #CBD5E1;
    --text-muted: #94A3B8;
    --text-inverse: #0B1020;
    
    --accent-primary: #6366F1;
    --accent-hover: #818CF8;
    --accent-gradient: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%);
    --accent-soft: rgba(99, 102, 241, 0.15);
    --accent-glow: rgba(99, 102, 241, 0.3);
    
    --user-bubble-bg: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%);
    --user-bubble-text: #FFFFFF;
    --assistant-bubble-bg: #121A30;
    --assistant-bubble-border: rgba(255, 255, 255, 0.1);
    --assistant-bubble-text: #F3F4F6;
    
    --button-bg: #1A2440;
    --button-border: rgba(255, 255, 255, 0.14);
    --button-text: #F3F4F6;
    --button-hover-bg: #222E52;
    --button-hover-border: #818CF8;
    
    --shadow-sm: 0 2px 6px rgba(0, 0, 0, 0.3);
    --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.4);
    --shadow-float: 0 12px 32px rgba(0, 0, 0, 0.55);
}

/* ----------------------------------------------------
   3. Global Page Layout & Typography
   ---------------------------------------------------- */
html, body, [class*="css"], .stApp {
    font-family: var(--font-sans) !important;
    background-color: var(--bg-app) !important;
    color: var(--text-primary) !important;
    -webkit-font-smoothing: antialiased;
}

.main .block-container {
    max-width: 980px !important;
    margin-left: auto !important;
    margin-right: auto !important;
    padding-top: 1.5rem !important;
    padding-bottom: 7.5rem !important;
}

/* Make top header bar transparent and click-through so custom top-right profile button works */
header[data-testid="stHeader"] {
    background: transparent !important;
    background-color: transparent !important;
    color: var(--text-primary) !important;
    height: 0 !important;
    min-height: 0 !important;
    overflow: visible !important;
    pointer-events: none !important;
    z-index: 10 !important;
}

header[data-testid="stHeader"] button,
header[data-testid="stHeader"] svg {
    color: var(--text-primary) !important;
    fill: var(--text-primary) !important;
}

/* Hide floating profile container (replaced by sidebar Profile and header settings) */
.eduvyn-profile-container {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
}

/* Custom Slim Scrollbar */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: transparent;
}
::-webkit-scrollbar-thumb {
    background: var(--border-hover);
    border-radius: var(--radius-full);
}
::-webkit-scrollbar-thumb:hover {
    background: var(--text-muted);
}

/* ----------------------------------------------------
   4. SPARK-AI Top Navigation Header (Image 2)
   ---------------------------------------------------- */
.top-nav-bar {
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    padding: 4px 0 14px 0 !important;
    margin-bottom: 20px !important;
    border-bottom: 1px solid #f1f5f9 !important;
    width: 100% !important;
}

.top-nav-left {
    display: inline-flex !important;
    align-items: center !important;
    gap: 12px !important;
}

.spark-logo-badge {
    width: 36px !important;
    height: 36px !important;
    min-width: 36px !important;
    min-height: 36px !important;
    background: #2563eb !important;
    background-color: #2563eb !important;
    border-radius: 10px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-shadow: 0 2px 6px rgba(37, 99, 235, 0.22) !important;
}

.spark-brand-title {
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif !important;
    font-size: 1.25rem !important;
    font-weight: 700 !important;
    color: #0f172a !important;
    letter-spacing: -0.01em !important;
    line-height: 1 !important;
}

div[class*="st-key-btn_top_"] button {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #64748b !important;
    font-size: 17px !important;
    width: 34px !important;
    height: 34px !important;
    min-width: 34px !important;
    min-height: 34px !important;
    padding: 0 !important;
    margin: 0 !important;
    border-radius: 8px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    cursor: pointer !important;
    transition: all 0.15s ease !important;
}

div[class*="st-key-btn_top_"] button:hover {
    background: #f1f5f9 !important;
    background-color: #f1f5f9 !important;
    color: #0f172a !important;
}

.app-header-container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 1.25rem;
    margin-bottom: 1.5rem;
    border-bottom: 1px solid var(--border-subtle);
    flex-wrap: wrap;
    gap: 16px;
}

.app-title-gradient {
    font-size: 40px; /* 40px bold */
    font-weight: 700;
    letter-spacing: -0.025em;
    line-height: 1.2;
    margin: 0;
    background: var(--accent-gradient);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    display: inline-block;
}

.app-subtitle {
    font-size: 16px; /* 16px muted */
    color: var(--text-secondary);
    margin: 0.35rem 0 0 0;
    font-weight: 400;
    line-height: 1.5;
}

.provider-status-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: var(--bg-card);
    border: 1px solid var(--border-card);
    border-radius: var(--radius-full);
    padding: 6px 14px;
    font-size: 0.82rem;
    font-weight: 500;
    color: var(--text-primary);
    box-shadow: var(--shadow-sm);
    transition: all var(--transition-fast);
}

.provider-status-pill:hover {
    border-color: var(--border-focus);
}

.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
    flex-shrink: 0;
}
.status-dot-ready {
    background-color: #22c55e;
    box-shadow: 0 0 6px rgba(34, 197, 94, 0.5);
}
.status-dot-configured {
    background-color: #f59e0b;
    box-shadow: 0 0 6px rgba(245, 158, 11, 0.4);
}
.status-dot-error {
    background-color: #ef4444;
    box-shadow: 0 0 6px rgba(239, 68, 68, 0.5);
}
.status-dot-gray {
    background-color: #94a3b8;
}

/* ----------------------------------------------------
   5. Empty State Hero Header (Original SPARK-AI Style)
   ---------------------------------------------------- */
.empty-hero-container {
    text-align: center !important;
    max-width: 680px !important;
    margin: 4.5rem auto 2.5rem auto !important;
    padding: 0 16px !important;
}

.hero-navy-circle {
    display: none !important;
}

.hero-help-title {
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif !important;
    font-size: 32px !important;
    font-weight: 700 !important;
    color: #0f172a !important;
    letter-spacing: -0.015em !important;
    margin: 0 0 8px 0 !important;
    line-height: 1.25 !important;
    text-align: center !important;
}

.hero-help-subtitle {
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif !important;
    font-size: 15px !important;
    font-weight: 400 !important;
    color: #475569 !important;
    margin: 0 0 28px 0 !important;
    line-height: 1.4 !important;
    text-align: center !important;
}


/* ----------------------------------------------------
   7. Chat Messages & Formatting
   ---------------------------------------------------- */
div[data-testid="stChatMessage"] {
    max-width: 960px !important;
    margin-left: auto !important;
    margin-right: auto !important;
    border-radius: var(--radius-lg) !important;
    padding: 16px 20px !important;
    margin-bottom: 16px !important;
    box-shadow: var(--shadow-sm) !important;
    animation: fadeIn 180ms ease-out !important;
    font-size: 0.96rem !important;
    line-height: 1.6 !important;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
}

/* User Message Bubble */
div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatar"]:has([aria-label*="user"])),
div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatar"]:contains("🧑‍💻")) {
    background: var(--user-bubble-bg) !important;
    color: var(--user-bubble-text) !important;
    border: none !important;
    margin-left: auto !important;
    border-bottom-right-radius: 4px !important;
}
div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatar"]:has([aria-label*="user"])) p,
div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatar"]:contains("🧑‍💻")) p {
    color: var(--user-bubble-text) !important;
}

/* Assistant Message Bubble */
div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatar"]:has([aria-label*="assistant"])),
div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatar"]:contains("🤖")) {
    background: var(--assistant-bubble-bg) !important;
    border: 1px solid var(--assistant-bubble-border) !important;
    color: var(--assistant-bubble-text) !important;
    border-bottom-left-radius: 4px !important;
}
div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatar"]:has([aria-label*="assistant"])) p,
div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatar"]:contains("🤖")) p {
    color: var(--assistant-bubble-text) !important;
}

/* Code Blocks & Inline Code */
div[data-testid="stChatMessage"] pre,
pre {
    background: var(--bg-code) !important;
    color: #F8FAFC !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: var(--radius-md) !important;
    padding: 14px 18px !important;
    font-family: var(--font-mono) !important;
    font-size: 0.88rem !important;
    margin: 12px 0 !important;
    overflow-x: auto !important;
}

div[data-testid="stChatMessage"] pre code,
pre code {
    background: transparent !important;
    color: #F8FAFC !important;
    font-family: var(--font-mono) !important;
}

div[data-testid="stChatMessage"] :not(pre) > code {
    font-family: var(--font-mono) !important;
    font-size: 0.86em !important;
    padding: 2px 6px !important;
    border-radius: 4px !important;
    background: var(--accent-soft) !important;
    color: var(--accent-primary) !important;
    border: 1px solid rgba(99, 102, 241, 0.15) !important;
}

/* Tables */
div[data-testid="stChatMessage"] table {
    width: 100% !important;
    border-collapse: collapse !important;
    margin: 14px 0 !important;
    border-radius: var(--radius-sm) !important;
    overflow: hidden !important;
    border: 1px solid var(--border-subtle) !important;
}
div[data-testid="stChatMessage"] th {
    background: var(--bg-card-hover) !important;
    color: var(--text-primary) !important;
    font-weight: 600 !important;
    padding: 10px 14px !important;
    border-bottom: 1px solid var(--border-subtle) !important;
}
div[data-testid="stChatMessage"] td {
    padding: 10px 14px !important;
    border-bottom: 1px solid var(--border-subtle) !important;
    color: var(--text-secondary) !important;
}

/* ----------------------------------------------------
   8. SPARK-AI Modern Chat Input Dock (Image 2)
   ---------------------------------------------------- */
.ai-search-dock {
    position: sticky !important;
    bottom: 20px !important;
    z-index: 99 !important;
    max-width: 960px !important;
    margin: 16px auto 10px auto !important;
    width: 100% !important;
    padding: 0 16px !important;
}

/* Floating Card Container: Clean White Rounded Capsule */
div.ai-search-dock div[data-testid="stForm"],
.ai-search-form-dock,
div[data-testid="stForm"]:has(div[data-testid="stTextInput"]),
div[data-testid="stForm"]:has(div[data-testid="stTextArea"]),
div[data-testid="stForm"]:has(input[placeholder*="Ask"]),
div[data-testid="stForm"]:has(textarea[placeholder*="Ask"]) {
    position: sticky !important;
    bottom: 20px !important;
    z-index: 99 !important;
    background: #ffffff !important;
    background-color: #ffffff !important;
    border-radius: 9999px !important;
    border: 1.5px solid #e5e7eb !important;
    padding: 6px 14px 6px 18px !important;
    max-width: 960px !important;
    width: 100% !important;
    margin: 16px auto 10px auto !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05), 0 1px 3px rgba(0, 0, 0, 0.02) !important;
    overflow: visible !important;
    transition: border-color 0.18s ease, box-shadow 0.18s ease !important;
}

div.ai-search-dock div[data-testid="stForm"]::before,
div.ai-search-dock div[data-testid="stForm"]::after,
.ai-search-form-dock::before,
.ai-search-form-dock::after,
div[data-testid="stForm"]:has(div[data-testid="stTextInput"])::before,
div[data-testid="stForm"]:has(div[data-testid="stTextInput"])::after,
div[data-testid="stForm"]:has(div[data-testid="stTextArea"])::before,
div[data-testid="stForm"]:has(div[data-testid="stTextArea"])::after {
    display: none !important;
    content: none !important;
}

/* Hover & Focus State */
div.ai-search-dock div[data-testid="stForm"]:hover,
.ai-search-form-dock:hover,
div[data-testid="stForm"]:has(div[data-testid="stTextInput"]):hover,
div[data-testid="stForm"]:has(div[data-testid="stTextArea"]):hover {
    border-color: #d1d5db !important;
    box-shadow: 0 6px 24px rgba(0, 0, 0, 0.08) !important;
}

div.ai-search-dock div[data-testid="stForm"]:focus-within,
.ai-search-form-dock:focus-within,
div[data-testid="stForm"]:has(div[data-testid="stTextInput"]):focus-within,
div[data-testid="stForm"]:has(div[data-testid="stTextArea"]):focus-within {
    border-color: #2F80ED !important;
    box-shadow: 0 6px 28px rgba(47, 128, 237, 0.16) !important;
}

/* Horizontal Row inside Dock Form */
div.ai-search-dock div[data-testid="stForm"] div[data-testid="stHorizontalBlock"],
.ai-search-form-dock div[data-testid="stHorizontalBlock"],
div[data-testid="stForm"]:has(div[data-testid="stTextInput"]) div[data-testid="stHorizontalBlock"],
div[data-testid="stForm"]:has(div[data-testid="stTextArea"]) div[data-testid="stHorizontalBlock"] {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    align-items: center !important;
    justify-content: space-between !important;
    gap: 8px !important;
    margin: 0 !important;
    padding: 0 !important;
    width: 100% !important;
}

/* 1. Col 1: Plus Button (+) on Far Left */
div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(1),
.ai-search-form-dock div[data-testid="stColumn"]:nth-child(1) {
    flex: 0 0 36px !important;
    width: 36px !important;
    min-width: 36px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 0 !important;
    margin: 0 !important;
}

div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(1) button,
.ai-search-form-dock div[data-testid="stColumn"]:nth-child(1) button {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #1f2937 !important;
    font-size: 24px !important;
    font-weight: 300 !important;
    width: 34px !important;
    height: 34px !important;
    min-width: 34px !important;
    min-height: 34px !important;
    border-radius: 50% !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 0 !important;
    margin: 0 !important;
    cursor: pointer !important;
    transition: all 0.15s ease !important;
}

div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(1) button:hover,
.ai-search-form-dock div[data-testid="stColumn"]:nth-child(1) button:hover {
    background: #f3f4f6 !important;
    background-color: #f3f4f6 !important;
    color: #000000 !important;
    transform: scale(1.08) !important;
}

div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(1) button svg,
div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(1) [data-testid="stIconMaterial"] {
    display: none !important;
}

div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(1) button p {
    font-size: 24px !important;
    font-weight: 300 !important;
    margin: 0 !important;
    padding: 0 !important;
    line-height: 1 !important;
}

/* 2. Col 2: Text Input / Text Area in Middle */
div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(2),
.ai-search-form-dock div[data-testid="stColumn"]:nth-child(2) {
    flex: 1 1 auto !important;
    min-width: 0 !important;
    padding: 0 4px !important;
    margin: 0 !important;
}

div[data-testid="stForm"] div[data-testid="stTextInput"],
div[data-testid="stForm"] div[data-testid="stTextInput"] *,
div[data-testid="stForm"] div[data-testid="stTextArea"],
div[data-testid="stForm"] div[data-testid="stTextArea"] *,
div[data-testid="stForm"] div[data-baseweb="input"],
div[data-testid="stForm"] div[data-baseweb="base-input"],
div[data-testid="stForm"] div[data-baseweb="textarea"] {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
}

div[data-testid="stForm"] div[data-testid="stTextInput"] input,
div[data-testid="stForm"] div[data-testid="stTextArea"] textarea {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
    color: #0d0d0d !important;
    font-size: 15px !important;
    font-family: inherit !important;
    font-weight: 400 !important;
    padding: 8px 4px !important;
    height: 40px !important;
    min-height: 40px !important;
    max-height: 120px !important;
    line-height: 24px !important;
    resize: none !important;
    caret-color: #2563eb !important;
    width: 100% !important;
    overflow-y: auto !important;
}

div[data-testid="stForm"] div[data-testid="stTextInput"] input::placeholder,
div[data-testid="stForm"] div[data-testid="stTextArea"] textarea::placeholder {
    color: #8e8ea0 !important;
    font-size: 15px !important;
    font-weight: 400 !important;
    opacity: 1 !important;
}

/* 3. Col 3: Think Button (Brain outline + "Think") */
div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(3),
.ai-search-form-dock div[data-testid="stColumn"]:nth-child(3) {
    flex: 0 0 auto !important;
    min-width: 90px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 0 !important;
    margin: 0 !important;
}

div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(3) button,
.ai-search-form-dock div[data-testid="stColumn"]:nth-child(3) button {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #6b7280 !important;
    font-size: 14.5px !important;
    font-weight: 500 !important;
    height: 34px !important;
    border-radius: 9999px !important;
    display: inline-flex !important;
    flex-direction: row !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 6px !important;
    padding: 4px 12px !important;
    margin: 0 !important;
    cursor: pointer !important;
    transition: all 0.15s ease !important;
    white-space: nowrap !important;
    word-break: keep-all !important;
    overflow-wrap: normal !important;
    min-width: 82px !important;
    flex-shrink: 0 !important;
}

div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(3) button:hover,
.ai-search-form-dock div[data-testid="stColumn"]:nth-child(3) button:hover {
    background: #f4f4f5 !important;
    background-color: #f4f4f5 !important;
    color: #111827 !important;
}

/* Brain outline SVG before text */
div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(3) button::before,
.ai-search-form-dock div[data-testid="stColumn"]:nth-child(3) button::before {
    content: "" !important;
    display: inline-block !important;
    width: 18px !important;
    height: 18px !important;
    flex-shrink: 0 !important;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 4.44-2.04Z'/%3E%3Cpath d='M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-4.44-2.04Z'/%3E%3C/svg%3E") !important;
    background-repeat: no-repeat !important;
    background-size: contain !important;
}

div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(3) button:hover::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='%23111827' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 4.44-2.04Z'/%3E%3Cpath d='M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-4.44-2.04Z'/%3E%3C/svg%3E") !important;
}

div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(3) button svg,
.ai-search-form-dock div[data-testid="stColumn"]:nth-child(3) button svg,
div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(3) [data-testid="stPopoverChevron"],
.ai-search-form-dock div[data-testid="stColumn"]:nth-child(3) [data-testid="stPopoverChevron"] {
    display: none !important;
    visibility: hidden !important;
    width: 0 !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}

div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(3) button p,
div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(3) button span,
div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(3) button div,
.ai-search-form-dock div[data-testid="stColumn"]:nth-child(3) button p,
.ai-search-form-dock div[data-testid="stColumn"]:nth-child(3) button span,
.ai-search-form-dock div[data-testid="stColumn"]:nth-child(3) button div {
    font-size: 14px !important;
    font-weight: 500 !important;
    margin: 0 !important;
    padding: 0 !important;
    line-height: 1 !important;
    white-space: nowrap !important;
    word-break: keep-all !important;
    overflow-wrap: normal !important;
    display: inline !important;
}

/* 4. Col 4: Microphone Icon (🎙️) */
div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(4),
.ai-search-form-dock div[data-testid="stColumn"]:nth-child(4) {
    flex: 0 0 36px !important;
    width: 36px !important;
    min-width: 36px !important;
    max-width: 36px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 0 !important;
    margin: 0 !important;
}

div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(4) button,
.ai-search-form-dock div[data-testid="stColumn"]:nth-child(4) button {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #1f2937 !important;
    width: 34px !important;
    height: 34px !important;
    min-width: 34px !important;
    min-height: 34px !important;
    border-radius: 50% !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 0 !important;
    margin: 0 !important;
    cursor: pointer !important;
    transition: all 0.15s ease !important;
}

div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(4) button:hover,
.ai-search-form-dock div[data-testid="stColumn"]:nth-child(4) button:hover {
    background: #f4f4f5 !important;
    background-color: #f4f4f5 !important;
    color: #000000 !important;
    transform: scale(1.08) !important;
}

div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(4) button::before,
.ai-search-form-dock div[data-testid="stColumn"]:nth-child(4) button::before {
    content: "" !important;
    display: inline-block !important;
    width: 19px !important;
    height: 19px !important;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='%23222222' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z'/%3E%3Cpath d='M19 10v2a7 7 0 0 1-14 0v-2'/%3E%3Cline x1='12' x2='12' y1='19' y2='22'/%3E%3C/svg%3E") !important;
    background-repeat: no-repeat !important;
    background-size: contain !important;
}

div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(4) button svg,
.ai-search-form-dock div[data-testid="stColumn"]:nth-child(4) button svg,
div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(4) [data-testid="stPopoverChevron"],
.ai-search-form-dock div[data-testid="stColumn"]:nth-child(4) [data-testid="stPopoverChevron"],
div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(4) button p,
div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(4) button span {
    display: none !important;
    visibility: hidden !important;
    width: 0 !important;
    height: 0 !important;
}

/* 5. Col 5: Blue Circular Waveform Submit Button (||||) */
div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(5),
.ai-search-form-dock div[data-testid="stColumn"]:nth-child(5) {
    flex: 0 0 42px !important;
    width: 42px !important;
    min-width: 42px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 0 !important;
    margin: 0 !important;
}

div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(5) button,
.ai-search-form-dock div[data-testid="stColumn"]:nth-child(5) button {
    width: 38px !important;
    height: 38px !important;
    min-width: 38px !important;
    min-height: 38px !important;
    max-width: 38px !important;
    max-height: 38px !important;
    border-radius: 50% !important;
    background: #1d72fe !important;
    background-color: #1d72fe !important;
    border: none !important;
    box-shadow: 0 2px 8px rgba(29, 114, 254, 0.35) !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 0 !important;
    margin: 0 !important;
    cursor: pointer !important;
    transition: background 0.15s ease, transform 0.12s ease, box-shadow 0.15s ease !important;
}

div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(5) button:hover,
.ai-search-form-dock div[data-testid="stColumn"]:nth-child(5) button:hover {
    background: #155bd5 !important;
    background-color: #155bd5 !important;
    transform: scale(1.06) !important;
    box-shadow: 0 4px 14px rgba(29, 114, 254, 0.45) !important;
}

div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(5) button:active,
.ai-search-form-dock div[data-testid="stColumn"]:nth-child(5) button:active {
    transform: scale(0.96) !important;
}

/* Crisp 4 white sound wave bars */
div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(5) button::before,
.ai-search-form-dock div[data-testid="stColumn"]:nth-child(5) button::before {
    content: "" !important;
    display: inline-block !important;
    width: 20px !important;
    height: 20px !important;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none'%3E%3Cline x1='6' y1='8.5' x2='6' y2='15.5' stroke='white' stroke-width='2.6' stroke-linecap='round'/%3E%3Cline x1='10.5' y1='4.5' x2='10.5' y2='19.5' stroke='white' stroke-width='2.6' stroke-linecap='round'/%3E%3Cline x1='15' y1='7' x2='15' y2='17' stroke='white' stroke-width='2.6' stroke-linecap='round'/%3E%3Cline x1='19' y1='9.5' x2='19' y2='14.5' stroke='white' stroke-width='2.6' stroke-linecap='round'/%3E%3C/svg%3E") !important;
    background-repeat: no-repeat !important;
    background-size: contain !important;
}

div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(5) button p,
div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(5) button span {
    display: none !important;
}

/* Search Mode Segmented Control & Suggestion Chips */
div[data-testid="stSegmentedControl"] {
    background: #ffffff !important;
    border: 1.5px solid #e2e8f0 !important;
    border-radius: 9999px !important;
    padding: 2px 4px !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04) !important;
    display: inline-flex !important;
    width: auto !important;
}

div[data-testid="stSegmentedControl"] button {
    border-radius: 9999px !important;
    border: none !important;
    background: transparent !important;
    color: #475569 !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 3px 12px !important;
    transition: all 0.16s ease !important;
}

div[data-testid="stSegmentedControl"] button[aria-checked="true"],
div[data-testid="stSegmentedControl"] button[data-checked="true"],
div[data-testid="stSegmentedControl"] button[aria-pressed="true"] {
    background: #2563eb !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 6px rgba(37, 99, 235, 0.28) !important;
}

div[data-testid="stSegmentedControl"] button:hover {
    color: #111827 !important;
    background: #f1f5f9 !important;
}

div[class*="st-key-sug_btn_"] button {
    border-radius: 9999px !important;
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    color: #334155 !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    padding: 4px 10px !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03) !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1) !important;
}

div[class*="st-key-sug_btn_"] button:hover {
    border-color: #3b82f6 !important;
    color: #2563eb !important;
    background: #eff6ff !important;
    transform: translateY(-1px) scale(1.02) !important;
    box-shadow: 0 3px 8px rgba(37, 99, 235, 0.12) !important;
}

/* Dark Mode Support for Dock */
@media (prefers-color-scheme: dark) {
    div[data-testid="stForm"],
    .ai-search-form-dock {
        background: #212121 !important;
        background-color: #212121 !important;
        border-color: #303030 !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3) !important;
    }
    div[data-testid="stForm"]:hover,
    .ai-search-form-dock:hover {
        border-color: #424242 !important;
    }
    div[data-testid="stForm"]:focus-within,
    .ai-search-form-dock:focus-within {
        border-color: #3b82f6 !important;
    }
    div[data-testid="stForm"] div[data-testid="stTextInput"] input,
    div[data-testid="stForm"] div[data-testid="stTextArea"] textarea,
    .ai-search-form-dock div[data-testid="stTextInput"] input,
    .ai-search-form-dock div[data-testid="stTextArea"] textarea {
        color: #f3f4f6 !important;
    }
    div[data-testid="stForm"] div[data-testid="stTextInput"] input::placeholder,
    div[data-testid="stForm"] div[data-testid="stTextArea"] textarea::placeholder,
    .ai-search-form-dock div[data-testid="stTextInput"] input::placeholder,
    .ai-search-form-dock div[data-testid="stTextArea"] textarea::placeholder {
        color: #71717a !important;
    }
    div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(1) button {
        color: #e5e7eb !important;
    }
    div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(1) button:hover {
        background: #2f2f2f !important;
    }
    div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(3) button {
        color: #9ca3af !important;
    }
    div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(3) button:hover {
        background: #2f2f2f !important;
        color: #f3f4f6 !important;
    }
    div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(4) button:hover {
        background: #2f2f2f !important;
    }
    div[data-testid="stForm"] div[data-testid="stColumn"]:nth-child(4) button::before {
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='%23e5e7eb' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z'/%3E%3Cpath d='M19 10v2a7 7 0 0 1-14 0v-2'/%3E%3Cline x1='12' x2='12' y1='19' y2='22'/%3E%3C/svg%3E") !important;
    }
}

/* ----------------------------------------------------
   Document Attachment Popover (Modern Light Look)
   ---------------------------------------------------- */
div[data-testid="stPopoverBody"]:has(div[data-testid="stFileUploader"]) {
    background: #FFFFFF !important;
    background-color: #FFFFFF !important;
    border-radius: 16px !important;
    border: 1.5px solid #DCE7FA !important;
    box-shadow: 0 10px 30px -6px rgba(47, 128, 237, 0.12),
                0 3px 10px -2px rgba(20, 35, 59, 0.04) !important;
    color: #14233B !important;
    padding: 12px 14px !important;
    width: 310px !important;
    max-width: min(310px, calc(100vw - 32px)) !important;
    font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif !important;
    animation: popoverFadeSlideIn 0.22s cubic-bezier(0.16, 1, 0.3, 1) !important;
    overflow: visible !important;
    box-sizing: border-box !important;
}

/* Generic Form Popovers (Voice & Think) */
div[data-testid="stForm"] div[data-testid="stPopoverBody"]:not(:has(div[data-testid="stFileUploader"])) {
    background: #FFFFFF !important;
    background-color: #FFFFFF !important;
    border-radius: 16px !important;
    border: 1.5px solid #DCE7FA !important;
    box-shadow: 0 10px 30px -6px rgba(47, 128, 237, 0.12),
                0 3px 10px -2px rgba(20, 35, 59, 0.04) !important;
    color: #14233B !important;
    padding: 12px 14px !important;
    width: 320px !important;
    max-width: min(320px, calc(100vw - 32px)) !important;
    font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif !important;
    box-sizing: border-box !important;
}

@keyframes popoverFadeSlideIn {
    0% {
        opacity: 0;
        transform: translateY(8px) scale(0.98);
    }
    100% {
        opacity: 1;
        transform: translateY(0) scale(1);
    }
}

/* Header: 30px compact rounded gradient badge with folder icon */
.popover-attach-header {
    display: flex !important;
    align-items: center !important;
    gap: 10px !important;
    margin-bottom: 8px !important;
}

.popover-badge-icon {
    width: 30px !important;
    height: 30px !important;
    min-width: 30px !important;
    min-height: 30px !important;
    border-radius: 8px !important;
    background: linear-gradient(135deg, #2F80ED 0%, #7C5CFF 100%) !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    color: #ffffff !important;
    box-shadow: 0 2px 8px rgba(47, 128, 237, 0.25) !important;
    flex-shrink: 0 !important;
}

.popover-badge-icon svg {
    width: 16px !important;
    height: 16px !important;
    stroke: #ffffff !important;
}

.popover-header-text {
    display: flex !important;
    flex-direction: column !important;
}

.popover-title {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 14.5px !important;
    font-weight: 700 !important;
    color: #14233B !important;
    line-height: 1.25 !important;
    letter-spacing: -0.01em !important;
    margin: 0 !important;
}

.popover-subtitle {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 11px !important;
    font-weight: 500 !important;
    color: #8A99B2 !important;
    line-height: 1.3 !important;
    margin: 1px 0 0 0 !important;
}

/* Dropzone: compact 1.5px dashed, 12px radius, minimal padding */
div[data-testid="stPopoverBody"] div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"],
div[data-testid="stPopoverBody"] div[data-testid="stFileUploader"] section {
    background: #FAFCFF !important;
    background-color: #FAFCFF !important;
    border: 1.5px dashed #C9D8F3 !important;
    border-radius: 12px !important;
    padding: 10px 8px !important;
    text-align: center !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    cursor: pointer !important;
    transition: border-color 0.2s ease, background-color 0.2s ease, box-shadow 0.2s ease !important;
    position: relative !important;
    margin-top: 4px !important;
    min-height: unset !important;
}

/* Hover and drag-over: border turns #2F80ED and the background turns #F1F7FF */
div[data-testid="stPopoverBody"] div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"]:hover,
div[data-testid="stPopoverBody"] div[data-testid="stFileUploader"] section:hover,
div[data-testid="stPopoverBody"] div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"]:focus-within,
div[data-testid="stPopoverBody"] div[data-testid="stFileUploader"] section:focus-within {
    border-color: #2F80ED !important;
    background: #F1F7FF !important;
    background-color: #F1F7FF !important;
    box-shadow: 0 2px 10px rgba(47, 128, 237, 0.08) !important;
}

/* Centered upload icon in a light-blue circle (compact 28px) */
div[data-testid="stPopoverBody"] div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"]::before,
div[data-testid="stPopoverBody"] div[data-testid="stFileUploader"] section::before {
    content: "" !important;
    display: block !important;
    width: 28px !important;
    height: 28px !important;
    border-radius: 50% !important;
    background: #EBF3FE url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%232F80ED' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4'/%3E%3Cpolyline points='17 8 12 3 7 8'/%3E%3Cline x1='12' y1='3' x2='12' y2='15'/%3E%3C/svg%3E") no-repeat center !important;
    margin: 0 auto 6px auto !important;
    transition: transform 0.2s ease !important;
    box-shadow: 0 1px 4px rgba(47, 128, 237, 0.12) !important;
}

div[data-testid="stPopoverBody"] div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"]:hover::before,
div[data-testid="stPopoverBody"] div[data-testid="stFileUploader"] section:hover::before {
    transform: translateY(-1px) scale(1.04) !important;
}

/* Hide Streamlit default file uploader label */
div[data-testid="stPopoverBody"] div[data-testid="stFileUploader"] label,
div[data-testid="stPopoverBody"] div[data-testid="stFileUploader"] [data-testid="stWidgetLabel"] {
    display: none !important;
}

/* Dropzone instruction text replacement: "Drag and drop files, or browse" & "Up to 200MB per file" */
div[data-testid="stPopoverBody"] [data-testid="stFileUploaderDropzoneInstructions"],
div[data-testid="stPopoverBody"] [data-testid="stFileUploaderInstructions"] {
    font-size: 0 !important;
    color: transparent !important;
    line-height: 0 !important;
    margin-top: 6px !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
}

div[data-testid="stPopoverBody"] [data-testid="stFileUploaderDropzoneInstructions"] *,
div[data-testid="stPopoverBody"] [data-testid="stFileUploaderInstructions"] *,
div[data-testid="stPopoverBody"] [data-testid="stFileUploaderFileLimit"] {
    font-size: 0 !important;
    color: transparent !important;
    display: none !important;
    visibility: hidden !important;
}

div[data-testid="stPopoverBody"] [data-testid="stFileUploaderDropzoneInstructions"]::before,
div[data-testid="stPopoverBody"] [data-testid="stFileUploaderInstructions"]::before {
    content: "Drag & drop or browse files" !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 11.5px !important;
    font-weight: 600 !important;
    color: #14233B !important;
    line-height: 1.3 !important;
    display: block !important;
    margin-bottom: 1px !important;
}

div[data-testid="stPopoverBody"] [data-testid="stFileUploaderDropzoneInstructions"]::after,
div[data-testid="stPopoverBody"] [data-testid="stFileUploaderInstructions"]::after {
    content: "Up to 200MB per file" !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 10px !important;
    font-weight: 500 !important;
    color: #8A99B2 !important;
    line-height: 1.3 !important;
    display: block !important;
}

/* Pill-shaped, gradient fill buttons inside popover with small lift on hover (compact 28px height) */
div[data-testid="stPopoverBody"] div[data-testid="stFileUploaderDropzone"] button,
div[data-testid="stPopoverBody"] div[data-testid="stFileUploader"] section button:not([data-testid="stFileChipDeleteBtn"] button),
div[data-testid="stPopoverBody"] button[data-testid="stBaseButton-secondary"]:not([data-testid="stFileChipDeleteBtn"] button) {
    background: linear-gradient(135deg, #2F80ED 0%, #7C5CFF 100%) !important;
    background-color: #2F80ED !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 9999px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 12px !important;
    padding: 4px 14px !important;
    height: 28px !important;
    min-height: 28px !important;
    box-shadow: 0 2px 8px rgba(47, 128, 237, 0.2) !important;
    cursor: pointer !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
}

div[data-testid="stPopoverBody"] div[data-testid="stFileUploaderDropzone"] button:hover,
div[data-testid="stPopoverBody"] div[data-testid="stFileUploader"] section button:not([data-testid="stFileChipDeleteBtn"] button):hover,
div[data-testid="stPopoverBody"] button[data-testid="stBaseButton-secondary"]:not([data-testid="stFileChipDeleteBtn"] button):hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(47, 128, 237, 0.3) !important;
    color: #ffffff !important;
}

div[data-testid="stPopoverBody"] div[data-testid="stFileUploaderDropzone"] button span,
div[data-testid="stPopoverBody"] div[data-testid="stFileUploaderDropzone"] button p,
div[data-testid="stPopoverBody"] button[data-testid="stBaseButton-secondary"] span,
div[data-testid="stPopoverBody"] button[data-testid="stBaseButton-secondary"] p {
    color: #ffffff !important;
    font-weight: 600 !important;
    font-size: 12px !important;
}

/* ----------------------------------------------------
   Uploaded File Rows:
   White cards with a 1.5px border #DCE7FA and 14px radius.
   Left: 40px colour-coded icon (PDF red, CSV/Excel green, Word blue, PY amber, JSON orange, TXT/MD grey).
   Middle: file name (weight 600, ellipsis on overflow) with size in muted text below.
   Right: green "Ready" tick and round remove button that turns red on hover.
   ---------------------------------------------------- */

/* Dropzone when files exist: hide the large upload icon circle and tighten padding */
div[data-testid="stPopoverBody"] [data-testid="stFileUploaderDropzone"]:has([data-testid="stFileChip"])::before,
div[data-testid="stPopoverBody"] div[data-testid="stFileUploader"] section:has([data-testid="stFileChip"])::before {
    display: none !important;
}

div[data-testid="stPopoverBody"] [data-testid="stFileUploaderDropzone"]:has([data-testid="stFileChip"]),
div[data-testid="stPopoverBody"] div[data-testid="stFileUploader"] section:has([data-testid="stFileChip"]) {
    padding: 12px 14px 14px 14px !important;
    align-items: stretch !important;
}

/* Streamlit Native File Chips container */
div[data-testid="stPopoverBody"] div[data-testid="stFileChips"] {
    display: flex !important;
    flex-direction: column !important;
    gap: 8px !important;
    width: 100% !important;
    margin: 4px 0 !important;
    padding: 0 !important;
}

div[data-testid="stPopoverBody"] div[data-testid="stFileChips"] > div {
    display: contents !important;
}

/* Ke wrapper element: MUST NOT have background/border/padding so it doesn't wrap or double-box */
div[data-testid="stPopoverBody"] div[data-testid="stFileChips"] > div > div {
    display: block !important;
    width: 100% !important;
    max-width: 100% !important;
    flex: 1 1 100% !important;
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    padding: 0 !important;
    margin: 0 !important;
    box-shadow: none !important;
}

/* Each file card: qe is div[data-testid="stFileChip"] */
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"],
.styled-uploaded-card {
    width: 100% !important;
    min-width: 100% !important;
    max-width: 100% !important;
    box-sizing: border-box !important;
    background: #FFFFFF !important;
    background-color: #FFFFFF !important;
    border: 1.5px solid #DCE7FA !important;
    border-radius: 14px !important;
    padding: 10px 14px !important;
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    justify-content: flex-start !important;
    gap: 12px !important;
    box-shadow: 0 2px 8px rgba(20, 35, 59, 0.04) !important;
    margin: 4px 0 !important;
    cursor: default !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
}

div[data-testid="stPopoverBody"] div[data-testid="stFileChip"]:hover,
.styled-uploaded-card:hover {
    border-color: #C9D8F3 !important;
    box-shadow: 0 4px 14px rgba(47, 128, 237, 0.08) !important;
}

/* Left: 40px colour-coded icon container (Ye) */
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"] > div:first-child,
.custom-file-icon-badge {
    width: 40px !important;
    height: 40px !important;
    min-width: 40px !important;
    min-height: 40px !important;
    max-width: 40px !important;
    max-height: 40px !important;
    border-radius: 10px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    flex-shrink: 0 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 11px !important;
    font-weight: 800 !important;
    letter-spacing: -0.02em !important;
    text-transform: uppercase !important;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04) !important;
    background: #F3F4F6 !important;
    background-color: #F3F4F6 !important;
    color: #4B5563 !important;
    border: 1px solid #E5E7EB !important;
    margin: 0 !important;
    padding: 0 !important;
}

div[data-testid="stPopoverBody"] div[data-testid="stFileChip"] > div:first-child svg {
    width: 20px !important;
    height: 20px !important;
}

/* PDF red */
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"]:has([title*=".pdf" i]) > div:first-child,
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"]:has([data-testid="stFileChipName"][title*=".pdf" i]) > div:first-child,
.badge-ext-pdf, div[data-file-ext="pdf"] .custom-file-icon-badge {
    background: #FEE2E2 !important;
    background-color: #FEE2E2 !important;
    color: #DC2626 !important;
    border: 1px solid #FECACA !important;
}
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"]:has([title*=".pdf" i]) > div:first-child svg {
    color: #DC2626 !important;
    fill: #DC2626 !important;
}

/* CSV / Excel green */
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"]:has([title*=".csv" i]) > div:first-child,
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"]:has([title*=".xlsx" i]) > div:first-child,
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"]:has([title*=".xls" i]) > div:first-child,
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"]:has([data-testid="stFileChipName"][title*=".csv" i]) > div:first-child,
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"]:has([data-testid="stFileChipName"][title*=".xlsx" i]) > div:first-child,
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"]:has([data-testid="stFileChipName"][title*=".xls" i]) > div:first-child,
.badge-ext-csv, .badge-ext-xlsx, .badge-ext-xls,
div[data-file-ext="csv"] .custom-file-icon-badge,
div[data-file-ext="xlsx"] .custom-file-icon-badge,
div[data-file-ext="xls"] .custom-file-icon-badge {
    background: #D1FAE5 !important;
    background-color: #D1FAE5 !important;
    color: #059669 !important;
    border: 1px solid #A7F3D0 !important;
}
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"]:has([title*=".csv" i]) > div:first-child svg,
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"]:has([title*=".xlsx" i]) > div:first-child svg,
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"]:has([title*=".xls" i]) > div:first-child svg {
    color: #059669 !important;
    fill: #059669 !important;
}

/* Word blue */
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"]:has([title*=".docx" i]) > div:first-child,
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"]:has([title*=".doc" i]) > div:first-child,
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"]:has([data-testid="stFileChipName"][title*=".docx" i]) > div:first-child,
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"]:has([data-testid="stFileChipName"][title*=".doc" i]) > div:first-child,
.badge-ext-docx, .badge-ext-doc,
div[data-file-ext="docx"] .custom-file-icon-badge,
div[data-file-ext="doc"] .custom-file-icon-badge {
    background: #DBEAFE !important;
    background-color: #DBEAFE !important;
    color: #2563EB !important;
    border: 1px solid #BFDBFE !important;
}
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"]:has([title*=".docx" i]) > div:first-child svg,
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"]:has([title*=".doc" i]) > div:first-child svg {
    color: #2563EB !important;
    fill: #2563EB !important;
}

/* PY amber */
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"]:has([title*=".py" i]) > div:first-child,
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"]:has([data-testid="stFileChipName"][title*=".py" i]) > div:first-child,
.badge-ext-py, div[data-file-ext="py"] .custom-file-icon-badge {
    background: #FEF3C7 !important;
    background-color: #FEF3C7 !important;
    color: #D97706 !important;
    border: 1px solid #FDE68A !important;
}
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"]:has([title*=".py" i]) > div:first-child svg {
    color: #D97706 !important;
    fill: #D97706 !important;
}

/* JSON orange */
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"]:has([title*=".json" i]) > div:first-child,
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"]:has([data-testid="stFileChipName"][title*=".json" i]) > div:first-child,
.badge-ext-json, div[data-file-ext="json"] .custom-file-icon-badge {
    background: #FFEDD5 !important;
    background-color: #FFEDD5 !important;
    color: #EA580C !important;
    border: 1px solid #FED7AA !important;
}
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"]:has([title*=".json" i]) > div:first-child svg {
    color: #EA580C !important;
    fill: #EA580C !important;
}

/* TXT / MD grey */
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"]:has([title*=".txt" i]) > div:first-child,
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"]:has([title*=".md" i]) > div:first-child,
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"]:has([data-testid="stFileChipName"][title*=".txt" i]) > div:first-child,
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"]:has([data-testid="stFileChipName"][title*=".md" i]) > div:first-child,
.badge-ext-txt, .badge-ext-md,
div[data-file-ext="txt"] .custom-file-icon-badge,
div[data-file-ext="md"] .custom-file-icon-badge {
    background: #F3F4F6 !important;
    background-color: #F3F4F6 !important;
    color: #4B5563 !important;
    border: 1px solid #E5E7EB !important;
}
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"]:has([title*=".txt" i]) > div:first-child svg,
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"]:has([title*=".md" i]) > div:first-child svg {
    color: #4B5563 !important;
    fill: #4B5563 !important;
}

/* Middle: file name (weight 600, ellipsis on overflow) with size in muted text below (Je) */
div[data-testid="stPopoverBody"] div[data-testid="stFileChip"] > div:nth-child(2),
.file-card-info {
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    align-items: flex-start !important;
    min-width: 0 !important;
    flex: 1 1 auto !important;
    overflow: hidden !important;
    gap: 3px !important;
    padding: 0 4px !important;
    text-align: left !important;
}

div[data-testid="stPopoverBody"] div[data-testid="stFileChip"] [data-testid="stFileChipName"],
.file-card-name {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 13.5px !important;
    font-weight: 600 !important;
    color: #14233B !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    line-height: 1.3 !important;
    display: block !important;
    width: 100% !important;
    max-width: 100% !important;
    text-align: left !important;
}

div[data-testid="stPopoverBody"] div[data-testid="stFileChip"] [data-testid="stFileChipName"] + *,
.file-card-size {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 11.5px !important;
    color: #8A99B2 !important;
    font-weight: 500 !important;
    line-height: 1.2 !important;
    display: block !important;
    text-align: left !important;
}

/* Right: Green "Ready" tick and round remove button that turns red on hover ($e) */
div[data-testid="stPopoverBody"] [data-testid="stFileChipDeleteBtn"] {
    display: inline-flex !important;
    align-items: center !important;
    margin-left: auto !important;
    flex-shrink: 0 !important;
    gap: 8px !important;
}

/* Green "Ready" tick */
div[data-testid="stPopoverBody"] [data-testid="stFileChipDeleteBtn"]::before,
.custom-ready-badge {
    content: "✓ Ready" !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    color: #10B981 !important;
    background: #ECFDF5 !important;
    background-color: #ECFDF5 !important;
    border: 1px solid #A7F3D0 !important;
    padding: 3px 8px !important;
    border-radius: 9999px !important;
    white-space: nowrap !important;
    display: inline-flex !important;
    align-items: center !important;
    line-height: 1 !important;
}

.custom-ready-badge {
    margin-left: auto !important;
}

/* Round remove button that turns red on hover */
div[data-testid="stPopoverBody"] [data-testid="stFileChipDeleteBtn"] button,
div[data-testid="stPopoverBody"] div[data-testid="stFileUploader"] button[aria-label*="Delete"],
div[data-testid="stPopoverBody"] div[data-testid="stFileUploader"] button[aria-label*="remove"],
div[data-testid="stPopoverBody"] div[data-testid="stFileUploader"] button[aria-label*="clear"] {
    width: 28px !important;
    height: 28px !important;
    min-width: 28px !important;
    min-height: 28px !important;
    max-width: 28px !important;
    max-height: 28px !important;
    border-radius: 50% !important;
    background: #F1F5F9 !important;
    background-color: #F1F5F9 !important;
    border: 1px solid #E2E8F0 !important;
    color: #64748B !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 0 !important;
    cursor: pointer !important;
    transition: all 0.15s ease !important;
    box-shadow: none !important;
}

div[data-testid="stPopoverBody"] [data-testid="stFileChipDeleteBtn"] button:hover,
div[data-testid="stPopoverBody"] div[data-testid="stFileUploader"] button[aria-label*="Delete"]:hover,
div[data-testid="stPopoverBody"] div[data-testid="stFileUploader"] button[aria-label*="remove"]:hover,
div[data-testid="stPopoverBody"] div[data-testid="stFileUploader"] button[aria-label*="clear"]:hover {
    background: #FEE2E2 !important;
    background-color: #FEE2E2 !important;
    border-color: #FECACA !important;
    color: #EF4444 !important;
    transform: scale(1.08) !important;
}

div[data-testid="stPopoverBody"] [data-testid="stFileChipDeleteBtn"] button:hover svg {
    color: #EF4444 !important;
    fill: #EF4444 !important;
}

/* Secondary "Add files" button inside dropzone */
div[data-testid="stPopoverBody"] button[aria-label="Add files"] {
    width: 34px !important;
    height: 34px !important;
    min-width: 34px !important;
    min-height: 34px !important;
    border-radius: 50% !important;
    background: #F1F7FF !important;
    background-color: #F1F7FF !important;
    border: 1.5px dashed #2F80ED !important;
    color: #2F80ED !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 0 !important;
    margin: 8px auto 2px auto !important;
    box-shadow: none !important;
    cursor: pointer !important;
    transition: all 0.15s ease !important;
}

div[data-testid="stPopoverBody"] button[aria-label="Add files"]:hover {
    background: #DBEAFE !important;
    background-color: #DBEAFE !important;
    color: #1D4ED8 !important;
    border-color: #1D4ED8 !important;
    transform: scale(1.06) !important;
}

/* Custom Uploaded Cards container fallback */
.attached-files-container {
    display: flex !important;
    flex-direction: column !important;
    gap: 8px !important;
    margin-top: 14px !important;
}

.styled-uploaded-card {
    background: #FFFFFF !important;
    border: 1.5px solid #DCE7FA !important;
    border-radius: 14px !important;
    padding: 10px 14px !important;
    display: flex !important;
    align-items: center !important;
    gap: 12px !important;
    box-shadow: 0 2px 8px rgba(20, 35, 59, 0.04) !important;
    transition: all 0.15s ease !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

.styled-uploaded-card:hover {
    border-color: #C9D8F3 !important;
    box-shadow: 0 4px 12px rgba(47, 128, 237, 0.08) !important;
}

/* Visible keyboard focus rings */
div[data-testid="stPopoverBody"] *:focus-visible,
div[data-testid="stForm"] div[data-testid="stPopover"] > button:focus-visible {
    outline: 2px solid #2F80ED !important;
    outline-offset: 2px !important;
}

/* Respect prefers-reduced-motion */
@media (prefers-reduced-motion: reduce) {
    div[data-testid="stPopoverBody"],
    div[data-testid="stPopoverBody"] *,
    div[data-testid="stForm"] div[data-testid="stPopover"] > button {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }
}

/* End of popover styles */

/* Hidden iframe for keyboard events */
iframe[title="st.iframe"] {
    position: absolute !important;
    width: 0 !important;
    height: 0 !important;
    border: none !important;
    opacity: 0 !important;
    pointer-events: none !important;
    overflow: hidden !important;
}

/* Sidebar Group Headings (Today, Yesterday, Previous 7 days) */
.sidebar-date-heading {
    display: block !important;
    font-size: 11px !important;
}

/* ----------------------------------------------------
   SPARK-AI Left Sidebar (Original Image Style)
   ---------------------------------------------------- */
[data-testid="stSidebar"] {
    background-color: #ffffff !important;
    border-right: 1px solid #e2e8f0 !important;
}

[data-testid="stSidebarUserContent"] {
    padding-top: 1rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
}

/* 1. Dark Navy Top Brand Card */
.sidebar-brand-card {
    background: #030826 !important;
    background-color: #030826 !important;
    border-radius: 14px !important;
    padding: 16px 18px !important;
    display: flex !important;
    align-items: center !important;
    gap: 14px !important;
    margin-bottom: 12px !important;
    box-shadow: 0 4px 14px rgba(3, 8, 38, 0.22) !important;
    width: 100% !important;
    box-sizing: border-box !important;
}

.sidebar-spark-glow {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    filter: drop-shadow(0 0 7px rgba(56, 189, 248, 0.95)) !important;
    flex-shrink: 0 !important;
}

.sidebar-brand-title {
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif !important;
    font-size: 1.3rem !important;
    font-weight: 800 !important;
    color: #ffffff !important;
    letter-spacing: 0.04em !important;
    line-height: 1 !important;
}

/* 2. Soft Pastel Blue "New chat" Button */
div[class*="st-key-btn_new_chat"] button {
    background: #d4e7fe !important;
    background-color: #d4e7fe !important;
    border: 1.5px solid #bddbff !important;
    border-radius: 10px !important;
    color: #1e40af !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    text-align: left !important;
    justify-content: flex-start !important;
    padding: 10px 14px !important;
    margin-bottom: 10px !important;
    box-shadow: none !important;
    width: 100% !important;
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
    transition: all 0.15s ease !important;
}

div[class*="st-key-btn_new_chat"] button:hover {
    background: #c5ddfc !important;
    border-color: #93c5fd !important;
    color: #1e3a8a !important;
}

/* 3. Search Input Box */
div[data-testid="stSidebar"] div[data-testid="stTextInput"] input {
    background: #ffffff !important;
    background-color: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 10px !important;
    font-size: 13.5px !important;
    padding: 9px 12px !important;
    color: #0f172a !important;
    box-shadow: none !important;
}

div[data-testid="stSidebar"] div[data-testid="stTextInput"] input::placeholder {
    color: #94a3b8 !important;
}

/* 4. "Recent" Heading */
.sidebar-recent-heading {
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    color: #64748b !important;
    margin: 16px 4px 8px 4px !important;
}

/* 5. Clean List Items for Recent Chats */
div[class*="st-key-chat_item_"] button {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    border-radius: 8px !important;
    color: #334155 !important;
    font-weight: 400 !important;
    font-size: 14px !important;
    text-align: left !important;
    justify-content: flex-start !important;
    padding: 7px 8px !important;
    margin: 1px 0 !important;
    box-shadow: none !important;
    width: 100% !important;
    transition: all 0.12s ease !important;
}

div[class*="st-key-chat_item_"] button:hover {
    background: #f1f5f9 !important;
    color: #0f172a !important;
}

div[class*="st-key-chat_item_active_"] button {
    background: #eef2ff !important;
    color: #1d4ed8 !important;
    font-weight: 600 !important;
}

/* 6. Sidebar Account Footer Button & Link */
.sidebar-account-link {
    display: flex !important;
    align-items: center !important;
    gap: 12px !important;
    border-top: 1px solid #e2e8f0 !important;
    margin-top: 24px !important;
    padding-top: 14px !important;
    padding-bottom: 6px !important;
    text-decoration: none !important;
    cursor: pointer !important;
    width: 100% !important;
    box-sizing: border-box !important;
}

.sidebar-account-text {
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    color: #334155 !important;
    transition: color 0.15s ease !important;
}

.sidebar-account-link:hover .sidebar-account-text {
    color: #0f172a !important;
}

div[class*="st-key-btn_account_row"] button {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    border-top: 1px solid #e2e8f0 !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    color: #334155 !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    text-align: left !important;
    justify-content: flex-start !important;
    padding: 14px 4px !important;
    margin-top: 20px !important;
    width: 100% !important;
    display: flex !important;
    align-items: center !important;
    gap: 12px !important;
}

div[class*="st-key-btn_account_row"] button:hover {
    background: #f8fafc !important;
    color: #0f172a !important;
}

.sidebar-avatar-circle {
    width: 32px !important;
    height: 32px !important;
    min-width: 32px !important;
    min-height: 32px !important;
    border-radius: 50% !important;
    background: #d4e7fe !important;
    color: #1e40af !important;
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    flex-shrink: 0 !important;
}

/* Sidebar Group Headings (Today, Yesterday, Previous 7 days) */
.sidebar-date-heading {
    display: block !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    color: #64748b !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    padding: 16px 6px 6px 6px !important;
    margin: 0 !important;
    line-height: 1.3 !important;
    box-sizing: border-box !important;
    user-select: none !important;
}

div[class*="st-key-sb_active_"] button {
    background: #eef2ff !important;
    background-color: #eef2ff !important;
    border: none !important;
    border-left: 3.5px solid #4f46e5 !important;
    border-radius: 2px 8px 8px 2px !important;
    color: #0f172a !important;
    font-weight: 700 !important;
    font-size: 13.5px !important;
    text-align: left !important;
    justify-content: flex-start !important;
    padding-left: 12px !important;
    height: 38px !important;
    min-height: 38px !important;
    box-shadow: none !important;
    width: 100% !important;
    margin: 1px 0 !important;
}
div[class*="st-key-sb_active_"] button:hover {
    background: #e0e7ff !important;
    color: #0f172a !important;
}

div[class*="st-key-sb_inact_"] button {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    color: #334155 !important;
    font-weight: 500 !important;
    font-size: 13.5px !important;
    text-align: left !important;
    justify-content: flex-start !important;
    border-radius: 8px !important;
    padding-left: 12px !important;
    height: 38px !important;
    min-height: 38px !important;
    box-shadow: none !important;
    width: 100% !important;
    margin: 1px 0 !important;
}
div[class*="st-key-sb_inact_"] button:hover {
    background: #f1f5f9 !important;
    color: #0f172a !important;
}

/* 3-Dots hover effect in sidebar rows */
div[class*="st-key-pop_opts_"] {
    opacity: 0 !important;
    transition: opacity 160ms ease !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
div[data-testid="stHorizontalBlock"]:hover div[class*="st-key-pop_opts_"] {
    opacity: 1 !important;
}

/* Sidebar Bottom 4 Utility Buttons */
.sidebar-footer-buttons button,
div[class*="st-key-sb_btn_"] button {
    background: #ffffff !important;
    background-color: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    color: #334155 !important;
    font-size: 11.5px !important;
    font-weight: 500 !important;
    padding: 4px 1px !important;
    min-height: 40px !important;
    height: 40px !important;
    line-height: 1.15 !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03) !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    text-align: center !important;
    transition: all 120ms ease !important;
}

.sidebar-footer-buttons button:hover,
div[class*="st-key-sb_btn_"] button:hover {
    background: #f8fafc !important;
    border-color: #cbd5e1 !important;
    color: #0f172a !important;
}

/* Sidebar Collapsibles */
[data-testid="stSidebar"] [data-testid="stExpander"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    margin-bottom: 0px !important;
    border-radius: 0 !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] details {
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 8px 6px !important;
    color: #334155 !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    width: 100% !important;
    cursor: pointer !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover {
    color: #0f172a !important;
    background: rgba(0, 0, 0, 0.02) !important;
    border-radius: 6px !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary svg,
[data-testid="stSidebar"] [data-testid="stExpander"] summary [data-testid="stIconMaterial"] {
    display: none !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary::after {
    content: "+" !important;
    font-size: 18px !important;
    color: #64748b !important;
    font-weight: 400 !important;
    margin-left: auto !important;
    line-height: 1 !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"][open] summary::after {
    content: "−" !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
    border: none !important;
    border-top: 1px solid #f1f5f9 !important;
    background: transparent !important;
    padding: 8px 6px !important;
}


/* ----------------------------------------------------
   9. Sidebar Styling & Form Controls
   ---------------------------------------------------- */
[data-testid="stSidebar"] {
    background-color: var(--bg-sidebar) !important;
    color: var(--text-primary) !important;
    border-right: 1px solid var(--border-subtle) !important;
}

.sidebar-section-label {
    font-size: 0.74rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    color: var(--text-secondary) !important; /* Clear readable contrast */
    margin-top: 1.25rem !important;
    margin-bottom: 0.5rem !important;
    display: flex !important;
    align-items: center !important;
    gap: 6px !important;
}

[data-testid="stSidebar"] label,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
    color: var(--text-primary) !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
}

[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p,
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] small,
[data-testid="stSidebar"] p {
    color: var(--text-secondary) !important;
}

/* Sidebar Inputs & Selects */
[data-testid="stSidebar"] div[data-baseweb="input"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-card) !important;
    border-radius: var(--radius-md) !important;
}
[data-testid="stSidebar"] div[data-baseweb="input"] input {
    color: var(--text-primary) !important;
}
[data-testid="stSidebar"] div[data-baseweb="select"] > div {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-card) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
}
[data-testid="stSidebar"] div[data-baseweb="select"] * {
    color: var(--text-primary) !important;
}

/* ----------------------------------------------------
   8. ChatGPT-Style Modern Left Sidebar
   ---------------------------------------------------- */
[data-testid="stSidebar"] {
    background-color: var(--bg-sidebar) !important;
    border-right: 1px solid var(--border-subtle) !important;
}

[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
    gap: 0.15rem !important;
}

/* ChatGPT Sidebar Header */
.chatgpt-sidebar-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 4px 10px 4px;
    margin-bottom: 2px;
}
.chatgpt-sidebar-title {
    font-size: 1.35rem;
    font-weight: 800;
    color: var(--text-primary);
    letter-spacing: -0.02em;
    font-family: var(--font-sans);
    white-space: nowrap;
    padding: 8px 4px 0 4px;
    margin-bottom: 8px;
}

/* New Chat Button spacing & styling */
.st-key-nav_new_chat,
div[class*="st-key-nav_new_chat"] {
    margin-top: 8px !important;
    margin-bottom: 8px !important;
}

.st-key-nav_new_chat button,
div[class*="st-key-nav_new_chat"] button {
    background: #eef2ff !important;
    background-color: #eef2ff !important;
    border: 1.5px solid #c7d2fe !important;
    border-radius: 10px !important;
    color: #4338ca !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    padding: 8px 14px !important;
    min-height: 40px !important;
    height: 40px !important;
    box-shadow: 0 1px 2px rgba(67, 56, 202, 0.05) !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 8px !important;
    width: 100% !important;
    transition: all 150ms ease !important;
}

.st-key-nav_new_chat button:hover,
div[class*="st-key-nav_new_chat"] button:hover {
    background: #e0e7ff !important;
    background-color: #e0e7ff !important;
    border-color: #a5b4fc !important;
    color: #3730a3 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 3px 8px rgba(67, 56, 202, 0.12) !important;
}

/* Sidebar Header Action Buttons (Search & Toggle) */
.st-key-btn_search_toggle button,
.st-key-btn_toggle_sidebar button {
    background: transparent !important;
    border: none !important;
    color: var(--text-muted) !important;
    padding: 2px 4px !important;
    font-size: 15px !important;
    min-height: 30px !important;
    height: 30px !important;
    width: 30px !important;
    border-radius: 6px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-shadow: none !important;
    margin: 0 !important;
}
.st-key-btn_search_toggle button:hover,
.st-key-btn_toggle_sidebar button:hover {
    background: rgba(0, 0, 0, 0.06) !important;
    color: var(--text-primary) !important;
}
@media (prefers-color-scheme: dark) {
    .st-key-btn_search_toggle button:hover,
    .st-key-btn_toggle_sidebar button:hover {
        background: rgba(255, 255, 255, 0.08) !important;
    }
}

/* Sidebar Search Input */
.st-key-chat_search_query {
    margin-top: 4px !important;
    margin-bottom: 6px !important;
}
.st-key-chat_search_query div[data-baseweb="input"] {
    background: rgba(0, 0, 0, 0.03) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: 8px !important;
    padding: 0 6px !important;
    height: 34px !important;
    transition: all 150ms ease !important;
}
.st-key-chat_search_query div[data-baseweb="input"]:focus-within {
    border-color: var(--accent-primary) !important;
    background: var(--bg-surface) !important;
    box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.12) !important;
}
.st-key-chat_search_query input {
    font-size: 13px !important;
    color: var(--text-primary) !important;
}
@media (prefers-color-scheme: dark) {
    .st-key-chat_search_query div[data-baseweb="input"] {
        background: rgba(255, 255, 255, 0.05) !important;
        border-color: rgba(255, 255, 255, 0.08) !important;
    }
    .st-key-chat_search_query div[data-baseweb="input"]:focus-within {
        background: #1e1e1e !important;
    }
}

/* Sleek ChatGPT Borderless Nav & Recent Items */
[data-testid="stSidebar"] [data-testid="stButton"] > button,
[data-testid="stSidebar"] [data-testid="stPopover"] > button {
    background: transparent !important;
    border: none !important;
    color: var(--text-primary) !important;
    border-radius: 8px !important;
    font-size: 13.5px !important;
    font-weight: 450 !important;
    padding: 7px 10px !important;
    text-align: left !important;
    justify-content: flex-start !important;
    width: 100% !important;
    box-shadow: none !important;
    transition: background 120ms ease !important;
    margin: 1px 0 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}

[data-testid="stSidebar"] [data-testid="stButton"] > button:hover,
[data-testid="stSidebar"] [data-testid="stPopover"] > button:hover {
    background: rgba(0, 0, 0, 0.05) !important;
    color: var(--text-primary) !important;
    transform: none !important;
    box-shadow: none !important;
}

@media (prefers-color-scheme: dark) {
    [data-testid="stSidebar"] [data-testid="stButton"] > button:hover,
    [data-testid="stSidebar"] [data-testid="stPopover"] > button:hover {
        background: rgba(255, 255, 255, 0.08) !important;
    }
}

/* Recents Header */
.sidebar-recents-label {
    font-size: 11.5px;
    font-weight: 600;
    color: var(--text-muted);
    padding: 14px 10px 4px 10px;
    letter-spacing: 0.02em;
}

/* User Profile Badge */
.sidebar-user-card {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 10px 4px 10px;
    border-radius: 10px;
    margin-top: 18px;
    cursor: pointer;
    transition: background 150ms ease;
}
.sidebar-user-card:hover {
    background: rgba(0, 0, 0, 0.04);
}
@media (prefers-color-scheme: dark) {
    .sidebar-user-card:hover {
        background: rgba(255, 255, 255, 0.06);
    }
}
.sidebar-user-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: #eab308;
    color: #ffffff;
    font-weight: 600;
    font-size: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}
.sidebar-user-info {
    display: flex;
    flex-direction: column;
}
.sidebar-user-name {
    font-size: 13.5px;
    font-weight: 600;
    color: var(--text-primary);
    line-height: 1.25;
}
.sidebar-user-tier {
    font-size: 11.5px;
    color: var(--text-muted);
    line-height: 1.25;
}

/* Claim Offer Pill Button */
.st-key-btn_claim_offer > button,
[data-testid="stSidebar"] .st-key-btn_claim_offer button {
    border: 1px solid var(--border-card) !important;
    border-radius: 9999px !important;
    background: var(--bg-surface) !important;
    color: var(--text-primary) !important;
    justify-content: center !important;
    text-align: center !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 7px 16px !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
    margin-top: 6px !important;
    margin-bottom: 8px !important;
}
.st-key-btn_claim_offer > button:hover,
[data-testid="stSidebar"] .st-key-btn_claim_offer button:hover {
    background: var(--bg-card-hover) !important;
    border-color: var(--border-hover) !important;
    color: var(--text-primary) !important;
}

/* File Uploader: Dashed-border Drop Zone */
[data-testid="stFileUploader"] section {
    background: var(--bg-card) !important;
    border: 2px dashed var(--border-card) !important;
    border-radius: var(--radius-md) !important;
    padding: 16px !important;
    color: var(--text-primary) !important;
    transition: all var(--transition-fast) !important;
}

[data-testid="stFileUploader"] section:hover {
    border-color: var(--accent-primary) !important;
    background: var(--bg-card-hover) !important;
}

[data-testid="stFileUploader"] section * {
    color: var(--text-secondary) !important;
}

[data-testid="stFileUploader"] button {
    background: var(--button-bg) !important;
    border: 1px solid var(--button-border) !important;
    color: var(--button-text) !important;
    border-radius: var(--radius-sm) !important;
    font-size: 0.82rem !important;
    padding: 4px 10px !important;
}

/* Expander Content styling */
[data-testid="stSidebar"] [data-testid="stExpanderDetails"] {
    background: transparent !important;
    color: var(--text-secondary) !important;
}

/* Provider Status Cards: Full-Width, Name on One Line, Detail Below */
.sidebar-status-card {
    width: 100% !important;
    padding: 8px 12px !important;
    margin-bottom: 6px !important;
    background: var(--bg-card) !important;
    border: 1px solid var(--border-card) !important;
    border-radius: var(--radius-sm) !important;
    transition: all var(--transition-fast) !important;
}

.sidebar-status-card:hover {
    border-color: var(--border-hover) !important;
    background: var(--bg-card-hover) !important;
}

.sidebar-status-header {
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
    font-size: 0.84rem !important;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
    white-space: nowrap !important;
}

.sidebar-status-name {
    color: var(--text-primary) !important;
}

.sidebar-status-detail {
    font-size: 0.76rem !important;
    color: var(--text-muted) !important;
    margin-top: 2px !important;
    margin-left: 16px !important;
    word-break: break-word !important;
}

/* ----------------------------------------------------
   10. Animated Thinking Dots & Error Cards
   ---------------------------------------------------- */
.thinking-container {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    color: var(--text-secondary);
    font-size: 0.88rem;
}
.thinking-dots {
    display: flex;
    align-items: center;
    gap: 4px;
}
.thinking-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background-color: var(--accent-primary);
    animation: bounceDot 1.4s infinite ease-in-out both;
}
.thinking-dot:nth-child(1) { animation-delay: -0.32s; }
.thinking-dot:nth-child(2) { animation-delay: -0.16s; }
.thinking-dot:nth-child(3) { animation-delay: 0s; }

@keyframes bounceDot {
    0%, 80%, 100% { transform: scale(0.3); opacity: 0.3; }
    40% { transform: scale(1); opacity: 1; }
}

.error-card-box {
    background: rgba(239, 68, 68, 0.06);
    border: 1px solid rgba(239, 68, 68, 0.25);
    border-radius: var(--radius-md);
    padding: 14px 18px;
    color: #b91c1c;
    margin: 12px 0;
    font-size: 0.92rem;
    line-height: 1.5;
}
@media (prefers-color-scheme: dark) {
    .error-card-box {
        background: rgba(239, 68, 68, 0.12);
        color: #fca5a5;
    }
}
.error-card-title {
    font-weight: 600;
    color: #dc2626;
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
}
@media (prefers-color-scheme: dark) {
    .error-card-title {
        color: #f87171;
    }
}

/* Sidebar 3-dots Popover Button styling - Attractive Gradient Squircle Dots */
[data-testid="stSidebar"] [data-testid="stPopoverButton"],
[data-testid="stSidebar"] div.stPopover button,
[data-testid="stSidebar"] [data-testid="stPopover"] button {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 28px !important;
    height: 30px !important;
    min-width: 28px !important;
    max-width: 30px !important;
    min-height: 30px !important;
    padding: 0 !important;
    margin: 0 auto !important;
    border-radius: 8px !important;
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
    position: relative !important;
    cursor: pointer !important;
    transition: all 180ms cubic-bezier(0.4, 0, 0.2, 1) !important;
}

/* Hide Streamlit default chevron, svg, icons, and text inside sidebar popover button */
[data-testid="stSidebar"] [data-testid="stPopoverButton"] svg,
[data-testid="stSidebar"] [data-testid="stPopoverButton"] span,
[data-testid="stSidebar"] [data-testid="stPopoverButton"] p,
[data-testid="stSidebar"] [data-testid="stPopoverButton"] div,
[data-testid="stSidebar"] div.stPopover button svg,
[data-testid="stSidebar"] div.stPopover button span,
[data-testid="stSidebar"] div.stPopover button p,
[data-testid="stSidebar"] div.stPopover button div {
    display: none !important;
    visibility: hidden !important;
    width: 0 !important;
    height: 0 !important;
    opacity: 0 !important;
    font-size: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* Render the custom gradient squircle 3-dots icon via ::before */
[data-testid="stSidebar"] [data-testid="stPopoverButton"]::before,
[data-testid="stSidebar"] div.stPopover button::before {
    content: "" !important;
    display: block !important;
    width: 10px !important;
    height: 22px !important;
    background-repeat: no-repeat !important;
    background-position: center !important;
    background-size: contain !important;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 120 340' fill='none'%3E%3Cdefs%3E%3ClinearGradient id='dotGrad' x1='0%25' y1='0%25' x2='0%25' y2='100%25'%3E%3Cstop offset='0%25' stop-color='%2338BDF8'/%3E%3Cstop offset='50%25' stop-color='%233B82F6'/%3E%3Cstop offset='100%25' stop-color='%234F46E5'/%3E%3C/linearGradient%3E%3C/defs%3E%3Crect x='24' y='16' width='72' height='72' rx='24' stroke='url(%23dotGrad)' stroke-width='22'/%3E%3Crect x='24' y='134' width='72' height='72' rx='24' stroke='url(%23dotGrad)' stroke-width='22'/%3E%3Crect x='24' y='252' width='72' height='72' rx='24' stroke='url(%23dotGrad)' stroke-width='22'/%3E%3C/svg%3E") !important;
    opacity: 0.85 !important;
    transition: transform 180ms cubic-bezier(0.4, 0, 0.2, 1), filter 180ms ease, opacity 180ms ease !important;
}

/* Attractive hover state */
[data-testid="stSidebar"] [data-testid="stPopoverButton"]:hover,
[data-testid="stSidebar"] div.stPopover button:hover {
    background-color: rgba(56, 189, 248, 0.12) !important;
    border: none !important;
    box-shadow: 0 0 12px rgba(56, 189, 248, 0.35) !important;
}

[data-testid="stSidebar"] [data-testid="stPopoverButton"]:hover::before,
[data-testid="stSidebar"] div.stPopover button:hover::before {
    opacity: 1 !important;
    transform: scale(1.18) !important;
    filter: drop-shadow(0 0 4px rgba(56, 189, 248, 0.7)) !important;
}

/* Active / Expanded Popover State */
[data-testid="stSidebar"] [data-testid="stPopoverButton"][aria-expanded="true"],
[data-testid="stSidebar"] div.stPopover button[aria-expanded="true"] {
    background-color: rgba(59, 130, 246, 0.2) !important;
    border: none !important;
    box-shadow: 0 0 14px rgba(59, 130, 246, 0.45) !important;
}

[data-testid="stSidebar"] [data-testid="stPopoverButton"][aria-expanded="true"]::before,
[data-testid="stSidebar"] div.stPopover button[aria-expanded="true"]::before {
    opacity: 1 !important;
    transform: scale(1.22) !important;
    filter: drop-shadow(0 0 6px rgba(59, 130, 246, 0.85)) !important;
}

@media (prefers-color-scheme: dark) {
    [data-testid="stSidebar"] [data-testid="stPopoverButton"]:hover,
    [data-testid="stSidebar"] div.stPopover button:hover {
        background-color: rgba(59, 130, 246, 0.22) !important;
        box-shadow: 0 0 14px rgba(59, 130, 246, 0.5) !important;
    }
}

/* 3-dots Popover Menu styling */
div[data-testid="stPopoverBody"] {
    padding: 8px !important;
    min-width: 155px !important;
    border-radius: 12px !important;
    background: var(--bg-surface) !important;
    border: 1px solid var(--border-subtle) !important;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.12), 0 8px 10px -6px rgba(0, 0, 0, 0.08) !important;
}

div[data-testid="stPopoverBody"] [data-testid="stButton"] > button {
    width: 100% !important;
    text-align: left !important;
    justify-content: flex-start !important;
    padding: 8px 12px !important;
    font-size: 13.5px !important;
    font-weight: 500 !important;
    border-radius: 8px !important;
    border: none !important;
    background: transparent !important;
    color: var(--text-primary) !important;
    box-shadow: none !important;
    margin: 2px 0 !important;
    transition: background 120ms ease, color 120ms ease, transform 120ms ease !important;
}

div[data-testid="stPopoverBody"] [data-testid="stButton"] > button:hover {
    background: rgba(59, 130, 246, 0.08) !important;
    color: var(--accent-primary) !important;
    transform: translateX(2px) !important;
}

@media (prefers-color-scheme: dark) {
    div[data-testid="stPopoverBody"] [data-testid="stButton"] > button:hover {
        background: rgba(99, 102, 241, 0.15) !important;
        color: #818cf8 !important;
    }
}

/* Red hover for Delete option inside popover */
div[data-testid="stPopoverBody"] div[class*="st-key-del_opt_"] button:hover {
    color: #ef4444 !important;
    background: rgba(239, 68, 68, 0.12) !important;
    transform: translateX(2px) !important;
}



/* Share Dialog Social Platform Buttons */
div[data-testid="stDialog"] a {
    font-weight: 600 !important;
    font-size: 13px !important;
    border-radius: 9px !important;
    padding: 8px 10px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    text-decoration: none !important;
    transition: all 160ms ease !important;
}

/* WhatsApp button styling */
div[data-testid="stDialog"] div[data-testid="stHorizontalBlock"] > div:nth-child(1) a {
    background: rgba(37, 211, 102, 0.1) !important;
    color: #128c7e !important;
    border: 1px solid rgba(37, 211, 102, 0.35) !important;
}
div[data-testid="stDialog"] div[data-testid="stHorizontalBlock"] > div:nth-child(1) a:hover {
    background: rgba(37, 211, 102, 0.22) !important;
    border-color: #25d366 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(37, 211, 102, 0.25) !important;
}

/* Gmail button styling */
div[data-testid="stDialog"] div[data-testid="stHorizontalBlock"] > div:nth-child(2) a {
    background: rgba(234, 67, 53, 0.1) !important;
    color: #ea4335 !important;
    border: 1px solid rgba(234, 67, 53, 0.35) !important;
}
div[data-testid="stDialog"] div[data-testid="stHorizontalBlock"] > div:nth-child(2) a:hover {
    background: rgba(234, 67, 53, 0.22) !important;
    border-color: #ea4335 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(234, 67, 53, 0.25) !important;
}

/* Arattai button styling */
div[data-testid="stDialog"] div[data-testid="stHorizontalBlock"] > div:nth-child(3) a {
    background: rgba(14, 165, 233, 0.1) !important;
    color: #0284c7 !important;
    border: 1px solid rgba(14, 165, 233, 0.35) !important;
}
div[data-testid="stDialog"] div[data-testid="stHorizontalBlock"] > div:nth-child(3) a:hover {
    background: rgba(14, 165, 233, 0.22) !important;
    border-color: #0ea5e9 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(14, 165, 233, 0.25) !important;
}

@media (prefers-color-scheme: dark) {
    div[data-testid="stDialog"] div[data-testid="stHorizontalBlock"] > div:nth-child(1) a {
        color: #4ade80 !important;
    }
    div[data-testid="stDialog"] div[data-testid="stHorizontalBlock"] > div:nth-child(2) a {
        color: #f87171 !important;
    }
    div[data-testid="stDialog"] div[data-testid="stHorizontalBlock"] > div:nth-child(3) a {
        color: #38bdf8 !important;
    }
}

/* ====================================================
   DEFINITIVE OVERRIDES FOR CLEAN REFERENCE LOOK
   ==================================================== */
/* Sidebar Width Matching Reference Image (ONLY when open/expanded) */
section[data-testid="stSidebar"]:not([aria-expanded="false"]),
[data-testid="stSidebar"]:not([aria-expanded="false"]) {
    min-width: 275px !important;
    max-width: 285px !important;
    width: 280px !important;
    transform: none !important;
    visibility: visible !important;
    pointer-events: auto !important;
}

section[data-testid="stSidebar"]:not([aria-expanded="false"]) > div:first-child,
[data-testid="stSidebar"]:not([aria-expanded="false"]) > div:first-child {
    padding-top: 1.2rem !important;
    padding-left: 0.9rem !important;
    padding-right: 0.9rem !important;
}

/* Sidebar when collapsed: cleanly collapse to 0 width so no blank strip is visible */
section[data-testid="stSidebar"][aria-expanded="false"],
[data-testid="stSidebar"][aria-expanded="false"] {
    min-width: 0 !important;
    max-width: 0 !important;
    width: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    border: none !important;
    transform: translateX(-100%) !important;
    visibility: hidden !important;
    pointer-events: none !important;
    overflow: hidden !important;
}

section[data-testid="stSidebar"][aria-expanded="false"] > div:first-child,
[data-testid="stSidebar"][aria-expanded="false"] > div:first-child {
    padding: 0 !important;
    margin: 0 !important;
    width: 0 !important;
    min-width: 0 !important;
    visibility: hidden !important;
}

/* 1. New Chat button */
[data-testid="stSidebar"] div[class*="st-key-btn_new_chat"] button,
[data-testid="stSidebar"] div[class*="st-key-nav_new_chat"] button,
div.st-key-btn_new_chat button,
div.st-key-nav_new_chat button {
    background: #d4e7fe !important;
    background-color: #d4e7fe !important;
    border: 1.5px solid #bddbff !important;
    border-radius: 10px !important;
    color: #1e40af !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    padding: 8px 14px !important;
    min-height: 40px !important;
    height: 40px !important;
    box-shadow: none !important;
    display: flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
    gap: 8px !important;
    width: 100% !important;
    transition: all 150ms ease !important;
    margin-bottom: 8px !important;
}

[data-testid="stSidebar"] div[class*="st-key-btn_new_chat"] button:hover,
[data-testid="stSidebar"] div[class*="st-key-nav_new_chat"] button:hover,
div.st-key-btn_new_chat button:hover,
div.st-key-nav_new_chat button:hover {
    background: #c5ddfc !important;
    background-color: #c5ddfc !important;
    border-color: #93c5fd !important;
    color: #1e3a8a !important;
    transform: translateY(-1px) !important;
}

/* 2. Search Conversations Input */
[data-testid="stSidebar"] div[class*="st-key-chat_search_query"] div[data-baseweb="input"] {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 10px !important;
    padding: 0 8px !important;
    height: 38px !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02) !important;
}
[data-testid="stSidebar"] div[class*="st-key-chat_search_query"] input {
    font-size: 13.5px !important;
    color: #1e293b !important;
}
[data-testid="stSidebar"] div[class*="st-key-chat_search_query"] input::placeholder {
    color: #94a3b8 !important;
}

/* 2.5 Date Category Headings (Today, Yesterday, Previous 7 days) */
[data-testid="stSidebar"] .sidebar-date-heading {
    display: block !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    color: #64748b !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    padding: 16px 6px 6px 6px !important;
    margin: 0 !important;
    line-height: 1.3 !important;
    box-sizing: border-box !important;
    user-select: none !important;
}

[data-testid="stSidebar"] div:has(> .sidebar-date-heading),
[data-testid="stSidebar"] div:has(> div > .sidebar-date-heading),
[data-testid="stSidebar"] div[data-testid="stMarkdown"]:has(.sidebar-date-heading) {
    margin-top: 4px !important;
    margin-bottom: 2px !important;
    min-height: 32px !important;
}

/* 3. Active Sidebar Item (Exact Prompt Workflow Tools) */
[data-testid="stSidebar"] div[class*="st-key-sb_active_"] button {
    background: #eef2ff !important;
    background-color: #eef2ff !important;
    border: none !important;
    border-left: 3.5px solid #4f46e5 !important;
    border-radius: 2px 8px 8px 2px !important;
    color: #0f172a !important;
    font-weight: 700 !important;
    font-size: 13.5px !important;
    text-align: left !important;
    justify-content: flex-start !important;
    padding-left: 12px !important;
    height: 38px !important;
    min-height: 38px !important;
    box-shadow: none !important;
    width: 100% !important;
    margin: 1px 0 !important;
}
[data-testid="stSidebar"] div[class*="st-key-sb_active_"] button:hover {
    background: #e0e7ff !important;
    color: #0f172a !important;
}

/* 4. Inactive Sidebar Items & Recent Chat Items */
[data-testid="stSidebar"] div[class*="st-key-sb_inact_"] button,
[data-testid="stSidebar"] div[class*="st-key-chat_item_"] button,
div[class*="st-key-chat_item_"] button {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    color: #334155 !important;
    font-weight: 450 !important;
    font-size: 14px !important;
    text-align: left !important;
    justify-content: flex-start !important;
    border-radius: 8px !important;
    padding: 7px 10px !important;
    height: 36px !important;
    min-height: 36px !important;
    box-shadow: none !important;
    width: 100% !important;
    margin: 1px 0 !important;
    transition: background 0.12s ease, color 0.12s ease !important;
}
[data-testid="stSidebar"] div[class*="st-key-sb_inact_"] button:hover,
[data-testid="stSidebar"] div[class*="st-key-chat_item_"] button:hover,
div[class*="st-key-chat_item_"] button:hover {
    background: #f1f5f9 !important;
    color: #0f172a !important;
}

[data-testid="stSidebar"] div[class*="st-key-chat_item_active_"] button,
div[class*="st-key-chat_item_active_"] button {
    background: #eef2ff !important;
    color: #1d4ed8 !important;
    font-weight: 600 !important;
}

/* 5. 3-Dots Popover Button: Invisible unless row hovered */
[data-testid="stSidebar"] div[class*="st-key-pop_opts_"],
[data-testid="stSidebar"] div[data-testid="stColumn"]:nth-child(2) div[data-testid="stPopover"] > button,
[data-testid="stSidebar"] div[data-testid="stColumn"]:nth-child(2) button[data-testid="stPopoverButton"] {
    opacity: 0.2 !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #94a3b8 !important;
    transition: opacity 160ms ease, color 160ms ease !important;
}
[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:hover div[class*="st-key-pop_opts_"],
[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:hover div[data-testid="stColumn"]:nth-child(2) div[data-testid="stPopover"] > button,
[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:hover div[data-testid="stColumn"]:nth-child(2) button[data-testid="stPopoverButton"] {
    opacity: 1 !important;
    color: #475569 !important;
}

/* 6. Expanders: Borderless with + on right */
[data-testid="stSidebar"] [data-testid="stExpander"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    margin-bottom: 0px !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] details {
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 7px 4px !important;
    color: #334155 !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    width: 100% !important;
    cursor: pointer !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover {
    color: #0f172a !important;
    background: rgba(0, 0, 0, 0.02) !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary svg,
[data-testid="stSidebar"] [data-testid="stExpander"] summary [data-testid="stIconMaterial"] {
    display: none !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary::after {
    content: "+" !important;
    font-size: 18px !important;
    color: #64748b !important;
    font-weight: 400 !important;
    margin-left: auto !important;
    line-height: 1 !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"][open] summary::after {
    content: "−" !important;
}

/* Direct Download Link Styling */
.direct-dl-link {
    display: inline-flex !important;
    align-items: center !important;
    gap: 6px !important;
    background: #edf3ff !important;
    color: #2563eb !important;
    padding: 6px 14px !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 13.5px !important;
    text-decoration: none !important;
    border: 1px solid #bfdbfe !important;
    margin: 6px 0 !important;
    cursor: pointer !important;
    transition: background 0.15s ease, border-color 0.15s ease, transform 0.15s ease !important;
}

.direct-dl-link:hover {
    background: #dbeafe !important;
    color: #1d4ed8 !important;
    border-color: #93c5fd !important;
    transform: translateY(-1px) !important;
    text-decoration: none !important;
}

/* ====================================================
   Modern Sidebar User Profile Card & Sign Out Button
   ==================================================== */
.user-profile-badge {
    background: #FFFFFF;
    border: 1.5px solid #DCE7FA;
    border-radius: 16px;
    padding: 10px 12px;
    margin-top: 14px;
    margin-bottom: 6px;
    box-shadow: 0 4px 14px rgba(47, 128, 237, 0.06), 0 1px 3px rgba(20, 35, 59, 0.04);
    display: flex;
    align-items: center;
    gap: 10px;
    transition: all 0.2s ease;
}

.user-profile-badge:hover {
    border-color: #CBD5E1;
    box-shadow: 0 6px 18px rgba(47, 128, 237, 0.1);
}

.user-avatar-wrap {
    position: relative;
    flex-shrink: 0;
}

.user-avatar {
    width: 38px;
    height: 38px;
    border-radius: 50%;
    background: linear-gradient(135deg, #2F80ED 0%, #7C5CFF 100%);
    color: #FFFFFF;
    font-size: 13.5px;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    letter-spacing: -0.5px;
    box-shadow: 0 3px 8px rgba(47, 128, 237, 0.28);
}

.user-status-dot {
    position: absolute;
    bottom: -1px;
    right: -1px;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #10B981;
    border: 2px solid #FFFFFF;
}

.user-info-text {
    flex: 1;
    min-width: 0;
    overflow: hidden;
}

.user-name-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
}

.user-name {
    font-size: 13.5px;
    font-weight: 700;
    color: #14233B;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    line-height: 1.25;
}

.user-plan-pill {
    font-size: 9.5px;
    font-weight: 700;
    padding: 1px 6px;
    border-radius: 5px;
    background: #EEF4FE;
    color: #2F80ED;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    line-height: 1.3;
}

.user-email {
    font-size: 11.5px;
    font-weight: 500;
    color: #8A99B2;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    line-height: 1.3;
    margin-top: 1px;
}

/* Off-screen triggers for Streamlit interop (Edit Profile & Sign Out) */
div[class*="st-key-btn_edit_profile"],
div[class*="st-key-btn_signout"],
div[class*="st-key-eduvyn_hidden_logout_trigger"],
.st-key-btn_edit_profile,
.st-key-btn_signout,
.st-key-eduvyn_hidden_logout_trigger {
    position: fixed !important;
    left: -9999px !important;
    top: -9999px !important;
    width: 1px !important;
    height: 1px !important;
    opacity: 0 !important;
    pointer-events: none !important;
    overflow: hidden !important;
    z-index: -9999 !important;
}

/* Tools and Verification Badges */
.chips-container {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 6px;
    margin-bottom: 8px;
}
.badge-verified {
    display: inline-flex;
    align-items: center;
    background: #ecfdf5;
    color: #065f46;
    border: 1px solid #a7f3d0;
    padding: 3px 9px;
    border-radius: 9999px;
    font-size: 11px;
    font-weight: 600;
}
.badge-tool {
    display: inline-flex;
    align-items: center;
    background: #f1f5f9;
    color: #334155;
    border: 1px solid #cbd5e1;
    padding: 3px 9px;
    border-radius: 9999px;
    font-size: 11px;
    font-weight: 500;
}

/* ====================================================
   Spark Copy Button & Feedback Styling
   ==================================================== */
.spark-copy-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    font-family: inherit;
    font-size: 14px;
    font-weight: 500;
    line-height: 1.6;
    padding: 0.25rem 0.75rem;
    min-height: 38.4px;
    height: 38.4px;
    border-radius: 8px;
    background-color: transparent;
    color: var(--text-color, #0F172A);
    border: 1px solid rgba(49, 51, 63, 0.2);
    cursor: pointer;
    transition: all 0.15s ease-in-out;
    user-select: none;
    white-space: nowrap;
    box-sizing: border-box;
}

.spark-copy-btn:hover {
    border-color: #2F80ED;
    color: #2F80ED;
    background-color: rgba(47, 128, 237, 0.08);
}

.spark-copy-btn:active {
    transform: scale(0.97);
}

.spark-copy-btn.spark-copied {
    border-color: #10B981 !important;
    color: #059669 !important;
    background-color: rgba(16, 185, 129, 0.12) !important;
}

/* Floating copy toast */
#spark-clipboard-toast {
    position: fixed;
    bottom: 24px;
    right: 24px;
    background-color: #0F172A;
    color: #ffffff;
    padding: 10px 18px;
    border-radius: 8px;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.35);
    z-index: 9999999;
    font-size: 14px;
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 8px;
    opacity: 0;
    transform: translateY(10px);
    transition: opacity 0.25s ease, transform 0.25s ease;
    pointer-events: none;
}

</style>
"""

def get_clipboard_helper_js() -> str:
    """Returns client-side JavaScript for robust clipboard operations across HTTP and HTTPS."""
    return """
<script>
(function() {
    if (window.__sparkClipboardLoaded) return;
    window.__sparkClipboardLoaded = true;

    window.__sparkShowToast = function(msg) {
        var toast = document.getElementById('spark-clipboard-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'spark-clipboard-toast';
            document.body.appendChild(toast);
        }
        toast.innerHTML = msg;
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
        if (window._sparkToastTimer) clearTimeout(window._sparkToastTimer);
        window._sparkToastTimer = setTimeout(function() {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(10px)';
        }, 2500);
    };

    window.__sparkCopyText = function(text, btnElement) {
        if (!text) return;

        function fallbackCopy(str) {
            var ta = document.createElement('textarea');
            ta.value = str;
            ta.setAttribute('readonly', '');
            ta.style.position = 'fixed';
            ta.style.left = '-9999px';
            ta.style.top = '0';
            ta.style.opacity = '0';
            document.body.appendChild(ta);
            ta.focus();
            ta.select();
            ta.setSelectionRange(0, ta.value.length);
            var ok = false;
            try {
                ok = document.execCommand('copy');
            } catch(e) {
                console.error('execCommand copy error:', e);
            }
            document.body.removeChild(ta);
            return ok;
        }

        function onDone(ok) {
            if (btnElement) {
                var orig = btnElement.getAttribute('data-orig-label') || btnElement.innerHTML;
                if (!btnElement.getAttribute('data-orig-label')) {
                    btnElement.setAttribute('data-orig-label', orig);
                }
                btnElement.innerHTML = ok ? '✅ Copied!' : '⚠️ Failed';
                if (ok) {
                    btnElement.classList.add('spark-copied');
                    window.__sparkShowToast('📋 Response copied to clipboard!');
                }
                setTimeout(function() {
                    btnElement.innerHTML = btnElement.getAttribute('data-orig-label') || '📋 Copy';
                    btnElement.classList.remove('spark-copied');
                }, 2000);
            } else if (ok) {
                window.__sparkShowToast('📋 Response copied to clipboard!');
            }
        }

        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(text).then(function() {
                onDone(true);
            }).catch(function(err) {
                console.warn('Clipboard API rejected, falling back:', err);
                var ok = fallbackCopy(text);
                onDone(ok);
            });
        } else {
            var ok = fallbackCopy(text);
            onDone(ok);
        }
    };

    window.__sparkCopyB64 = function(btn) {
        if (!btn) return;
        var b64 = btn.getAttribute('data-content-b64');
        if (!b64) return;
        try {
            var bin = atob(b64);
            var bytes = new Uint8Array(bin.length);
            for (var i = 0; i < bin.length; i++) {
                bytes[i] = bin.charCodeAt(i);
            }
            var text = new TextDecoder('utf-8').decode(bytes);
            window.__sparkCopyText(text, btn);
        } catch(e) {
            console.error('B64 decode error, attempting fallback:', e);
            try {
                var decoded = decodeURIComponent(escape(atob(b64)));
                window.__sparkCopyText(decoded, btn);
            } catch(e2) {
                window.__sparkCopyText(atob(b64), btn);
            }
        }
    };
})();
</script>
"""

def apply_custom_styles():
    """Injects custom stylesheet into Streamlit app."""
    import streamlit as st
    css = get_custom_css()
    js = get_clipboard_helper_js()
    if hasattr(st, "html"):
        st.html(css)
        st.html(js, unsafe_allow_javascript=True)
    else:
        st.markdown(css + js, unsafe_allow_html=True)

