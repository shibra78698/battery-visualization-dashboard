import streamlit as st

from data_loader import load_capacity_data


def format_de(value, decimals=2):
    if value is None:
        return "–"

    text = f"{value:,.{decimals}f}"

    return (
        text
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


data = load_capacity_data()
summary = data["summary"]


st.markdown(
    """
    <div class="dashboard-header">
        <h1>Interaktive Batterie-Datenanalyse</h1>
        <p>
            Analyse und didaktische Aufbereitung realer Messdaten
            eines 12 Zellen Batteriemoduls
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


st.subheader("Überblick")

st.write(
    """
    Die Anwendung verbindet die Auswertung realer Batteriemessdaten
    mit interaktiven Visualisierungen und didaktischen Elementen.
    Die analytischen Berechnungen werden vollständig im Python-Backend
    durchgeführt. Das Dashboard verwendet ausschließlich die bereits
    berechneten und exportierten Ergebnisse.
    """
)


c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(
        "Entladekapazität",
        f"{format_de(summary['capacity']['discharge_Ah'], 2)} Ah",
    )

with c2:
    st.metric(
        "Entladeenergie",
        f"{format_de(summary['energy']['discharge_Wh'] / 1000, 2)} kWh",
    )

with c3:
    st.metric(
        "Energieeffizienz",
        f"{format_de(summary['energy']['efficiency_pct'], 2)} %",
    )

with c4:
    st.metric(
        "Max. Zellstreuung",
        f"{format_de(summary['cells']['maximum_spread_mV'], 2)} mV",
    )


st.divider()

st.subheader("Mess- und Lernbereiche")

capacity_col, ocv_col, discharge_col = st.columns(3)

with capacity_col:
    with st.container(border=True):
        st.markdown("### 🔋 Kapazitätstest")
        st.write(
            """
            Kapazität, Energie, Wirkungsgrad, Zellspannungen
            und thermisches Verhalten.
            """
        )
        st.success("Analyse verfügbar")

with ocv_col:
    with st.container(border=True):
        st.markdown("### 📈 OCV-Verhalten")
        st.write(
            """
            Leerlaufspannung, Relaxationsverhalten und
            Zusammenhang zwischen OCV und Ladezustand.
            """
        )
        st.info("Wird im nächsten Arbeitsschritt ergänzt")

with discharge_col:
    with st.container(border=True):
        st.markdown("### ⚡ Entladung & EIS")
        st.write(
            """
            Dynamisches Entladeverhalten, Spannungsabfall,
            Innenwiderstand und Impedanzanalyse.
            """
        )
        st.info("Wird nach der OCV-Analyse ergänzt")


st.divider()

st.subheader("Didaktisches Konzept")

st.write(
    """
    Die Lerninhalte werden auf mehreren Ebenen angeboten.
    Neben grundlegenden Fakten werden Zusammenhänge erklärt,
    Berechnungsmethoden schrittweise dargestellt und Aufgaben
    zur Übertragung des Wissens auf neue Situationen angeboten.
    """
)

d1, d2, d3, d4 = st.columns(4)

with d1:
    with st.container(border=True):
        st.markdown("**Faktenwissen**")
        st.caption(
            "Definitionen, Formeln, Einheiten und grundlegende Begriffe"
        )

with d2:
    with st.container(border=True):
        st.markdown("**Konzeptwissen**")
        st.caption(
            "Zusammenhänge verstehen und Warum-Fragen beantworten"
        )

with d3:
    with st.container(border=True):
        st.markdown("**Prozedurales Wissen**")
        st.caption(
            "Berechnungen und Auswertungsmethoden nachvollziehen"
        )

with d4:
    with st.container(border=True):
        st.markdown("**Wissenstransfer**")
        st.caption(
            "Gelerntes auf neue Messsituationen übertragen"
        )


st.divider()

