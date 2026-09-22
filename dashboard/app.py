from pathlib import Path
import sys

import streamlit as st


DASHBOARD_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = DASHBOARD_DIR.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))


st.set_page_config(
    page_title="Batterie Lernplattform",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>
    .block-container {
        max-width: 1450px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    .dashboard-header {
        padding: 1.4rem 1.5rem;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(120, 140, 170, 0.22);
        border-radius: 16px;
        background: linear-gradient(
            110deg,
            rgba(224, 242, 254, 0.80),
            rgba(237, 233, 254, 0.65)
        );
    }

    .dashboard-header h1 {
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
    }

    .dashboard-header p {
        margin-top: 0.45rem;
        margin-bottom: 0;
        opacity: 0.75;
    }

    [data-testid="stMetric"] {
        padding: 1rem 1.1rem;
        border: 1px solid rgba(130, 145, 160, 0.25);
        border-radius: 14px;
        background-color: rgba(248, 250, 252, 0.78);
    }

    [data-testid="stMetricLabel"] {
        font-weight: 600;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 14px;
    }

    div.stButton > button {
        border-radius: 9px;
    }

    div[data-baseweb="tab-list"] {
        gap: 0.35rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


st.sidebar.markdown("## 🔋 Batterie Lernplattform")
st.sidebar.caption("Interaktive Analyse realer Batteriemessdaten")
st.sidebar.divider()


pages = [
    st.Page(
        "pages/overview.py",
        title="Übersicht",
        icon="🏠",
        default=True,
    ),
    st.Page(
        "pages/capacity.py",
        title="Kapazitätstest",
        icon="🔋",
    ),
    st.Page(
        "pages/ocv.py",
        title="OCV-Verhalten",
        icon="📈",
    ),
    st.Page(
        "pages/discharge.py",
        title="Entladung & EIS",
        icon="⚡",
    ),
]


navigation = st.navigation(pages)
navigation.run()