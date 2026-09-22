import streamlit as st

#from data_loader import load_capacity_data
from data_loader import (
    load_capacity_data,
    select_capacity_test,
)

def format_number(value, decimals=2):
    if value is None:
        return "–"

    text = f"{value:,.{decimals}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def get_system_name(number_of_cells):
    if number_of_cells == 1:
        return "Einzelzelle"

    if number_of_cells > 1:
        return f"{number_of_cells} Zellen Batteriemodul"

    return "Batteriesystem"


selected_test = select_capacity_test()

data = load_capacity_data(
    selected_test
)

summary = data["summary"]

number_of_cells = summary.get("module", {}).get("number_of_cells", 0)
system_name = get_system_name(number_of_cells)

discharge_capacity = summary["capacity"]["discharge_Ah"]
discharge_energy_kwh = summary["energy"]["discharge_Wh"] / 1000
energy_efficiency = summary["energy"]["efficiency_pct"]
max_temperature = summary["temperature"]["maximum_C"]


st.markdown(
    f"""
    <div class="dashboard-header">
        <h1>Interaktive Batterie Datenanalyse</h1>
        <p>
            Analyse und didaktische Aufbereitung realer Messdaten:
            {system_name}
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

source_file = summary.get(
    "source_file"
)

if source_file:
    st.caption(
        f"Aktuelle Messdatei: {source_file}"
    )
    
st.subheader("Überblick")

st.write(
    """
    Die Anwendung verbindet die Auswertung realer Batteriemessdaten
    mit interaktiven Visualisierungen und didaktischen Elementen.
    Die analytischen Berechnungen werden vollständig im Python-Backend
    durchgeführt. Das Dashboard greift auf die bereits berechneten und
    exportierten Ergebnisse zu.
    """
)


col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        "Entladekapazität",
        f"{format_number(discharge_capacity, 2)} Ah",
    )

with col2:
    st.metric(
        "Entladeenergie",
        f"{format_number(discharge_energy_kwh, 2)} kWh",
    )

with col3:
    st.metric(
        "Energieeffizienz",
        f"{format_number(energy_efficiency, 2)} %",
    )

with col4:
    if number_of_cells > 1:
        max_cell_spread = summary["cells"]["maximum_spread_mV"]

        st.metric(
            "Max. Zellspannungsdifferenz",
            f"{format_number(max_cell_spread, 2)} mV",
        )

    elif number_of_cells == 1:
        min_cell_voltage = summary["cells"]["weakest_cell_voltage_V"]

        st.metric(
            "Minimale Zellspannung",
            f"{format_number(min_cell_voltage, 4)} V",
        )

    else:
        st.metric(
            "Zellspannungen",
            "–",
        )

with col5:
    st.metric(
        "Maximale Temperatur",
        f"{format_number(max_temperature, 2)} °C",
    )


st.divider()

st.subheader("Mess- und Analysebereiche")

capacity_col, ocv_col, discharge_col = st.columns(3)


with capacity_col:
    with st.container(border=True):
        st.markdown("### 🔋 Kapazitätstest")

        st.write(
            """
            Kapazität, Energie, Wirkungsgrad, elektrisches Verhalten,
            Zellspannungen und thermisches Verhalten.
            """
        )

        st.success("Analyse verfügbar")


with ocv_col:
    with st.container(border=True):
        st.markdown("### 📈 OCV-Verhalten")

        st.write(
            """
            Leerlaufspannung, Relaxationsverhalten und Zusammenhang
            zwischen OCV und Ladezustand.
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

st.subheader("Aktuelle Messung")

with st.container(border=True):
    st.write(
        f"**Untersuchtes System:** {system_name}"
    )

    st.write(
        f"**Erkannte Zellspannungssignale:** {number_of_cells}"
    )

    st.write(
        "**Aktuell verfügbare Analyse:** Kapazitätstest"
    )


st.divider()

st.subheader("Didaktisches Konzept")

st.write(
    """
    Die Lerninhalte sind so aufgebaut, dass neben grundlegenden Fakten
    auch Zusammenhänge, Auswertungsmethoden und die Übertragung des
    Wissens auf neue Messsituationen behandelt werden.
    """
)


d1, d2, d3, d4 = st.columns(4)


with d1:
    with st.container(border=True):
        st.markdown("**Faktenwissen**")

        st.caption(
            "Definitionen, Formeln, Einheiten und Grundbegriffe"
        )


with d2:
    with st.container(border=True):
        st.markdown("**Konzeptwissen**")

        st.caption(
            "Zusammenhänge verstehen und begründen"
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

st.caption(
    "Die Datenanalyse erfolgt vollständig in Python. "
    "Die Ergebnisse werden über strukturierte CSV- und JSON-Dateien "
    "für Streamlit und die spätere Integration in DiBaLa bereitgestellt."
)

