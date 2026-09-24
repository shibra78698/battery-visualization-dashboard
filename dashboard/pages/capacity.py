import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

#from dashboard.data_loader import (load_capacity_data,capacity_export_path,select_capacity_test,)
from data_loader import (load_capacity_data,capacity_export_path,select_capacity_test,)


def format_number(value, decimals=2):
    if value is None or pd.isna(value):
        return "–"

    text = f"{value:,.{decimals}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def get_system_name(number_of_cells):
    if number_of_cells == 1:
        return "Einzelzelle"

    if number_of_cells > 1:
        return f"{number_of_cells} Zellen Batteriemodul"

    return "Batteriesystem"


def get_cell_columns(df):
    return sorted(
        column
        for column in df.columns
        if re.fullmatch(r"cell_\d+_V", column)
    )


def cell_label(column):
    if not column:
        return "–"

    match = re.search(r"cell_(\d+)_V", column)

    if not match:
        return column

    return f"Zelle {int(match.group(1))}"


def get_extreme_cells(df, cell_columns):
    minimum_values = df[cell_columns].min()

    lowest_cell = minimum_values.idxmin()
    highest_cell = minimum_values.idxmax()

    return lowest_cell, highest_cell


def get_explanation(summary, group, key):
    return (
        summary
        .get("kpi_explanations", {})
        .get(group, {})
        .get(key)
    )


