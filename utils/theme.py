def get_css(dark: bool = False) -> str:
    if dark:
        bg          = "#0d0e10"
        bg_sidebar  = "#111316"
        bg_card     = "#161820"
        bg_hover    = "#1a1e26"
        bg_input    = "#1a1e26"
        text        = "#eff3f4"
        text2       = "#8a9bb0"
        text3       = "#5a6880"
        border      = "#1e2430"
        border2     = "#2a3448"
        btn_primary_bg   = "#3abdaf"
        btn_primary_text = "#0d0e10"
        shadow      = "0 1px 3px rgba(0,0,0,0.4)"
    else:
        bg          = "#ffffff"
        bg_sidebar  = "#f7f7f5"
        bg_card     = "#ffffff"
        bg_hover    = "#f0f0ee"
        bg_input    = "#ffffff"
        text        = "#1a1a1a"
        text2       = "#6b7280"
        text3       = "#9ca3af"
        border      = "#e8e8e6"
        border2     = "#d1d1cf"
        btn_primary_bg   = "#1a1a1a"
        btn_primary_text = "#ffffff"
        shadow      = "0 1px 3px rgba(0,0,0,0.08)"

    accent = "#3abdaf"

    return f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Base ──────────────────────────────── */
html, body, .stApp {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    -webkit-font-smoothing: antialiased !important;
}}

.stApp {{
    background-color: {bg} !important;
    color: {text} !important;
}}

[data-testid="stAppViewContainer"] {{
    background-color: {bg} !important;
}}

[data-testid="stMainBlockContainer"] {{
    background-color: {bg} !important;
    padding: 2rem 2.5rem !important;
    max-width: 1280px !important;
}}

/* ── Sidebar ────────────────────────────── */
[data-testid="stSidebar"] {{
    background-color: {bg_sidebar} !important;
    border-right: 1px solid {border} !important;
}}

[data-testid="stSidebar"] > div:first-child {{
    padding-top: 1.25rem !important;
}}

[data-testid="stSidebar"] * {{
    color: {text} !important;
}}

[data-testid="stSidebarNav"] {{
    padding: 0 0.5rem !important;
}}

[data-testid="stSidebarNav"] a {{
    border-radius: 6px !important;
    padding: 6px 10px !important;
    font-size: 13.5px !important;
    font-weight: 500 !important;
    color: {text2} !important;
    text-decoration: none !important;
    transition: background 0.12s ease !important;
    display: flex !important;
    align-items: center !important;
    gap: 6px !important;
}}

[data-testid="stSidebarNav"] a:hover {{
    background-color: {bg_hover} !important;
    color: {text} !important;
}}

[data-testid="stSidebarNav"] a[aria-current="page"] {{
    background-color: {bg_hover} !important;
    color: {text} !important;
    font-weight: 600 !important;
}}

/* ── Sidebar form labels ─────────────────── */
[data-testid="stSidebar"] .stMarkdown p {{
    color: {text3} !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.07em !important;
    text-transform: uppercase !important;
    margin: 18px 0 4px 0 !important;
}}

/* ── Buttons ────────────────────────────── */
.stButton > button {{
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    font-size: 13.5px !important;
    border-radius: 8px !important;
    padding: 7px 14px !important;
    border: 1px solid {border2} !important;
    background-color: {bg_card} !important;
    color: {text} !important;
    transition: all 0.12s ease !important;
    letter-spacing: -0.01em !important;
    box-shadow: {shadow} !important;
    height: auto !important;
    min-height: 36px !important;
}}

.stButton > button:hover {{
    background-color: {bg_hover} !important;
    border-color: {border2} !important;
    box-shadow: none !important;
}}

.stButton > button[kind="primary"] {{
    background-color: {btn_primary_bg} !important;
    color: {btn_primary_text} !important;
    border-color: {btn_primary_bg} !important;
    font-weight: 600 !important;
    box-shadow: none !important;
}}

.stButton > button[kind="primary"]:hover {{
    opacity: 0.88 !important;
}}

.stButton > button[kind="secondary"] {{
    background-color: {bg_card} !important;
    color: {text2} !important;
    border-color: {border} !important;
}}

/* ── Text Input ──────────────────────────── */
.stTextInput > div > div > input {{
    background-color: {bg_input} !important;
    border: 1px solid {border} !important;
    border-radius: 8px !important;
    color: {text} !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13.5px !important;
    padding: 8px 12px !important;
    transition: border-color 0.15s, box-shadow 0.15s !important;
    box-shadow: none !important;
}}

