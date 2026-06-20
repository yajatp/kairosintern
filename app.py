import streamlit as st
from dotenv import load_dotenv
from utils.theme import get_css

load_dotenv()

st.set_page_config(
    page_title="Kairos",
    page_icon="⏳",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

st.markdown(get_css(st.session_state.dark_mode), unsafe_allow_html=True)

with st.sidebar:
    col_brand, col_toggle = st.columns([5, 1])
    with col_brand:
        st.markdown(
            "<div class='sidebar-brand-name'>⏳ Kairos</div>",
            unsafe_allow_html=True,
        )
    with col_toggle:
        st.markdown("<div class='theme-toggle'>", unsafe_allow_html=True)
        icon = "☀️" if st.session_state.dark_mode else "🌙"
        if st.button(icon, key="theme_toggle", help="Toggle light / dark mode"):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    border_color = "#1e2430" if st.session_state.dark_mode else "#e8e8e6"
    st.markdown(
        f"<hr style='border:none;border-top:1px solid {border_color};margin:10px 0 4px 0'>",
        unsafe_allow_html=True,
    )

pg = st.navigation([
    st.Page("pages/leads.py",     title="Find Leads",  icon="⏳", default=True),
    st.Page("pages/api_usage.py", title="API Usage",   icon="📊"),
    st.Page("pages/history.py",   title="Run History", icon="🕐"),
])
pg.run()
