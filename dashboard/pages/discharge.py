import streamlit as st


st.markdown(
    """
    <div class="dashboard-header">
        <h1>Entladeverhalten & EIS</h1>
        <p>
            Dynamische Belastung, Innenwiderstand und Impedanzanalyse
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


st.info(
    "Die Analyse des Entladeverhaltens und der "
    "EIS-Messungen wird nach der OCV-Auswertung ergänzt."
)


discharge_tab, eis_tab = st.tabs(
    [
        "Entladeverhalten",
        "EIS-Auswertung",
    ]
)


with discharge_tab:
    st.subheader("Geplanter Inhalt")

    st.markdown(
        """
        - Strom- und Spannungsverlauf
        - Lastsprünge
        - Spannungsabfall unter Last
        - Spannungserholung
        - Innenwiderstand aus ΔV / ΔI
        - Zellverhalten
        - Temperaturverhalten
        - Lernaufgaben und Quiz
        """
    )


with eis_tab:
    st.subheader("Geplanter Inhalt")

    st.markdown(
        """
        - Impedanz Z
        - Realteil und Imaginärteil
        - Nyquist-Diagramm
        - Bode-Darstellung
        - Frequenzabhängiges Verhalten
        - ACIR
        - Interpretation der Impedanzmessung
        - Quiz- und Transferaufgaben
        """
    )