.stTextInput > div > div > input:focus {{
    border-color: {accent} !important;
    box-shadow: 0 0 0 3px {accent}28 !important;
    outline: none !important;
}}

.stTextInput > div > div > input::placeholder {{
    color: {text3} !important;
}}

/* ── Slider ──────────────────────────────── */
.stSlider [data-testid="stTickBar"] {{
    color: {text3} !important;
    font-size: 11px !important;
}}

.stSlider [data-baseweb="slider"] [role="slider"] {{
    background-color: {accent} !important;
    border-color: {accent} !important;
}}

.stSlider [data-baseweb="slider"] [data-testid="stSliderThumb"] {{
    background-color: {accent} !important;
}}

/* ── Select Slider ───────────────────────── */
div[data-testid="stSelectSlider"] [role="slider"] {{
    background-color: {accent} !important;
    border-color: {accent} !important;
}}

/* ── Multiselect ──────────────────────────── */
.stMultiSelect [data-baseweb="select"] > div:first-child {{
    background-color: {bg_input} !important;
    border: 1px solid {border} !important;
    border-radius: 8px !important;
    font-size: 13.5px !important;
}}

.stMultiSelect [data-baseweb="tag"] {{
    background-color: {bg_hover} !important;
    border: 1px solid {border2} !important;
    border-radius: 5px !important;
    color: {text} !important;
    font-size: 12px !important;
}}

/* ── Metrics ──────────────────────────────── */
[data-testid="stMetric"] {{
    background-color: {bg_card} !important;
    border: 1px solid {border} !important;
    border-radius: 10px !important;
    padding: 16px 18px !important;
    box-shadow: {shadow} !important;
}}

[data-testid="stMetricLabel"] > div {{
    color: {text2} !important;
    font-size: 11.5px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}}

[data-testid="stMetricValue"] > div {{
    color: {text} !important;
    font-size: 22px !important;
    font-weight: 700 !important;
    letter-spacing: -0.03em !important;
}}

/* ── Progress bars ────────────────────────── */
.stProgress > div > div > div {{
    background-color: {bg_hover} !important;
    border-radius: 4px !important;
    height: 6px !important;
}}

.stProgress > div > div > div > div {{
    background-color: {accent} !important;
    border-radius: 4px !important;
}}

/* ── Tabs ─────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {{
    background-color: transparent !important;
    border-bottom: 1px solid {border} !important;
    gap: 0 !important;
    padding: 0 !important;
}}

.stTabs [data-baseweb="tab"] {{
    background-color: transparent !important;
    color: {text2} !important;
    font-size: 13.5px !important;
    font-weight: 500 !important;
    padding: 8px 18px !important;
    border-bottom: 2px solid transparent !important;
    margin-bottom: -1px !important;
    transition: all 0.12s !important;
}}

.stTabs [data-baseweb="tab"]:hover {{
    color: {text} !important;
    background-color: transparent !important;
}}

.stTabs [data-baseweb="tab"][aria-selected="true"] {{
    color: {text} !important;
    border-bottom: 2px solid {text} !important;
    font-weight: 600 !important;
    background-color: transparent !important;
}}

.stTabs [data-baseweb="tab-panel"] {{
    background-color: transparent !important;
    padding: 1.5rem 0 0 0 !important;
}}

/* ── Expanders ────────────────────────────── */
[data-testid="stExpander"] {{
    border: 1px solid {border} !important;
    border-radius: 10px !important;
    overflow: hidden !important;
    background-color: {bg_card} !important;
    box-shadow: {shadow} !important;
    margin-bottom: 6px !important;
}}

[data-testid="stExpander"] summary {{
    background-color: {bg_card} !important;
    color: {text} !important;
    font-weight: 500 !important;
    font-size: 13.5px !important;
    padding: 12px 16px !important;
    border-radius: 10px !important;
}}

[data-testid="stExpander"] summary:hover {{
    background-color: {bg_hover} !important;
}}

[data-testid="stExpander"] > div > div {{
    background-color: {bg_card} !important;
    border-top: 1px solid {border} !important;
    padding: 16px !important;
}}

/* ── Headings ─────────────────────────────── */
h1 {{
    color: {text} !important;
    font-size: 26px !important;
    font-weight: 700 !important;
    letter-spacing: -0.03em !important;
    line-height: 1.2 !important;
    margin-bottom: 2px !important;
}}

h2 {{
    color: {text} !important;
    font-size: 18px !important;
    font-weight: 600 !important;
    letter-spacing: -0.02em !important;
}}

