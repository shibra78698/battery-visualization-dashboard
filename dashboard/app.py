import streamlit as st


st.set_page_config(
    page_title="Interaktive Batterie Datenanalyse",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded",
)


def apply_global_styles():
    st.markdown(
        """
        <style>

        :root {
            --uni-green: #89BA17;
            --uni-green-dark: #5E7F10;
            --uni-green-deep: #49660B;
            --uni-green-soft: #EAF3D5;
            --uni-green-very-soft: #F5F8EE;

            --ui-border: #D9DEE5;
            --ui-text: #20252B;
            --ui-muted: #68717C;
        }


        /* Main page */

        .block-container {
            padding-top: 1.25rem;
            padding-bottom: 3rem;
            max-width: 1500px;
        }


        h1 {
            font-size: 2.2rem !important;
            line-height: 1.2 !important;
        }


        h2 {
            font-size: 1.65rem !important;
        }


        h3 {
            font-size: 1.22rem !important;
        }


        p,
        li,
        label {
            line-height: 1.55;
        }


        /* Sidebar */

        section[data-testid="stSidebar"] {
            min-width: 22rem !important;
            max-width: 22rem !important;
            background: #F7F9F3;
            border-right: 1px solid #D7DDCC;
        }


        section[data-testid="stSidebar"] > div:first-child {
            width: 22rem !important;
        }


        section[data-testid="stSidebar"]
        [data-testid="stPageLink-NavLink"] {
            min-height: 54px;
            padding: 0.72rem 0.9rem;
            border-radius: 10px;
            margin-bottom: 0.28rem;
            font-size: 1.04rem;
            transition:
                background 0.15s ease,
                transform 0.15s ease;
        }


        section[data-testid="stSidebar"]
        [data-testid="stPageLink-NavLink"]:hover {
            background: #EEF4E1 !important;
        }


        section[data-testid="stSidebar"]
        [aria-current="page"] {
            background: var(--uni-green-soft) !important;
            border-left: 5px solid var(--uni-green) !important;
            font-weight: 700 !important;
        }


        section[data-testid="stSidebar"]
        [aria-current="page"] * {
            color: var(--uni-green-dark) !important;
        }


        /* Sidebar project title */

        .sidebar-brand {
            border-left: 5px solid var(--uni-green);
            background: #F1F6E6;
            border-radius: 0 10px 10px 0;

            padding:
                0.8rem
                0.9rem
                0.8rem
                0.9rem;

            margin:
                0.7rem
                0
                1rem
                0;
        }


        .sidebar-brand-title {
            font-size: 1.18rem;
            font-weight: 750;
            line-height: 1.3;
            color: var(--uni-green-deep);
        }


        .sidebar-brand-subtitle {
            margin-top: 0.35rem;
            font-size: 0.93rem;
            line-height: 1.45;
            color: #66705B;
        }


        /* Overview hero */

        .dashboard-hero {
            background:
                linear-gradient(
                    110deg,
                    #EDF6D9 0%,
                    #F6F9EF 55%,
                    #F0F6E3 100%
                );

            border: 1px solid #D5E3B9;
            border-left: 6px solid var(--uni-green);

            border-radius: 14px;

            padding:
                1.5rem
                1.65rem;

            margin-bottom: 1.25rem;
        }


        .dashboard-hero h1 {
            margin: 0;

            color: var(--uni-green-dark);

            font-size: 2.1rem !important;
            font-weight: 800;
        }


        .dashboard-hero p {
            margin:
                0.6rem
                0
                0
                0;

            color: #526039;
            font-size: 1rem;
        }


        /* KPI cards */

        [data-testid="stMetric"] {
            border: 1px solid var(--ui-border);
            border-top: 4px solid var(--uni-green);

            border-radius: 12px;

            padding:
                0.8rem
                1rem;

            background: #FFFFFF;
        }


        [data-testid="stMetricValue"] {
            font-size: 1.65rem;
        }


        /* Buttons and interactive elements */

        .stButton > button {
            min-height: 48px;
            border-radius: 10px;
        }


        div[data-testid="stTabs"] button {
            min-height: 48px;
        }


        div[data-testid="stExpander"] summary {
            min-height: 48px;
        }


        /* Existing green information note */

        .green-note {
            background: #F5F9EC;

            border-left:
                4px solid
                var(--uni-green);

            border-radius: 9px;

            padding:
                0.8rem
                1rem;

            margin:
                0.5rem
                0
                1rem
                0;
        }


        /* Compact graph learning box */

        .learn-box {
            background: #F5F9EC;

            border-left:
                4px solid
                var(--uni-green);

            border-radius: 10px;

            padding:
                0.95rem
                1rem;

            margin-top: 0.25rem;

            line-height: 1.55;
        }


        .learn-box-title {
            font-size: 0.98rem;
            font-weight: 700;

            color: var(--uni-green-deep);

            margin-bottom: 0.45rem;
        }


        .learn-box-text {
            font-size: 0.94rem;
            line-height: 1.55;
            color: #3F474F;
        }


        /* Keyboard focus */

        *:focus-visible {
            outline:
                3px solid
                var(--uni-green-dark)
                !important;

            outline-offset:
                2px !important;
        }


        </style>
        """,
        unsafe_allow_html=True,
    )


apply_global_styles()

with st.sidebar:
    st.markdown(
        '<div class="sidebar-brand">'
        '<div class="sidebar-brand-title">'
        '🔋 Batterie Lernplattform'
        '</div>'
        '<div class="sidebar-brand-subtitle">'
        'Interaktive Analyse realer Batteriemessdaten'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


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
        title="OCV Verhalten",
        icon="📈",
    ),

    st.Page(
        "pages/discharge.py",
        title="Entladung & EIS",
        icon="⚡",
    ),
]


navigation = st.navigation(
    pages,
    position="sidebar",
)


navigation.run()
