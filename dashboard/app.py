from pathlib import Path
import sys

import streamlit as st


DASHBOARD_DIR = Path(__file__).resolve().parent

if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))


st.set_page_config(
    page_title="Batterie-Lernplattform",
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

    [data-testid="stMetric"] {
        background: rgba(248, 250, 252, 0.75);
        border: 1px solid rgba(130, 145, 160, 0.25);
        border-radius: 14px;
        padding: 16px 18px;
    }

    [data-testid="stMetricLabel"] {
        font-weight: 600;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 14px;
    }

    .dashboard-header {
        padding: 1.3rem 1.5rem;
        border-radius: 16px;
        background: linear-gradient(
            110deg,
            rgba(224, 242, 254, 0.75),
            rgba(237, 233, 254, 0.65)
        );
        border: 1px solid rgba(120, 140, 170, 0.22);
        margin-bottom: 1.5rem;
    }

    .dashboard-header h1 {
        margin: 0;
        font-size: 2rem;
    }

    .dashboard-header p {
        margin-top: 0.4rem;
        margin-bottom: 0;
        opacity: 0.78;
    }

    .learning-box {
        padding: 1rem 1.2rem;
        border-radius: 12px;
        border-left: 4px solid #4f7cac;
        background: rgba(239, 246, 255, 0.7);
        margin: 0.7rem 0;
    }

    .small-note {
        opacity: 0.72;
        font-size: 0.9rem;
    }

    div.stButton > button {
        border-radius: 10px;
    }

    div[data-baseweb="tab-list"] {
        gap: 0.4rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


st.sidebar.markdown("## 🔋 Batterie-Lernplattform")
st.sidebar.caption(
    "Interaktive Analyse realer Messdaten eines 12-Zellen-Batteriemoduls"
)

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