h3 {{
    color: {text} !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    letter-spacing: -0.01em !important;
}}

/* ── Divider ──────────────────────────────── */
hr {{
    border: none !important;
    border-top: 1px solid {border} !important;
    margin: 20px 0 !important;
}}

/* ── Dataframe ────────────────────────────── */
.stDataFrame {{
    border: 1px solid {border} !important;
    border-radius: 10px !important;
    overflow: hidden !important;
    box-shadow: {shadow} !important;
}}

.stDataFrame [data-testid="stDataFrameResizable"] {{
    border-radius: 10px !important;
}}

/* ── Alerts ───────────────────────────────── */
[data-testid="stNotification"] {{
    border-radius: 8px !important;
    font-size: 13.5px !important;
    font-family: 'Inter', sans-serif !important;
}}

.stAlert {{
    border-radius: 8px !important;
    font-size: 13.5px !important;
}}

/* ── Caption ──────────────────────────────── */
[data-testid="stCaptionContainer"] p {{
    color: {text2} !important;
    font-size: 12.5px !important;
}}

/* ── Markdown text ────────────────────────── */
.stMarkdown p,
.stMarkdown li,
[data-testid="stMarkdownContainer"] p {{
    color: {text} !important;
    font-size: 13.5px !important;
    line-height: 1.6 !important;
}}

.stMarkdown strong, .stMarkdown b {{
    color: {text} !important;
    font-weight: 600 !important;
}}

/* ── Info / Warning / Error banners ─────────── */
div[data-testid="stAlert"] {{
    font-family: 'Inter', sans-serif !important;
}}

/* ── Hide Streamlit chrome ───────────────────── */
#MainMenu {{ visibility: hidden !important; }}
footer {{ visibility: hidden !important; }}
[data-testid="stDecoration"] {{ display: none !important; }}
[data-testid="stStatusWidget"] {{ display: none !important; }}
[data-testid="manage-app-button"] {{ display: none !important; }}

/* ── Scrollbar ────────────────────────────── */
::-webkit-scrollbar {{
    width: 6px;
    height: 6px;
}}

::-webkit-scrollbar-track {{
    background: {bg_sidebar};
}}

::-webkit-scrollbar-thumb {{
    background: {border2};
    border-radius: 3px;
}}

::-webkit-scrollbar-thumb:hover {{
    background: {text3};
}}

/* ── Select box ───────────────────────────── */
.stSelectbox [data-baseweb="select"] > div {{
    background-color: {bg_input} !important;
    border: 1px solid {border} !important;
    border-radius: 8px !important;
    color: {text} !important;
    font-size: 13.5px !important;
}}

/* ── Custom pill component ────────────────── */
.attio-pill {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 20px;
    font-size: 11.5px;
    font-weight: 600;
    letter-spacing: 0.01em;
}}

/* ── Page header ──────────────────────────── */
.page-header {{
    margin-bottom: 1.75rem;
    padding-bottom: 1.25rem;
    border-bottom: 1px solid {border};
}}

.page-header h1 {{
    font-size: 24px !important;
    font-weight: 700 !important;
    letter-spacing: -0.03em !important;
    color: {text} !important;
    margin: 0 !important;
}}

.page-header p {{
    color: {text2} !important;
    font-size: 13.5px !important;
    margin: 4px 0 0 0 !important;
}}

/* ── Stat card grid ───────────────────────── */
.stat-card {{
    background: {bg_card};
    border: 1px solid {border};
    border-radius: 10px;
    padding: 16px 18px;
    box-shadow: {shadow};
}}

.stat-card .label {{
    color: {text2};
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 6px;
}}

.stat-card .value {{
    color: {text};
    font-size: 22px;
    font-weight: 700;
    letter-spacing: -0.03em;
}}

/* ── Theme toggle button ──────────────────── */
.theme-toggle button {{
    background: none !important;
    border: 1px solid {border} !important;
    border-radius: 6px !important;
    padding: 4px 8px !important;
    font-size: 15px !important;
    min-height: 30px !important;
    box-shadow: none !important;
    color: {text2} !important;
}}

.theme-toggle button:hover {{
    background-color: {bg_hover} !important;
}}

/* ── Sidebar logo area ────────────────────── */
.sidebar-brand {{
    padding: 0 1rem 1rem 1rem;
    border-bottom: 1px solid {border};
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
}}

.sidebar-brand-name {{
    font-size: 15px;
    font-weight: 700;
    color: {text};
    letter-spacing: -0.02em;
}}
</style>"""
