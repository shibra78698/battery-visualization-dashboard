import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from plotly.subplots import make_subplots

from data_loader import (
    load_capacity_data,
    capacity_export_path,
)


def format_de(value, decimals=2):
    if value is None or pd.isna(value):
        return "–"

    text = f"{value:,.{decimals}f}"

    return (
        text
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def display_cell_name(name):
    if not name:
        return "–"

    if name.startswith("cell_"):
        number = name.split("_")[1]
        return f"Zelle {int(number)}"

    return name


def get_cell_columns(df):
    return sorted(
        column
        for column in df.columns
        if (
            column.startswith("cell_")
            and column.endswith("_V")
            and column[5:7].isdigit()
        )
    )


def cell_label(column):
    number = int(column.split("_")[1])
    return f"Zelle {number}"


def get_lowest_and_highest_cells(df):
    cell_columns = get_cell_columns(df)

    minimum_per_cell = df[cell_columns].min()

    lowest_cell = minimum_per_cell.idxmin()
    highest_cell = minimum_per_cell.idxmax()

    return lowest_cell, highest_cell


def electrical_plot(df):
    figure = make_subplots(
        specs=[[{"secondary_y": True}]]
    )

    time_h = df["timestamp_s"] / 3600

    figure.add_trace(
        go.Scatter(
            x=time_h,
            y=df["voltage_V"],
            name="Spannung",
            mode="lines",
            hovertemplate=(
                "Zeit: %{x:.2f} h<br>"
                "Spannung: %{y:.3f} V"
                "<extra></extra>"
            ),
        ),
        secondary_y=False,
    )

    figure.add_trace(
        go.Scatter(
            x=time_h,
            y=df["current_A"],
            name="Strom",
            mode="lines",
            hovertemplate=(
                "Zeit: %{x:.2f} h<br>"
                "Strom: %{y:.2f} A"
                "<extra></extra>"
            ),
        ),
        secondary_y=True,
    )

    figure.update_layout(
        title="Modulspannung und Strom über der Messzeit",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            y=1.08,
        ),
        margin=dict(
            l=20,
            r=20,
            t=80,
            b=20,
        ),
    )

    figure.update_xaxes(
        title_text="Messzeit [h]"
    )

    figure.update_yaxes(
        title_text="Spannung [V]",
        secondary_y=False,
    )

    figure.update_yaxes(
        title_text="Strom [A]",
        secondary_y=True,
    )

    return figure


def cell_voltage_plot(df, selected_cells):
    figure = go.Figure()

    time_h = (
        df["timestamp_s"]
        - df["timestamp_s"].min()
    ) / 3600

    for column in selected_cells:
        figure.add_trace(
            go.Scatter(
                x=time_h,
                y=df[column],
                mode="lines",
                name=cell_label(column),
                hovertemplate=(
                    "Zeit: %{x:.2f} h<br>"
                    "Spannung: %{y:.4f} V"
                    "<extra></extra>"
                ),
            )
        )

    figure.update_layout(
        title="Zellspannungen während der Hauptentladung",
        xaxis_title="Zeit seit Beginn der Entladung [h]",
        yaxis_title="Zellspannung [V]",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            y=-0.2,
        ),
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=80,
        ),
    )

    return figure


def cell_spread_plot(df):
    figure = go.Figure()

    time_h = (
        df["timestamp_s"]
        - df["timestamp_s"].min()
    ) / 3600

    if "cell_spread_mV" in df.columns:
        spread = df["cell_spread_mV"]

    elif "cell_delta_V" in df.columns:
        spread = df["cell_delta_V"] * 1000

    else:
        return figure

    figure.add_trace(
        go.Scatter(
            x=time_h,
            y=spread,
            mode="lines",
            name="Zellspannungsdifferenz",
            hovertemplate=(
                "Zeit: %{x:.2f} h<br>"
                "Differenz: %{y:.2f} mV"
                "<extra></extra>"
            ),
        )
    )

    figure.update_layout(
        title="Spannungsdifferenz zwischen den Zellen",
        xaxis_title="Zeit seit Beginn der Entladung [h]",
        yaxis_title="Zellspannungsdifferenz [mV]",
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=40,
        ),
    )

    return figure


