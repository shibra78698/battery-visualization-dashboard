import streamlit as st


st.markdown(
    """
    <div class="dashboard-header">
        <h1>OCV-Verhalten</h1>
        <p>
            Analyse der Leerlaufspannung und des Relaxationsverhaltens
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


st.info(
    "Die OCV-Analyse wird nach Abschluss der "
    "Kapazitätsseite implementiert."
)


st.subheader("Geplanter Inhalt")

with st.container(border=True):
    st.markdown(
        """
        **Analyse**

        - Erkennung von Ruhephasen
        - Bestimmung stabiler OCV-Werte
        - Vergleich der OCV-Messungen
        - OCV in Abhängigkeit von SOC bzw. DoD
        - Zellspannungsvergleich während der Ruhephasen
        - Relaxationsverhalten
        """
    )

with st.container(border=True):
    st.markdown(
        """
        **Didaktik**

        - Was ist die Leerlaufspannung?
        - Warum muss die Batterie für eine OCV-Messung ruhen?
        - Zusammenhang zwischen OCV und Ladezustand
        - Schrittweise Bestimmung eines OCV-Punktes
        - Quiz, Reflexionsfragen und Transferaufgaben
        """
    )