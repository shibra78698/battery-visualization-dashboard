import streamlit as st

from data_loader import (
    get_dashboard_status,
    get_system_description,
)


def format_temperature(value):
    if value is None:
        return "–"

    value = float(value)
    rounded = round(value)

    if abs(value - rounded) < 0.05:
        return f"{rounded:.0f} °C"

    return f"{value:.1f} °C"


status = get_dashboard_status()

system_description = (
    get_system_description()
)


st.markdown(
    f"""
    <div class="dashboard-hero">
        <h1>
            Interaktive Batterie Datenanalyse
        </h1>
        <p>
            Analyse und didaktische Aufbereitung
            realer Messdaten:
            {system_description}
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


st.header(
    "Überblick"
)

st.write(
    "Die Anwendung verbindet die Auswertung realer "
    "Batteriemessdaten mit interaktiven Visualisierungen "
    "und didaktischen Lerninhalten. Die analytischen "
    "Berechnungen erfolgen vollständig in Python. "
    "Das Dashboard verwendet anschließend die bereits "
    "berechneten und exportierten Ergebnisse."
)


st.header(
    "Messbereiche"
)


capacity_col, ocv_col, discharge_col = (
    st.columns(3)
)


with capacity_col:
    with st.container(
        border=True
    ):
        st.markdown(
            "### 🔋 Kapazitätstest"
        )

        st.write(
            "Kapazität, Energie, Wirkungsgrad, "
            "Zellspannungen und thermisches Verhalten."
        )

        if status[
            "capacity_available"
        ]:
            count = status[
                "capacity_tests"
            ]

            if count == 1:
                st.success(
                    "1 Messung verfügbar"
                )
            else:
                st.success(
                    f"{count} Messungen verfügbar"
                )

        else:
            st.info(
                "Noch keine Messung verfügbar."
            )

        st.page_link(
            "pages/capacity.py",
            label="Kapazitätstest öffnen",
            icon="➡️",
        )


with ocv_col:
    with st.container(
        border=True
    ):
        st.markdown(
            "### 📈 OCV Verhalten"
        )

        st.write(
            "Temperaturabhängige Entladung, "
            "Spannungsrelaxation, Zellverhalten "
            "und Vergleich verschiedener "
            "Temperaturbedingungen."
        )

        if status[
            "ocv_available"
        ]:
            count = status[
                "ocv_tests"
            ]

            if count == 1:
                st.success(
                    "1 Messung verfügbar"
                )
            else:
                st.success(
                    f"{count} Messungen verfügbar"
                )

            

        else:
            st.info(
                "Noch keine OCV Messung verfügbar."
            )

        st.page_link(
            "pages/ocv.py",
            label="OCV Verhalten öffnen",
            icon="➡️",
        )


with discharge_col:
    with st.container(
        border=True
    ):
        st.markdown(
            "### ⚡ Entladung und EIS"
        )

        st.write(
            "Dynamisches Entladeverhalten, "
            "Spannungsverhalten und "
            "elektrochemische Impedanzanalyse."
        )

        if status[
            "discharge_available"
        ]:
            count = status[
                "discharge_tests"
            ]

            if count == 1:
                st.success(
                    "1 Messung verfügbar"
                )
            else:
                st.success(
                    f"{count} Messungen verfügbar"
                )

        else:
            st.info(
                "Wird in einem späteren "
                "Arbeitsschritt ergänzt."
            )

        st.page_link(
            "pages/discharge.py",
            label="Entladung und EIS öffnen",
            icon="➡️",
        )


st.divider()


st.header(
    "Didaktisches Konzept"
)

st.write(
    "Die Lerninhalte sind so aufgebaut, dass neben "
    "grundlegenden Fakten auch Zusammenhänge, "
    "Auswertungsmethoden und die Übertragung des "
    "Wissens auf neue Messsituationen behandelt werden."
)


knowledge_1, knowledge_2, knowledge_3, knowledge_4 = (
    st.columns(4)
)


with knowledge_1:
    with st.container(
        border=True
    ):
        st.markdown(
            "#### Faktenwissen"
        )

        st.caption(
            "Definitionen, Formeln, Einheiten "
            "und Grundbegriffe"
        )


with knowledge_2:
    with st.container(
        border=True
    ):
        st.markdown(
            "#### Konzeptwissen"
        )

        st.caption(
            "Zusammenhänge verstehen "
            "und begründen"
        )


with knowledge_3:
    with st.container(
        border=True
    ):
        st.markdown(
            "#### Prozedurales Wissen"
        )

        st.caption(
            "Berechnungen und "
            "Auswertungsmethoden nachvollziehen"
        )


with knowledge_4:
    with st.container(
        border=True
    ):
        st.markdown(
            "#### Wissenstransfer"
        )

        st.caption(
            "Gelerntes auf neue "
            "Messsituationen übertragen"
        )


st.divider()


st.caption(
    "Die Datenanalyse erfolgt vollständig in Python. "
    "Die Ergebnisse werden über strukturierte CSV und "
    "JSON Dateien für Streamlit und die spätere "
    "Integration in DiBaLa bereitgestellt."
)