def temperature_plot(df):
    figure = go.Figure()

    time_h = (
        df["timestamp_s"]
        - df["timestamp_s"].min()
    ) / 3600

    temperature_columns = {
        "temp_01_C": "Temperatur 1",
        "temp_02_C": "Temperatur 2",
        "temp_03_C": "Temperatur 3",
        "climate_temp_C": "Klimatemperatur",
    }

    for column, label in temperature_columns.items():
        if column not in df.columns:
            continue

        figure.add_trace(
            go.Scatter(
                x=time_h,
                y=df[column],
                mode="lines",
                name=label,
                hovertemplate=(
                    "Zeit: %{x:.2f} h<br>"
                    "Temperatur: %{y:.2f} °C"
                    "<extra></extra>"
                ),
            )
        )

    figure.update_layout(
        title="Temperaturverlauf während der Hauptentladung",
        xaxis_title="Zeit seit Beginn der Entladung [h]",
        yaxis_title="Temperatur [°C]",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            y=1.08,
        ),
        margin=dict(
            l=20,
            r=20,
            t=80,
            b=40,
        ),
    )

    return figure


def show_quiz(quiz):
    quiz_id = quiz["id"]

    with st.container(border=True):
        difficulty = quiz.get(
            "difficulty",
            ""
        ).capitalize()

        st.caption(
            f"Schwierigkeitsgrad: {difficulty}"
        )

        answer = st.radio(
            quiz["question"],
            quiz["options"],
            index=None,
            key=f"{quiz_id}_choice",
        )

        if st.button(
            "Antwort prüfen",
            key=f"{quiz_id}_button",
        ):
            if answer is None:
                st.warning(
                    "Bitte zuerst eine Antwort auswählen."
                )
            else:
                st.session_state[
                    f"{quiz_id}_submitted"
                ] = answer

        submitted = st.session_state.get(
            f"{quiz_id}_submitted"
        )

        if submitted is not None:
            correct_answer = quiz["options"][
                quiz["correct_index"]
            ]

            if submitted == correct_answer:
                st.success("Richtig.")
            else:
                st.error(
                    "Nicht ganz. Die richtige Antwort ist: "
                    f"{correct_answer}"
                )

            st.info(
                "Erklärung: "
                + quiz["explanation"]
            )


def show_reflection(question, index):
    with st.container(border=True):
        st.markdown(
            f"**{question['question']}**"
        )

        user_answer = st.text_area(
            "Eigene Überlegung",
            key=f"reflection_text_{index}",
            height=120,
            placeholder="Formuliere zuerst deine eigene Antwort...",
        )

        has_answer = bool(
            user_answer
            and user_answer.strip()
        )

        if not has_answer:
            st.caption(
                "Eine eigene Antwort ist erforderlich, bevor "
                "die mögliche Erklärung angezeigt werden kann."
            )

        show_answer = st.button(
            "Mögliche Antwort anzeigen",
            key=f"reflection_button_{index}",
            disabled=not has_answer,
        )

        if show_answer:
            st.session_state[
                f"reflection_show_{index}"
            ] = True

        if (
            has_answer
            and st.session_state.get(
                f"reflection_show_{index}",
                False,
            )
        ):
            st.markdown(
                "**Mögliche Antwort / Orientierung:**"
            )

            st.info(
                question["sample_answer"]
            )

            st.caption(
                "Vergleiche diese Erklärung mit deiner eigenen "
                "Antwort. Andere Antworten können ebenfalls "
                "sinnvoll sein, wenn sie fachlich begründet sind."
            )


def show_transfer_task(task, index):
    with st.container(border=True):
        st.markdown(
            f"**Transferaufgabe {index + 1}**"
        )

        st.write(
            task["question"]
        )

        user_answer = st.text_area(
            "Eigene Antwort",
            key=f"transfer_text_{index}",
            height=130,
            placeholder=(
                "Übertrage das Gelernte auf die neue Situation "
                "und begründe deine Antwort..."
            ),
        )

        has_answer = bool(
            user_answer
            and user_answer.strip()
        )

        if not has_answer:
            st.caption(
                "Bitte zuerst eine eigene Antwort formulieren."
            )

        show_answer = st.button(
            "Beispielantwort anzeigen",
            key=f"transfer_button_{index}",
            disabled=not has_answer,
        )

        if show_answer:
            st.session_state[
                f"transfer_show_{index}"
            ] = True

        if (
            has_answer
            and st.session_state.get(
                f"transfer_show_{index}",
                False,
            )
        ):
            st.markdown(
                "**Beispielhafte Lösung:**"
            )

            st.info(
                task["sample_answer"]
            )

            st.caption(
                "Die Beispielantwort ist keine zwingend einzige "
                "Lösung. Entscheidend ist eine fachlich "
                "nachvollziehbare Begründung."
            )