def electrical_plot(df):
    figure = make_subplots(
        specs=[[{"secondary_y": True}]]
    )

    time_h = df["timestamp_s"] / 3600

    figure.add_trace(
        go.Scatter(
            x=time_h,
            y=df["voltage_V"],
            mode="lines",
            name="Spannung",
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
            mode="lines",
            name="Strom",
            hovertemplate=(
                "Zeit: %{x:.2f} h<br>"
                "Strom: %{y:.2f} A"
                "<extra></extra>"
            ),
        ),
        secondary_y=True,
    )

    figure.update_layout(
        title="Spannung und Strom über der Messzeit",
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


def cell_voltage_plot(df, selected_cells, title):
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
        title=title,
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
    if "cell_spread_mV" in df.columns:
        spread = df["cell_spread_mV"]

    elif "cell_delta_V" in df.columns:
        spread = df["cell_delta_V"] * 1000

    else:
        return None

    time_h = (
        df["timestamp_s"]
        - df["timestamp_s"].min()
    ) / 3600

    figure = go.Figure()

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


def get_temperature_columns(df):
    columns = []

    for column in df.columns:
        if column == "timestamp_s":
            continue

        name = column.lower()

        if "temp" not in name and "temperature" not in name:
            continue

        derived_names = [
            "spread",
            "delta",
            "mean",
            "minimum",
            "maximum",
        ]

        if any(word in name for word in derived_names):
            continue

        columns.append(column)

    return columns


def temperature_label(column):
    name = column.lower()

    if "climate" in name or "clima" in name:
        return "Klimatemperatur"

    match = re.search(r"(\d+)", column)

    if match:
        return f"Temperatur {int(match.group(1))}"

    return column


def temperature_plot(df):
    figure = go.Figure()

    time_h = (
        df["timestamp_s"]
        - df["timestamp_s"].min()
    ) / 3600

    for column in get_temperature_columns(df):
        figure.add_trace(
            go.Scatter(
                x=time_h,
                y=df[column],
                mode="lines",
                name=temperature_label(column),
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


def show_quiz(quiz, test_id):
    quiz_id = quiz["id"]
    key_prefix = f"{test_id}_{quiz_id}"

    with st.container(border=True):
        difficulty = quiz.get("difficulty")

        if difficulty:
            st.caption(
                f"Schwierigkeitsgrad: {difficulty.capitalize()}"
            )

        answer = st.radio(
            quiz["question"],
            quiz["options"],
            index=None,
            key=f"{key_prefix}_choice",
        )

        if st.button(
            "Antwort prüfen",
            key=f"{key_prefix}_button",
        ):
            if answer is None:
                st.warning(
                    "Bitte zuerst eine Antwort auswählen."
                )
            else:
                st.session_state[
                    f"{key_prefix}_submitted"
                ] = answer

        submitted = st.session_state.get(
            f"{key_prefix}_submitted"
        )

        if submitted is None:
            return

        correct_answer = quiz["options"][
            quiz["correct_index"]
        ]

        if submitted == correct_answer:
            st.success("Richtig.")
        else:
            st.error(
                f"Nicht ganz. Die richtige Antwort ist: "
                f"{correct_answer}"
            )

        st.info(
            f"Erklärung: {quiz['explanation']}"
        )


def show_reflection(question, index, test_id):
    key_prefix = f"{test_id}_reflection_{index}"

    with st.container(border=True):
        st.markdown(
            f"**{question['question']}**"
        )

        user_answer = st.text_area(
            "Eigene Überlegung",
            key=f"{key_prefix}_text",
            height=120,
            placeholder="Formuliere zuerst deine eigene Antwort...",
        )

        has_answer = bool(
            user_answer
            and user_answer.strip()
        )

        if not has_answer:
            st.caption(
                "Eine eigene Antwort ist erforderlich, "
                "bevor die mögliche Antwort angezeigt werden kann."
            )

        if st.button(
            "Mögliche Antwort anzeigen",
            key=f"{key_prefix}_button",
            disabled=not has_answer,
        ):
            st.session_state[
                f"{key_prefix}_show"
            ] = True

        if (
            has_answer
            and st.session_state.get(
                f"{key_prefix}_show",
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
                "Vergleiche diese mögliche Antwort mit deiner "
                "eigenen Überlegung. Andere fachlich begründete "
                "Antworten können ebenfalls sinnvoll sein."
            )


def show_transfer_task(task, index, test_id):
    key_prefix = f"{test_id}_transfer_{index}"

    with st.container(border=True):
        st.markdown(
            f"**Transferaufgabe {index + 1}**"
        )

        st.write(
            task["question"]
        )

        user_answer = st.text_area(
            "Eigene Antwort",
            key=f"{key_prefix}_text",
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

        if st.button(
            "Beispielantwort anzeigen",
            key=f"{key_prefix}_button",
            disabled=not has_answer,
        ):
            st.session_state[
                f"{key_prefix}_show"
            ] = True

        if (
            has_answer
            and st.session_state.get(
                f"{key_prefix}_show",
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
                "Die Beispielantwort stellt nicht zwingend "
                "die einzige mögliche Lösung dar."
            )


def show_download_button(
    label,
    filename,
    mime_type,
    test_id,
):
    path = capacity_export_path(
        filename,
        test_id,
    )

    if not path.exists():
        st.warning(
            f"{filename} wurde nicht gefunden."
        )
        return

    st.download_button(
        label,
        data=path.read_bytes(),
        file_name=filename,
        mime=mime_type,
    )


selected_test = select_capacity_test()

data = load_capacity_data(
    selected_test
)

summary = data["summary"]
electrical = data["electrical"]
cells = data["cells"]
temperature = data["temperature"]
events = data["events"]
learning = data["learning"]
manifest = data.get("manifest", {})

cell_columns = get_cell_columns(
    cells
)

number_of_cells = (
    summary
    .get("module", {})
    .get("number_of_cells", len(cell_columns))
)

if cell_columns and number_of_cells != len(cell_columns):
    number_of_cells = len(cell_columns)

system_name = get_system_name(
    number_of_cells
)

source_file = summary.get(
    "source_file"
)


st.markdown(
    f"""
    <div class="dashboard-header">
        <h1>Kapazitätstest</h1>
        <p>
            Elektrische, zellbezogene und thermische Analyse:
            {system_name}
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

if source_file:
    st.caption(
        f"Aktuelle Messdatei: {source_file}"
    )


view_mode = st.radio(
    "Ansicht",
    [
        "Lernmodus",
        "Erweiterte Analyse",
    ],
    horizontal=True,
    key=f"{selected_test}_view_mode",
)


st.subheader(
    "Zentrale Ergebnisse"
)

discharge_capacity = summary[
    "capacity"
]["discharge_Ah"]

discharge_energy_kwh = (
    summary["energy"]["discharge_Wh"]
    / 1000
)

energy_efficiency = summary[
    "energy"
]["efficiency_pct"]

max_temperature = summary[
    "temperature"
]["maximum_C"]


k1, k2, k3, k4, k5 = st.columns(5)


with k1:
    st.metric(
        "Entladekapazität",
        f"{format_number(discharge_capacity, 2)} Ah",
    )


with k2:
    st.metric(
        "Entladeenergie",
        f"{format_number(discharge_energy_kwh, 2)} kWh",
    )


with k3:
    st.metric(
        "Energieeffizienz",
        f"{format_number(energy_efficiency, 2)} %",
    )


with k4:
    if number_of_cells > 1:
        max_cell_spread = summary[
            "cells"
        ]["maximum_spread_mV"]

        st.metric(
            "Max. Zellspannungsdifferenz",
            f"{format_number(max_cell_spread, 2)} mV",
        )

    elif number_of_cells == 1:
        min_cell_voltage = summary[
            "cells"
        ]["weakest_cell_voltage_V"]

        st.metric(
            "Minimale Zellspannung",
            f"{format_number(min_cell_voltage, 4)} V",
        )

    else:
        st.metric(
            "Zellspannungen",
            "–",
        )


with k5:
    st.metric(
        "Maximale Temperatur",
        f"{format_number(max_temperature, 2)} °C",
    )


with st.expander(
    "Was bedeuten diese Kennwerte?"
):
    explanations = [
        (
            "Entladekapazität",
            get_explanation(
                summary,
                "capacity",
                "discharge_Ah",
            ),
        ),
        (
            "Entladeenergie",
            get_explanation(
                summary,
                "energy",
                "discharge_Wh",
            ),
        ),
        (
            "Energieeffizienz",
            get_explanation(
                summary,
                "energy",
                "efficiency_pct",
            ),
        ),
    ]

    if number_of_cells > 1:
        explanations.append(
            (
                "Maximale Zellspannungsdifferenz",
                get_explanation(
                    summary,
                    "cells",
                    "maximum_spread_mV",
                ),
            )
        )

    elif number_of_cells == 1:
        explanations.append(
            (
                "Minimale Zellspannung",
                get_explanation(
                    summary,
                    "cells",
                    "weakest_cell_voltage_V",
                ),
            )
        )

    explanations.append(
        (
            "Maximale Temperatur",
            get_explanation(
                summary,
                "temperature",
                "maximum_C",
            ),
        )
    )

    for title, explanation in explanations:
        if explanation:
            st.markdown(
                f"**{title}**"
            )

            st.write(
                explanation
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

    min_voltage = summary[
        "electrical"
    ]["minimum_module_voltage_V"]

    mean_discharge_current = summary[
        "electrical"
    ]["mean_discharge_current_A"]

    mean_charge_current = summary[
        "electrical"
    ]["mean_charge_current_A"]

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "Min. Systemspannung",
            f"{format_number(min_voltage, 3)} V",
        )

    with c2:
        st.metric(
            "Mittlerer Entladestrom",
            f"{format_number(mean_discharge_current, 2)} A",
        )

    with c3:
        st.metric(
            "Mittlerer Ladestrom",
            f"{format_number(mean_charge_current, 2)} A",
        )

    with st.expander(
        "Elektrische Kennwerte verstehen"
    ):
        entries = [
            (
                "Minimale Systemspannung",
                "minimum_module_voltage_V",
            ),
            (
                "Mittlerer Entladestrom",
                "mean_discharge_current_A",
            ),
            (
                "Mittlerer Ladestrom",
                "mean_charge_current_A",
            ),
        ]

        for title, key in entries:
            explanation = get_explanation(
                summary,
                "electrical",
                key,
            )

            if explanation:
                st.markdown(
                    f"**{title}**"
                )

                st.write(
                    explanation
                )


with cells_tab:
    if not cell_columns:
        st.warning(
            "Für diese Messung stehen keine "
            "Einzelzellspannungen zur Verfügung."
        )

    elif number_of_cells == 1:
        single_cell = cell_columns[0]

        st.subheader(
            "Zellspannung"
        )

        st.plotly_chart(
            cell_voltage_plot(
                cells,
                [single_cell],
                "Zellspannung während der Hauptentladung",
            ),
            use_container_width=True,
        )

        minimum_voltage = cells[
            single_cell
        ].min()

        maximum_voltage = cells[
            single_cell
        ].max()

        c1, c2 = st.columns(2)

        with c1:
            st.metric(
                "Minimale Zellspannung",
                f"{format_number(minimum_voltage, 4)} V",
            )

        with c2:
            st.metric(
                "Maximale Zellspannung",
                f"{format_number(maximum_voltage, 4)} V",
            )

        st.info(
            "Da nur eine Einzelzelle untersucht wird, "
            "sind Kennwerte zum Vergleich mehrerer Zellen "
            "wie die Zellspannungsdifferenz oder die "
            "Zelle mit der niedrigsten Spannung nicht relevant."
        )

    else:
        st.subheader(
            "Zellspannungsvergleich"
        )

        lowest_cell, highest_cell = get_extreme_cells(
            cells,
            cell_columns,
        )

        display_mode = st.radio(
            "Darstellung",
            [
                "Alle Zellen",
                "Ausgewählte Zellen",
                "Niedrigste und höchste Zelle",
            ],
            horizontal=True,
            key=f"{selected_test}_cell_display_mode",
        )

        if display_mode == "Alle Zellen":
            selected_cells = cell_columns

        elif display_mode == "Ausgewählte Zellen":
            labels = [
                cell_label(column)
                for column in cell_columns
            ]

            selected_labels = st.multiselect(
                "Zellen auswählen",
                options=labels,
                default=[
                    cell_label(lowest_cell)
                ],
                key=f"{selected_test}_cell_selection",
            )

            selected_cells = [
                column
                for column in cell_columns
                if cell_label(column) in selected_labels
            ]

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
                "Die Auswahl basiert auf den minimalen "
                "Zellspannungen während der Hauptentladung."
            )

        if selected_cells:
            st.plotly_chart(
                cell_voltage_plot(
                    cells,
                    selected_cells,
                    "Zellspannungen während der Hauptentladung",
                ),
                use_container_width=True,
            )

        else:
            st.info(
                "Bitte mindestens eine Zelle auswählen."
            )

        weakest_cell = summary[
            "cells"
        ]["weakest_cell"]

        weakest_voltage = summary[
            "cells"
        ]["weakest_cell_voltage_V"]

        max_spread = summary[
            "cells"
        ]["maximum_spread_mV"]

        c1, c2, c3 = st.columns(3)

        with c1:
            st.metric(
                "Zelle mit niedrigster Spannung",
                cell_label(weakest_cell),
            )

        with c2:
            st.metric(
                "Niedrigste Zellspannung",
                f"{format_number(weakest_voltage, 4)} V",
            )

        with c3:
            st.metric(
                "Max. Zellspannungsdifferenz",
                f"{format_number(max_spread, 2)} mV",
            )

        spread_figure = cell_spread_plot(
            cells
        )

        if spread_figure is not None:
            st.plotly_chart(
                spread_figure,
                use_container_width=True,
            )

        with st.expander(
            "Zellkennwerte verstehen"
        ):
            entries = [
                (
                    "Zelle mit niedrigster Spannung",
                    "weakest_cell",
                ),
                (
                    "Niedrigste Zellspannung",
                    "weakest_cell_voltage_V",
                ),
                (
                    "Maximale Zellspannungsdifferenz",
                    "maximum_spread_mV",
                ),
                (
                    "Mittlere Zellspannungsdifferenz",
                    "mean_spread_mV",
                ),
            ]

            for title, key in entries:
                explanation = get_explanation(
                    summary,
                    "cells",
                    key,
                )

                if explanation:
                    st.markdown(
                        f"**{title}**"
                    )

                    st.write(
                        explanation
                    )


with temperature_tab:
    st.plotly_chart(
        temperature_plot(temperature),
        use_container_width=True,
    )

    maximum_temperature = summary[
        "temperature"
    ]["maximum_C"]

    temperature_change = summary[
        "temperature"
    ]["temperature_change_C"]

    maximum_spread = summary[
        "temperature"
    ]["maximum_spread_C"]

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "Maximale Temperatur",
            f"{format_number(maximum_temperature, 2)} °C",
        )

    with c2:
        st.metric(
            "Temperaturänderung Start–Ende",
            f"{format_number(temperature_change, 2)} °C",
        )

    with c3:
        st.metric(
            "Max. Temperaturdifferenz",
            f"{format_number(maximum_spread, 2)} °C",
        )

    with st.expander(
        "Temperaturkennwerte verstehen"
    ):
        entries = [
            (
                "Maximale Temperatur",
                "maximum_C",
            ),
            (
                "Temperaturänderung Start–Ende",
                "temperature_change_C",
            ),
            (
                "Maximale Temperaturdifferenz",
                "maximum_spread_C",
            ),
        ]

        for title, key in entries:
            explanation = get_explanation(
                summary,
                "temperature",
                key,
            )

            if explanation:
                st.markdown(
                    f"**{title}**"
                )

                st.write(
                    explanation
                )


validation = summary[
    "validation"
]


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

    validation_table[
        "Abweichung [%]"
    ] = validation_table[
        "Abweichung [%]"
    ].round(5)

    st.dataframe(
        validation_table,
        use_container_width=True,
        hide_index=True,
    )

    st.success(
        "Die in Python berechneten Kennwerte stimmen "
        "sehr gut mit den zugehörigen "
        "Prüfstandsergebnissen überein."
    )

    tester_efficiency = validation.get(
        "tester_energy_efficiency_pct"
    )

    if tester_efficiency is not None:
        st.caption(
            "Vom Prüfstand gespeicherte Energieeffizienz: "
            f"{format_number(tester_efficiency, 3)} %"
        )


if view_mode == "Lernmodus":
    st.divider()

    st.header(
        "Lernbereich"
    )

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

        for objective in learning.get(
            "learning_objectives",
            [],
        ):
            st.markdown(
                f"- {objective}"
            )


    with facts_tab:
        for item in learning.get(
            "factual_knowledge",
            [],
        ):
            with st.container(border=True):
                st.markdown(
                    f"### {item.get('title', 'Lerninhalt')}"
                )

                st.write(
                    item.get("text", "")
                )

                if item.get("formula"):
                    st.markdown(
                        "**Formel**"
                    )

                    st.latex(
                        item["formula"]
                    )

                if item.get("unit"):
                    st.markdown(
                        f"**Einheit:** {item['unit']}"
                    )


    with concepts_tab:
        st.write(
            "Hier stehen die Zusammenhänge zwischen "
            "den verschiedenen Messgrößen und "
            "Kennwerten im Mittelpunkt."
        )

        for item in learning.get(
            "conceptual_knowledge",
            [],
        ):
            question = item.get(
                "question",
                "Erklärung",
            )

            with st.expander(
                question
            ):
                st.write(
                    item.get(
                        "answer",
                        "",
                    )
                )


    with procedure_tab:
        for item in learning.get(
            "procedural_knowledge",
            [],
        ):
            with st.expander(
                item.get(
                    "title",
                    "Vorgehen",
                ),
                expanded=True,
            ):
                steps = item.get(
                    "steps",
                    [],
                )

                for number, step in enumerate(
                    steps,
                    start=1,
                ):
                    st.write(
                        f"{number}. {step}"
                    )

                if item.get("formula"):
                    st.markdown(
                        "**Formel**"
                    )

                    st.latex(
                        item["formula"]
                    )


    with quiz_tab:
        st.subheader(
            "Quiz"
        )

        st.caption(
            "Nach der Auswahl wird die Antwort geprüft "
            "und eine fachliche Erklärung angezeigt."
        )

        for quiz in learning.get(
            "quizzes",
            [],
        ):
            show_quiz(
                quiz,
                selected_test,
            )

        st.divider()

        st.subheader(
            "Reflexionsfragen"
        )

        st.write(
            "Formuliere zuerst eine eigene Antwort. "
            "Danach kannst du die hinterlegte mögliche "
            "Antwort anzeigen und mit deiner eigenen "
            "Überlegung vergleichen."
        )

        reflection_questions = learning.get(
            "reflection_questions",
            [],
        )

        for index, question in enumerate(
            reflection_questions
        ):
            show_reflection(
                question,
                index,
                selected_test,
            )


    with transfer_tab:
        st.write(
            "Bei den Transferaufgaben soll das Gelernte "
            "auf eine neue Mess- oder Problemsituation "
            "übertragen werden."
        )

        transfer_tasks = learning.get(
            "transfer_tasks",
            [],
        )

        for index, task in enumerate(
            transfer_tasks
        ):
            show_transfer_task(
                task,
                index,
                selected_test,
            )

        takeaways = learning.get(
            "key_takeaways",
            [],
        )

        if takeaways:
            st.divider()

            st.subheader(
                "Zentrale Erkenntnisse"
            )

            for takeaway in takeaways:
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
        Diese Ansicht dient der technischen Nachvollziehbarkeit
        der Ergebnisse. Sie zeigt die ausgewerteten Ereignisse,
        die verwendeten Berechnungsmethoden, die Validierung
        gegenüber dem Prüfstand und die exportierte Schnittstelle.
        """
    )


    st.subheader(
        "Ereignisübersicht"
    )

    st.caption(
        "Die Lade- und Entladeereignisse werden getrennt "
        "ausgewertet und anschließend für die Berechnung "
        "der relevanten Kennwerte verwendet."
    )

    event_table = events.copy()

    rename_map = {
        "event_type": "Ereignistyp",
        "event": "Nr.",
        "event_number": "Nr.",
        "start_s": "Start [s]",
        "end_s": "Ende [s]",
        "duration_s": "Dauer [s]",
        "active_duration_s": "Aktive Dauer [s]",
        "python_capacity_Ah": "Kapazität [Ah]",
        "python_energy_Wh": "Energie [Wh]",
        "mean_current_A": "Mittlerer Strom [A]",
        "minimum_voltage_V": "Min. Spannung [V]",
        "maximum_voltage_V": "Max. Spannung [V]",
        "quantity_difference_div3600_pct":
            "Kapazitätsabweichung [%]",
        "energy_difference_div3600_pct":
            "Energieabweichung [%]",
    }

    event_table = event_table.rename(
        columns=rename_map
    )

    st.dataframe(
        event_table,
        use_container_width=True,
        hide_index=True,
    )


    st.subheader(
        "Kennwerte des Hauptzyklus"
    )

    recharge_capacity = summary[
        "capacity"
    ]["recharge_Ah"]

    capacity_balance = summary[
        "capacity"
    ]["capacity_balance_pct"]

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Entladekapazität",
            f"{format_number(discharge_capacity, 3)} Ah",
        )

    with c2:
        st.metric(
            "Nachladekapazität",
            f"{format_number(recharge_capacity, 3)} Ah",
        )

    with c3:
        st.metric(
            "Energieeffizienz",
            f"{format_number(energy_efficiency, 3)} %",
        )

    with c4:
        st.metric(
            "Kapazitätsbilanz Gesamtmessung",
            f"{format_number(capacity_balance, 2)} %",
        )


    st.subheader(
        "Auswertungsmethodik"
    )

    with st.container(border=True):
        st.markdown(
            "### Kapazität"
        )

        st.write(
            "Für jedes relevante Lade- beziehungsweise "
            "Entladeereignis wird der Strom über die Zeit "
            "integriert."
        )

        st.latex(
            r"""
            Q_{\mathrm{Ah}}
            =
            \frac{1}{3600}
            \int_{t_0}^{t_1} I(t)\,\mathrm{d}t
            """
        )

        st.write(
            "Der Faktor 1/3600 dient der Umrechnung "
            "von Amperesekunden in Amperestunden."
        )

        st.divider()

        st.markdown(
            "### Elektrische Leistung"
        )

        st.write(
            "Aus Spannung und Strom wird die momentane "
            "elektrische Leistung bestimmt."
        )

        st.latex(
            r"""
            P(t) = U(t)\cdot I(t)
            """
        )

        st.divider()

        st.markdown(
            "### Elektrische Energie"
        )

        st.write(
            "Die elektrische Energie wird durch Integration "
            "der Leistung über die Zeit bestimmt."
        )

        st.latex(
            r"""
            E_{\mathrm{Wh}}
            =
            \frac{1}{3600}
            \int_{t_0}^{t_1} P(t)\,\mathrm{d}t
            =
            \frac{1}{3600}
            \int_{t_0}^{t_1} U(t)I(t)\,\mathrm{d}t
            """
        )

        st.divider()

        st.markdown(
            "### Energieeffizienz"
        )

        st.write(
            "Für den Hauptzyklus wird die abgegebene "
            "Entladeenergie mit der aufgenommenen "
            "Ladeenergie verglichen."
        )

        st.latex(
            r"""
            \eta_E
            =
            \frac{E_{\mathrm{Entladung}}}
                 {E_{\mathrm{Ladung}}}
            \cdot 100\,\%
            """
        )

        st.divider()

        st.markdown(
            "### Zellspannungsdifferenz"
        )

        if number_of_cells > 1:
            st.write(
                "Für jeden Zeitpunkt wird die Differenz "
                "zwischen der höchsten und der niedrigsten "
                "gemessenen Zellspannung bestimmt."
            )

            st.latex(
                r"""
                \Delta V(t)
                =
                V_{\mathrm{max}}(t)
                -
                V_{\mathrm{min}}(t)
                """
            )

        else:
            st.write(
                "Bei einer Einzelzelle ist keine "
                "Zellspannungsdifferenz zwischen mehreren "
                "Zellen definiert."
            )

        st.divider()

        st.markdown(
            "### Ereignisbasierte Auswertung"
        )

        st.write(
            "Die Messdatei kann mehrere getrennte Ladeereignisse "
            "enthalten. Deshalb werden Lade- und Entladeabschnitte "
            "zunächst einzeln identifiziert und ausgewertet. "
            "Für die Kennwerte des Hauptzyklus werden anschließend "
            "die zusammengehörenden Messabschnitte verwendet."
        )


    st.subheader(
        "Validierung der Berechnung"
    )

    st.write(
        "Die in Python berechneten Werte werden mit den "
        "vom Prüfstand gespeicherten Referenzwerten verglichen."
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

    validation_table[
        "Abweichung [%]"
    ] = validation_table[
        "Abweichung [%]"
    ].round(5)

    st.dataframe(
        validation_table,
        use_container_width=True,
        hide_index=True,
    )


    st.subheader(
        "Technische Schnittstelle"
    )

    st.write(
        """
        Die analytischen Berechnungen werden vollständig im
        Python-Backend durchgeführt. Die exportierten JSON-
        und CSV-Dateien enthalten bereits berechnete Kennwerte
        und aufbereitete Visualisierungsdaten. Dieselbe
        Schnittstelle kann später auch von DiBaLa beziehungsweise
        Unity verwendet werden.
        """
    )

    st.write(
        f"**Aktuell ausgewählter Test:** `{selected_test}`"
    )

    if source_file:
        st.write(
            f"**Quelldatei:** `{source_file}`"
        )

    d1, d2, d3 = st.columns(3)

    with d1:
        show_download_button(
            "Kennwerte herunterladen",
            "capacity_summary.json",
            "application/json",
            selected_test,
        )

    with d2:
        show_download_button(
            "Ereignisdaten herunterladen",
            "events.csv",
            "text/csv",
            selected_test,
        )

    with d3:
        show_download_button(
            "Lerninhalte herunterladen",
            "learning_content.json",
            "application/json",
            selected_test,
        )

    if manifest:
        with st.expander(
            "Schnittstellenbeschreibung anzeigen"
        ):
            st.json(
                manifest
            )