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
    "Als Naechstes geplant."
)


st.subheader("Geplanter Inhalt")

with st.container(border=True):
    st.markdown(
        """
        **Analyse**
        ...

        
        """
    )

with st.container(border=True):
    st.markdown(
        """
        **Didaktik**

        - Was ist die Leerlaufspannung?
        -... etc..
        - Quiz, Reflexionsfragen und Transferaufgaben
        """
    )


#Erkennung von Ruhephase
#Bestimmung stabiler OCV-Werte
#Vergleich der OCV-Messungen
#OCV in Abhängigkeit von SOC bzw. DoD
#Zellspannungsvergleich während der Ruhephasen
#Relaxationsverhalten    