data = load_capacity_data()

summary = data["summary"]
electrical = data["electrical"]
cells = data["cells"]
temperature = data["temperature"]
events = data["events"]
learning = data["learning"]
validation = summary["validation"]


st.markdown(
    """
    <div class="dashboard-header">
        <h1>Kapazitätstest</h1>
        <p>
            Elektrische, zellbezogene und thermische Analyse
            des Batteriemoduls
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


view_mode = st.radio(
    "Ansicht",
    [
        "Lernmodus",
        "Erweiterte Analyse",
    ],
    horizontal=True,
)


st.subheader("Zentrale Ergebnisse")

k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    st.metric(
        "Entladekapazität",
        f"{format_de(summary['capacity']['discharge_Ah'], 2)} Ah",
    )

with k2:
    st.metric(
        "Entladeenergie",
        f"{format_de(summary['energy']['discharge_Wh'] / 1000, 2)} kWh",
    )

with k3:
    st.metric(
        "Energieeffizienz",
        f"{format_de(summary['energy']['efficiency_pct'], 2)} %",
    )

with k4:
    st.metric(
        "Max. Zellspannungsdifferenz",
        f"{format_de(summary['cells']['maximum_spread_mV'], 2)} mV",
    )

with k5:
    st.metric(
        "Max. Temperatur",
        f"{format_de(summary['temperature']['maximum_C'], 2)} °C",
    )


st.divider()


electrical_tab, cells_tab, temperature_tab, validation_tab = st.tabs(
    [
        "Elektrisches Verhalten",
        "Zellverhalten",
        "Thermisches Verhalten",
        "Validierung",
    ]
)


with electrical_tab:
    st.plotly_chart(
        electrical_plot(electrical),
        use_container_width=True,
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "Min. Modulspannung",
            f"{format_de(summary['electrical']['minimum_module_voltage_V'], 3)} V",
        )

    with c2:
        st.metric(
            "Mittlerer Entladestrom",
            f"{format_de(summary['electrical']['mean_discharge_current_A'], 2)} A",
        )

    with c3:
        st.metric(
            "Mittlerer Ladestrom",
            f"{format_de(summary['electrical']['mean_charge_current_A'], 2)} A",
        )


with cells_tab:
    st.subheader(
        "Zellspannungsvergleich"
    )

    cell_columns = get_cell_columns(cells)

    lowest_cell, highest_cell = (
        get_lowest_and_highest_cells(cells)
    )

    display_mode = st.radio(
        "Darstellung",
        [
            "Alle Zellen",
            "Ausgewählte Zellen",
            "Niedrigste und höchste Zelle",
        ],
        horizontal=True,
        key="cell_display_mode",
    )

    if display_mode == "Alle Zellen":
        selected_cells = cell_columns

    elif display_mode == "Ausgewählte Zellen":
        selected_labels = st.multiselect(
            "Zellen auswählen",
            options=[
                cell_label(column)
                for column in cell_columns
            ],
            default=[
                cell_label(lowest_cell)
            ],
        )

        selected_cells = [
            column
            for column in cell_columns
            if cell_label(column) in selected_labels
        ]

        if not selected_cells:
            st.info(
                "Bitte mindestens eine Zelle auswählen."
            )

    else:
        selected_cells = list(
            dict.fromkeys(
                [
                    lowest_cell,
                    highest_cell,
                ]
            )
        )

        st.caption(
            f"Verglichen werden "
            f"{cell_label(lowest_cell)} und "
            f"{cell_label(highest_cell)}."
        )

    if selected_cells:
        st.plotly_chart(
            cell_voltage_plot(
                cells,
                selected_cells,
            ),
            use_container_width=True,
        )

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "Zelle mit niedrigster Spannung",
            display_cell_name(
                summary["cells"]["weakest_cell"]
            ),
        )

    with c2:
        st.metric(
            "Niedrigste Zellspannung",
            f"{format_de(summary['cells']['weakest_cell_voltage_V'], 4)} V",
        )

    with c3:
        st.metric(
            "Max. Zellspannungsdifferenz",
            f"{format_de(summary['cells']['maximum_spread_mV'], 2)} mV",
        )

    st.plotly_chart(
        cell_spread_plot(cells),
        use_container_width=True,
    )

    with st.expander(
        "Was zeigt die Zellspannungsdifferenz?"
    ):
        st.write(
            """
            Für jeden Zeitpunkt wird die niedrigste
            Zellspannung von der höchsten Zellspannung
            abgezogen.

            Die maximale Zellspannungsdifferenz beschreibt
            damit den größten gemessenen Abstand zwischen
            den Zellen während der Hauptentladung.

            Eine niedrige Zellspannung allein erlaubt
            keine eindeutige Aussage über die Ursache.
            """
        )


with temperature_tab:
    st.plotly_chart(
        temperature_plot(temperature),
        use_container_width=True,
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "Maximale Temperatur",
            f"{format_de(summary['temperature']['maximum_C'], 2)} °C",
        )

    with c2:
        st.metric(
            "Temperaturänderung Start–Ende",
            f"{format_de(summary['temperature']['temperature_change_C'], 2)} °C",
        )

    with c3:
        st.metric(
            "Max. Temperaturdifferenz",
            f"{format_de(summary['temperature']['maximum_spread_C'], 2)} °C",
        )

    with st.expander(
        "Wie sind diese Temperaturkennwerte zu verstehen?"
    ):
        st.markdown(
            """
            **Maximale Temperatur**

            Höchster Messwert der Batterietemperatursensoren
            während der Hauptentladung.

            **Temperaturänderung Start–Ende**

            Änderung der mittleren Batterietemperatur
            zwischen Beginn und Ende der Hauptentladung.

            **Maximale Temperaturdifferenz**

            Größter gleichzeitig auftretender Unterschied
            zwischen den Batterietemperatursensoren.
            """
        )


with validation_tab:
    st.subheader(
        "Vergleich mit den Prüfstandsergebnissen"
    )

    validation_table = pd.DataFrame(
        {
            "Kennwert": [
                "Ladekapazität",
                "Ladeenergie",
                "Entladekapazität",
                "Entladeenergie",
                "Energieeffizienz",
            ],

            "Abweichung [%]": [
                validation.get(
                    "charge_capacity_difference_pct"
                ),
                validation.get(
                    "charge_energy_difference_pct"
                ),
                validation.get(
                    "discharge_capacity_difference_pct"
                ),
                validation.get(
                    "discharge_energy_difference_pct"
                ),
                validation.get(
                    "energy_efficiency_difference_pct"
                ),
            ],
        }
    )

    st.dataframe(
        validation_table,
        use_container_width=True,
        hide_index=True,
    )

    st.success(
        "Die in Python berechneten Kennwerte stimmen "
        "sehr gut mit den Prüfstandsergebnissen überein."
    )


if view_mode == "Lernmodus":

    st.divider()
    st.header("Lernbereich")

    (
        objectives_tab,
        facts_tab,
        concepts_tab,
        procedure_tab,
        quiz_tab,
        transfer_tab,
    ) = st.tabs(
        [
            "Lernziele",
            "Faktenwissen",
            "Konzeptwissen",
            "Vorgehen",
            "Quiz & Reflexion",
            "Transfer",
        ]
    )


    with objectives_tab:
        st.subheader(
            "Was soll nach dieser Seite verstanden werden?"
        )

        for objective in learning[
            "learning_objectives"
        ]:
            st.markdown(
                f"- {objective}"
            )


    with facts_tab:
        for item in learning[
            "factual_knowledge"
        ]:

            with st.container(
                border=True
            ):
                st.markdown(
                    f"### {item['title']}"
                )

                st.write(
                    item["text"]
                )

                st.markdown(
                    f"**Formel:** {item['formula']}"
                )

                st.markdown(
                    f"**Einheit:** {item['unit']}"
                )


    with concepts_tab:
        st.write(
            """
            In diesem Bereich stehen die Zusammenhänge
            zwischen den verschiedenen Messgrößen im
            Mittelpunkt.
            """
        )

        for item in learning[
            "conceptual_knowledge"
        ]:
            with st.expander(
                item["question"]
            ):
                st.write(
                    item["answer"]
                )


    with procedure_tab:
        for item in learning[
            "procedural_knowledge"
        ]:

            with st.expander(
                item["title"],
                expanded=True,
            ):
                for number, step in enumerate(
                    item["steps"],
                    start=1,
                ):
                    st.write(
                        f"{number}. {step}"
                    )

                st.markdown(
                    f"**Formel:** {item['formula']}"
                )


    with quiz_tab:
        st.subheader("Quiz")

        st.caption(
            "Nach jeder Antwort wird zusätzlich eine "
            "fachliche Erklärung angezeigt."
        )

        for quiz in learning[
            "quizzes"
        ]:
            show_quiz(
                quiz
            )

        st.divider()

        st.subheader(
            "Reflexionsfragen"
        )

        st.write(
            """
            Formuliere zunächst eine eigene Antwort.
            Erst danach kann eine mögliche Erklärung
            eingeblendet werden.
            """
        )

        for index, question in enumerate(
            learning[
                "reflection_questions"
            ]
        ):
            show_reflection(
                question,
                index,
            )


    with transfer_tab:
        st.write(
            """
            Übertrage das zuvor Gelernte auf eine neue
            Mess- oder Problemsituation.
            """
        )

        for index, task in enumerate(
            learning[
                "transfer_tasks"
            ]
        ):
            show_transfer_task(
                task,
                index,
            )

        st.divider()

        st.subheader(
            "Zentrale Erkenntnisse"
        )

        for takeaway in learning[
            "key_takeaways"
        ]:
            st.markdown(
                f"- {takeaway}"
            )


else:

    st.divider()
    st.header(
        "Erweiterte Analyse"
    )

    st.write(
        """
        Diese Ansicht dient der technischen
        Nachvollziehbarkeit der Ergebnisse.
        Sie zeigt die ausgewerteten Testereignisse,
        die verwendeten Berechnungsmethoden,
        die Validierung und die bereitgestellte
        Datenschnittstelle.
        """
    )


    st.subheader(
        "Ereignisübersicht"
    )

    st.caption(
        "Die Tabelle zeigt die getrennt ausgewerteten "
        "Lade- und Entladeereignisse."
    )

    event_table = events.copy()

    rename_columns = {
        "event_type":
            "Ereignistyp",

        "event":
            "Nr.",

        "start_s":
            "Start [s]",

        "end_s":
            "Ende [s]",

        "duration_s":
            "Dauer [s]",

        "python_capacity_Ah":
            "Kapazität [Ah]",

        "python_energy_Wh":
            "Energie [Wh]",

        "mean_current_A":
            "Mittlerer Strom [A]",

        "minimum_voltage_V":
            "Min. Spannung [V]",

        "maximum_voltage_V":
            "Max. Spannung [V]",

        "quantity_difference_div3600_pct":
            "Kapazitätsabweichung [%]",

        "energy_difference_div3600_pct":
            "Energieabweichung [%]",
    }

    event_table = event_table.rename(
        columns=rename_columns
    )

    st.dataframe(
        event_table,
        use_container_width=True,
        hide_index=True,
    )


    st.subheader(
        "Kennwerte des Hauptzyklus"
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Entladekapazität",
            f"{format_de(summary['capacity']['discharge_Ah'], 3)} Ah",
        )

    with c2:
        st.metric(
            "Hauptladekapazität",
            f"{format_de(summary['capacity']['recharge_Ah'], 3)} Ah",
        )

    with c3:
        st.metric(
            "Energieeffizienz",
            f"{format_de(summary['energy']['efficiency_pct'], 3)} %",
        )

    with c4:
        st.metric(
            "Kapazitätsbilanz Gesamtmessung",
            f"{format_de(summary['capacity']['capacity_balance_pct'], 2)} %",
        )


    st.subheader(
        "Auswertungsmethodik"
    )

    with st.container(
        border=True
    ):

        st.markdown(
            "### Kapazität"
        )

        st.write(
            "Für jedes relevante Lade- bzw. "
            "Entladeereignis wird der Strom über "
            "die Zeit integriert."
        )

        st.latex(
            r"""
            Q_{\mathrm{Ah}}
            =
            \frac{1}{3600}
            \int_{t_0}^{t_1}
            I(t)\,\mathrm{d}t
            """
        )

        st.write(
            "Der Faktor 1/3600 dient der Umrechnung "
            "von Amperesekunden (As) in "
            "Amperestunden (Ah)."
        )

        st.divider()

        st.markdown(
            "### Elektrische Leistung"
        )

        st.write(
            "Aus Modulspannung und Strom wird "
            "die momentane elektrische Leistung "
            "bestimmt."
        )

        st.latex(
            r"""
            P(t)
            =
            U(t)\cdot I(t)
            """
        )

        st.divider()

        st.markdown(
            "### Elektrische Energie"
        )

        st.write(
            "Die elektrische Energie wird durch "
            "Integration der Leistung über die "
            "Zeit bestimmt."
        )

        st.latex(
            r"""
            E_{\mathrm{Wh}}
            =
            \frac{1}{3600}
            \int_{t_0}^{t_1}
            P(t)\,\mathrm{d}t
            """
        )

        st.latex(
            r"""
            E_{\mathrm{Wh}}
            =
            \frac{1}{3600}
            \int_{t_0}^{t_1}
            U(t)I(t)\,\mathrm{d}t
            """
        )

        st.divider()

        st.markdown(
            "### Energieeffizienz"
        )

        st.write(
            "Für den betrachteten Hauptzyklus "
            "wird die abgegebene Entladeenergie "
            "mit der aufgenommenen Ladeenergie "
            "verglichen."
        )

        st.latex(
            r"""
            \eta_E
            =
            \frac{
                E_{\mathrm{Entladung}}
            }{
                E_{\mathrm{Ladung}}
            }
            \cdot 100\,\%
            """
        )

        st.divider()

        st.markdown(
            "### Ereignisbasierte Auswertung"
        )

        st.write(
            """
            Die Messdatei enthält mehrere getrennte
            Ladeereignisse. Deshalb werden Lade- und
            Entladeabschnitte zunächst einzeln
            identifiziert und ausgewertet.

            Für Kapazität, Energie und
            Energieeffizienz werden anschließend
            nur die jeweils zusammengehörenden
            Messabschnitte verwendet.
            """
        )


    st.subheader(
        "Validierung der Berechnung"
    )

    st.write(
        """
        Die aus den Messsignalen berechneten Werte
        werden mit den vom Prüfstand gespeicherten
        Referenzwerten verglichen.
        """
    )

    advanced_validation_table = pd.DataFrame(
        {
            "Kennwert": [
                "Ladekapazität",
                "Ladeenergie",
                "Entladekapazität",
                "Entladeenergie",
                "Energieeffizienz",
            ],

            "Abweichung [%]": [
                validation.get(
                    "charge_capacity_difference_pct"
                ),
                validation.get(
                    "charge_energy_difference_pct"
                ),
                validation.get(
                    "discharge_capacity_difference_pct"
                ),
                validation.get(
                    "discharge_energy_difference_pct"
                ),
                validation.get(
                    "energy_efficiency_difference_pct"
                ),
            ],
        }
    )

    st.dataframe(
        advanced_validation_table,
        use_container_width=True,
        hide_index=True,
    )


    st.subheader(
        "Technische Schnittstelle"
    )

    st.write(
        """
        Die analytischen Berechnungen werden vollständig
        im Python-Backend durchgeführt.

        Die exportierten JSON- und CSV-Dateien enthalten
        die bereits berechneten Kennwerte und die für
        Visualisierungen vorbereiteten Daten. Sie können
        sowohl von Streamlit als auch später von
        DiBaLa bzw. Unity eingelesen werden.
        """
    )

    d1, d2, d3 = st.columns(3)

    with d1:
        summary_path = capacity_export_path(
            "capacity_summary.json"
        )

        st.download_button(
            "Kennwerte herunterladen",
            data=summary_path.read_bytes(),
            file_name="capacity_summary.json",
            mime="application/json",
        )

    with d2:
        events_path = capacity_export_path(
            "events.csv"
        )

        st.download_button(
            "Ereignisdaten herunterladen",
            data=events_path.read_bytes(),
            file_name="events.csv",
            mime="text/csv",
        )

    with d3:
        learning_path = capacity_export_path(
            "learning_content.json"
        )

        st.download_button(
            "Lerninhalte herunterladen",
            data=learning_path.read_bytes(),
            file_name="learning_content.json",
            mime="application/json",
        )

    with st.expander(
        "Schnittstellenbeschreibung anzeigen"
    ):
        st.json(
            data["manifest"]
        )