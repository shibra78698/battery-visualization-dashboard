import html
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from data_loader import (
    load_capacity_data,
    capacity_export_path,
    select_capacity_test,
)


# ============================================================
# CONSTANTS
# ============================================================

UNI_GREEN = "#6F9512"
DARK_GREY = "#59636E"

CELL_COLUMN_PATTERN = re.compile(
    r"^cell_\d+_V$"
)


# ============================================================
# BASIC HELPERS
# ============================================================

def safe_float(value):
    if value is None:
        return None

    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    if not np.isfinite(value):
        return None

    return value


def format_number(
    value,
    decimals=2,
):
    value = safe_float(
        value
    )

    if value is None:
        return "–"

    text = (
        f"{value:,.{decimals}f}"
    )

    return (
        text
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def metric_text(
    value,
    unit="",
    decimals=2,
):
    number = format_number(
        value,
        decimals,
    )

    if number == "–":
        return number

    if unit:
        return (
            f"{number} {unit}"
        )

    return number


def get_system_name(
    number_of_cells,
):
    if number_of_cells == 1:
        return "Einzelzelle"

    if number_of_cells > 1:
        return (
            f"{number_of_cells} "
            f"Zellen Batteriemodul"
        )

    return "Batteriesystem"


def get_cell_columns(
    dataframe,
):
    if dataframe is None:
        return []

    return sorted(
        column
        for column
        in dataframe.columns
        if CELL_COLUMN_PATTERN.fullmatch(
            column
        )
    )


def cell_label(
    column,
):
    if not column:
        return "–"

    match = re.search(
        r"cell_(\d+)_V",
        str(column),
    )

    if not match:
        return str(column)

    return (
        f"Zelle "
        f"{int(match.group(1))}"
    )


def get_extreme_cells(
    dataframe,
    cell_columns,
):
    if (
        dataframe is None
        or dataframe.empty
        or not cell_columns
    ):
        return None, None

    minimum_values = (
        dataframe[
            cell_columns
        ]
        .min()
    )

    lowest_cell = (
        minimum_values.idxmin()
    )

    highest_cell = (
        minimum_values.idxmax()
    )

    return (
        lowest_cell,
        highest_cell,
    )


def get_kpi_explanation(
    summary,
    group,
    key,
):
    return (
        summary
        .get(
            "kpi_explanations",
            {},
        )
        .get(
            group,
            {},
        )
        .get(
            key
        )
    )


def get_graph_explanation(
    learning,
    graph_id,
):
    if not learning:
        return None

    for item in learning.get(
        "graph_explanations",
        [],
    ):
        if (
            item.get("id")
            == graph_id
        ):
            return item

    return None


def render_graph_explanation(
    explanation,
):
    """
    Same graph explanation style as OCV and Discharge:
    one continuous flow text inside a rectangular box.
    """

    if not explanation:
        return

    text_parts = []

    for key in (
        "what",
        "focus",
        "interpretation",
    ):
        value = explanation.get(
            key
        )

        if value:
            text_parts.append(
                str(value).strip()
            )

    if not text_parts:
        return

    flow_text = " ".join(
        text_parts
    )

    safe_text = html.escape(
        flow_text
    )

    st.markdown(
        (
            '<div class="learn-box">'
            '<div class="learn-box-title">'
            'Einordnung'
            '</div>'
            '<div class="learn-box-text">'
            f'{safe_text}'
            '</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def section_selector(
    options,
    key,
):
    """
    Only one major section is rendered at a time.
    """

    segmented_control = getattr(
        st,
        "segmented_control",
        None,
    )

    if segmented_control is not None:
        selected = segmented_control(
            "Bereich",
            options=options,
            default=options[0],
            key=key,
            label_visibility="collapsed",
        )

        if selected is not None:
            return selected

    return st.radio(
        "Bereich",
        options=options,
        horizontal=True,
        key=key + "_fallback",
        label_visibility="collapsed",
    )


def read_optional_export_csv(
    filename,
    test_id,
):
    """
    Load additional analysis tables only when needed.

    This keeps the normal Capacity page lightweight.
    """

    path = capacity_export_path(
        filename,
        test_id,
    )

    if not path.exists():
        return None

    try:
        return pd.read_csv(
            path
        )

    except Exception:
        return None


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
        return

    st.download_button(
        label,
        data=path.read_bytes(),
        file_name=filename,
        mime=mime_type,
        use_container_width=True,
    )


# ============================================================
# PLOT:
# VOLTAGE + CURRENT
# ============================================================

def electrical_plot(
    dataframe,
):
    figure = make_subplots(
        specs=[
            [
                {
                    "secondary_y":
                        True
                }
            ]
        ]
    )

    time_h = (
        dataframe[
            "timestamp_s"
        ]
        /
        3600.0
    )

    if (
        "phase"
        in dataframe.columns
    ):
        phase_values = (
            dataframe[
                "phase"
            ]
            .astype(str)
            .to_numpy()
        )

    else:
        phase_values = np.array(
            ["–"] * len(dataframe)
        )

    customdata = np.column_stack(
        [
            phase_values,
        ]
    )

    figure.add_trace(
        go.Scatter(
            x=time_h,
            y=dataframe[
                "voltage_V"
            ],
            mode="lines",
            name="Spannung",
            line=dict(
                color=UNI_GREEN,
                width=2,
            ),
            customdata=customdata,
            hovertemplate=(
                "Zeit: %{x:.2f} h"
                "<br>"
                "Spannung: %{y:.3f} V"
                "<br>"
                "Phase: %{customdata[0]}"
                "<extra></extra>"
            ),
        ),
        secondary_y=False,
    )

    figure.add_trace(
        go.Scatter(
            x=time_h,
            y=dataframe[
                "current_A"
            ],
            mode="lines",
            name="Strom",
            line=dict(
                color=DARK_GREY,
                width=1.4,
            ),
            customdata=customdata,
            hovertemplate=(
                "Zeit: %{x:.2f} h"
                "<br>"
                "Strom: %{y:.2f} A"
                "<br>"
                "Phase: %{customdata[0]}"
                "<extra></extra>"
            ),
        ),
        secondary_y=True,
    )

    figure.update_xaxes(
        title_text=(
            "Messzeit [h]"
        )
    )

    figure.update_yaxes(
        title_text=(
            "Spannung [V]"
        ),
        secondary_y=False,
    )

    figure.update_yaxes(
        title_text=(
            "Strom [A]"
        ),
        secondary_y=True,
    )

    figure.update_layout(
        height=470,
        margin=dict(
            l=25,
            r=25,
            t=40,
            b=30,
        ),
        legend=dict(
            orientation="h",
            y=1.08,
        ),
        hovermode="closest",
    )

    return figure


# ============================================================
# PLOT:
# CELL VOLTAGES
# ============================================================

def cell_voltage_plot(
    dataframe,
    selected_cells,
):
    figure = go.Figure()

    time_h = (
        dataframe[
            "timestamp_s"
        ]
        -
        dataframe[
            "timestamp_s"
        ].min()
    ) / 3600.0

    for column in selected_cells:
        figure.add_trace(
            go.Scatter(
                x=time_h,
                y=dataframe[
                    column
                ],
                mode="lines",
                name=cell_label(
                    column
                ),
                hovertemplate=(
                    "Zeit: %{x:.2f} h"
                    "<br>"
                    "Spannung: %{y:.4f} V"
                    "<extra></extra>"
                ),
            )
        )

    figure.update_layout(
        height=460,
        margin=dict(
            l=25,
            r=25,
            t=40,
            b=50,
        ),
        xaxis_title=(
            "Zeit seit Beginn der "
            "Hauptentladung [h]"
        ),
        yaxis_title=(
            "Zellspannung [V]"
        ),
        legend=dict(
            orientation="h",
            y=-0.20,
        ),
        hovermode="closest",
    )

    return figure


# ============================================================
# PLOT:
# CELL SPREAD
# ============================================================

def cell_spread_plot(
    dataframe,
):
    if (
        "cell_spread_mV"
        in dataframe.columns
    ):
        spread = dataframe[
            "cell_spread_mV"
        ]

    elif (
        "cell_delta_V"
        in dataframe.columns
    ):
        spread = (
            dataframe[
                "cell_delta_V"
            ]
            *
            1000.0
        )

    else:
        return None

    time_h = (
        dataframe[
            "timestamp_s"
        ]
        -
        dataframe[
            "timestamp_s"
        ].min()
    ) / 3600.0

    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=time_h,
            y=spread,
            mode="lines",
            line=dict(
                color=UNI_GREEN,
                width=2,
            ),
            name=(
                "Zellspannungsdifferenz"
            ),
            hovertemplate=(
                "Zeit: %{x:.2f} h"
                "<br>"
                "Differenz: %{y:.2f} mV"
                "<extra></extra>"
            ),
        )
    )

    figure.update_layout(
        height=390,
        margin=dict(
            l=25,
            r=25,
            t=30,
            b=35,
        ),
        xaxis_title=(
            "Zeit seit Beginn der "
            "Hauptentladung [h]"
        ),
        yaxis_title=(
            "Zellspannungsdifferenz [mV]"
        ),
        showlegend=False,
    )

    return figure


# ============================================================
# PLOT:
# TEMPERATURE
# ============================================================

def get_temperature_columns(
    dataframe,
):
    if dataframe is None:
        return []

    columns = []

    for column in dataframe.columns:
        if column == "timestamp_s":
            continue

        name = column.lower()

        if (
            "temp"
            not in name
            and
            "temperature"
            not in name
        ):
            continue

        derived_names = [
            "spread",
            "delta",
            "mean",
            "minimum",
            "maximum",
            "start",
            "end",
        ]

        if any(
            word in name
            for word in derived_names
        ):
            continue

        columns.append(
            column
        )

    return columns


def temperature_label(
    column,
):
    name = column.lower()

    if (
        "climate"
        in name
        or
        "clima"
        in name
    ):
        return "Klimatemperatur"

    match = re.search(
        r"(\d+)",
        column,
    )

    if match:
        return (
            f"Temperatur "
            f"{int(match.group(1))}"
        )

    return column


def temperature_plot(
    dataframe,
):
    figure = go.Figure()

    time_h = (
        dataframe[
            "timestamp_s"
        ]
        -
        dataframe[
            "timestamp_s"
        ].min()
    ) / 3600.0

    for column in get_temperature_columns(
        dataframe
    ):
        figure.add_trace(
            go.Scatter(
                x=time_h,
                y=dataframe[
                    column
                ],
                mode="lines",
                name=temperature_label(
                    column
                ),
                hovertemplate=(
                    "Zeit: %{x:.2f} h"
                    "<br>"
                    "Temperatur: %{y:.2f} °C"
                    "<extra></extra>"
                ),
            )
        )

    figure.update_layout(
        height=440,
        margin=dict(
            l=25,
            r=25,
            t=40,
            b=35,
        ),
        xaxis_title=(
            "Zeit seit Beginn der "
            "Hauptentladung [h]"
        ),
        yaxis_title=(
            "Temperatur [°C]"
        ),
        legend=dict(
            orientation="h",
            y=1.08,
        ),
        hovermode="closest",
    )

    return figure


# ============================================================
# FAST LEARNING:
# QUIZ
# ============================================================

def render_quiz(
    quiz,
    test_id,
):
    quiz_id = quiz.get(
        "id",
        "quiz",
    )

    key_base = (
        f"{test_id}_{quiz_id}"
    )

    options = quiz.get(
        "options",
        [],
    )

    difficulty = quiz.get(
        "difficulty"
    )

    with st.form(
        key=key_base + "_form",
        clear_on_submit=False,
    ):
        if difficulty:
            st.caption(
                "Schwierigkeitsgrad: "
                + difficulty.capitalize()
            )

        st.markdown(
            "**"
            + quiz.get(
                "question",
                "",
            )
            + "**"
        )

        selected = st.radio(
            "Antwort",
            options=options,
            index=None,
            key=(
                key_base
                + "_answer"
            ),
            label_visibility="collapsed",
        )

        submitted = (
            st.form_submit_button(
                "Antwort prüfen"
            )
        )

    if submitted:
        if selected is None:
            st.session_state[
                key_base
                + "_result"
            ] = (
                "warning",
                (
                    "Bitte zuerst eine "
                    "Antwort auswählen."
                ),
                None,
            )

        else:
            correct_index = quiz.get(
                "correct_index"
            )

            selected_index = (
                options.index(
                    selected
                )
            )

            is_correct = (
                selected_index
                ==
                correct_index
            )

            correct_answer = None

            if (
                correct_index is not None
                and
                0
                <= correct_index
                < len(options)
            ):
                correct_answer = (
                    options[
                        correct_index
                    ]
                )

            if is_correct:
                message = (
                    "Richtig."
                )

            else:
                message = (
                    "Noch nicht ganz."
                )

                if correct_answer:
                    message += (
                        " Die richtige "
                        "Antwort ist: "
                        + str(
                            correct_answer
                        )
                    )

            st.session_state[
                key_base
                + "_result"
            ] = (
                (
                    "success"
                    if is_correct
                    else "error"
                ),
                message,
                quiz.get(
                    "explanation"
                ),
            )

    result = st.session_state.get(
        key_base
        + "_result"
    )

    if result:
        (
            kind,
            message,
            explanation,
        ) = result

        if kind == "success":
            st.success(
                message
            )

        elif kind == "error":
            st.error(
                message
            )

        else:
            st.warning(
                message
            )

        if explanation:
            st.info(
                explanation
            )


# ============================================================
# FAST LEARNING:
# REFLECTION
# ============================================================

def render_reflection(
    question,
    test_id,
):
    question_id = question.get(
        "id",
        "reflection",
    )

    key_base = (
        f"{test_id}_{question_id}"
    )

    minimum = int(
        question.get(
            "minimum_input_characters",
            0,
        )
        or 0
    )

    with st.form(
        key=key_base + "_form",
        clear_on_submit=False,
    ):
        answer = st.text_area(
            question.get(
                "question",
                "",
            ),
            key=(
                key_base
                + "_text"
            ),
            height=120,
            placeholder=(
                "Formuliere zuerst "
                "deine eigene Antwort ..."
            ),
        )

        submitted = (
            st.form_submit_button(
                "Musterantwort anzeigen"
            )
        )

    if submitted:
        if (
            len(
                answer.strip()
            )
            <
            minimum
        ):
            st.session_state[
                key_base
                + "_revealed"
            ] = False

            st.warning(
                "Bitte zuerst eine ausreichend "
                "ausführliche eigene Antwort "
                "formulieren."
            )

        else:
            st.session_state[
                key_base
                + "_revealed"
            ] = True

    if st.session_state.get(
        key_base
        + "_revealed",
        False,
    ):
        st.markdown(
            "**Mögliche Antwort**"
        )

        st.info(
            question.get(
                "sample_answer",
                "",
            )
        )

        st.caption(
            "Vergleiche diese Orientierung "
            "mit deiner eigenen Antwort. "
            "Andere fachlich begründete "
            "Antworten können ebenfalls "
            "sinnvoll sein."
        )


# ============================================================
# FAST LEARNING:
# TRANSFER
# ============================================================

def render_transfer_task(
    task,
    test_id,
):
    task_id = task.get(
        "id",
        "transfer",
    )

    key_base = (
        f"{test_id}_{task_id}"
    )

    minimum = int(
        task.get(
            "minimum_input_characters",
            0,
        )
        or 0
    )

    with st.form(
        key=key_base + "_form",
        clear_on_submit=False,
    ):
        answer = st.text_area(
            task.get(
                "question",
                "",
            ),
            key=(
                key_base
                + "_text"
            ),
            height=130,
            placeholder=(
                "Übertrage das Gelernte "
                "auf die neue Situation "
                "und begründe deine Antwort ..."
            ),
        )

        submitted = (
            st.form_submit_button(
                "Beispielantwort anzeigen"
            )
        )

    if submitted:
        if (
            len(
                answer.strip()
            )
            <
            minimum
        ):
            st.session_state[
                key_base
                + "_revealed"
            ] = False

            st.warning(
                "Bitte zuerst eine ausreichend "
                "ausführliche eigene Antwort "
                "formulieren."
            )

        else:
            st.session_state[
                key_base
                + "_revealed"
            ] = True

    if st.session_state.get(
        key_base
        + "_revealed",
        False,
    ):
        st.markdown(
            "**Beispielhafte Lösung**"
        )

        st.info(
            task.get(
                "sample_answer",
                "",
            )
        )

        st.caption(
            "Die Beispielantwort stellt "
            "nicht zwingend die einzige "
            "fachlich sinnvolle Lösung dar."
        )


# ============================================================
# SELECT CAPACITY TEST
# ============================================================

selected_test = (
    select_capacity_test()
)


if selected_test is None:
    st.title(
        "Kapazitätstest"
    )

    st.warning(
        "Es sind noch keine exportierten "
        "Kapazitätsdaten verfügbar."
    )

    st.stop()


# ============================================================
# LOAD DATA
# ============================================================

data = load_capacity_data(
    selected_test
)


summary = data[
    "summary"
]

electrical = data.get(
    "electrical"
)

cells = data.get(
    "cells"
)

temperature = data.get(
    "temperature"
)

events = data.get(
    "events"
)

learning = (
    data.get(
        "learning"
    )
    or {}
)

manifest = (
    data.get(
        "manifest"
    )
    or {}
)


cell_columns = (
    get_cell_columns(
        cells
    )
)


number_of_cells = (
    summary
    .get(
        "module",
        {},
    )
    .get(
        "number_of_cells",
        len(
            cell_columns
        ),
    )
)


try:
    number_of_cells = int(
        number_of_cells
        or 0
    )

except (
    TypeError,
    ValueError,
):
    number_of_cells = len(
        cell_columns
    )


if (
    cell_columns
    and
    number_of_cells
    !=
    len(cell_columns)
):
    number_of_cells = len(
        cell_columns
    )


system_name = (
    get_system_name(
        number_of_cells
    )
)


source_file = summary.get(
    "source_file"
)


capacity_summary = summary.get(
    "capacity",
    {},
)

energy_summary = summary.get(
    "energy",
    {},
)

electrical_summary = summary.get(
    "electrical",
    {},
)

cell_summary = summary.get(
    "cells",
    {},
)

temperature_summary = summary.get(
    "temperature",
    {},
)

validation_summary = summary.get(
    "validation",
    {},
)


# ============================================================
# HEADER
# ============================================================

st.title(
    "Kapazitätstest"
)


st.write(
    "Elektrische, zellbezogene und "
    "thermische Analyse des Kapazitätstests "
    "mit didaktischer Aufbereitung der "
    "berechneten Ergebnisse."
)


metadata_text = (
    system_name
)


if source_file:
    metadata_text += (
        " · "
        + str(
            source_file
        )
    )


st.caption(
    metadata_text
)


st.markdown(
    """
    <div class="green-note">
        Die analytischen Kennwerte werden vor dem Dashboard
        aus den vollständigen Messdaten berechnet. Die für
        die Darstellung exportierten Zeitreihen können
        reduziert sein, ohne die KPI-Berechnung zu verändern.
        Lade- und Entladeereignisse werden ereignisbasiert
        getrennt ausgewertet.
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# CENTRAL KPIs
# ============================================================

discharge_capacity = (
    capacity_summary.get(
        "discharge_Ah"
    )
)


discharge_energy_Wh = (
    energy_summary.get(
        "discharge_Wh"
    )
)


discharge_energy_kWh = None


if (
    safe_float(
        discharge_energy_Wh
    )
    is not None
):
    discharge_energy_kWh = (
        float(
            discharge_energy_Wh
        )
        /
        1000.0
    )


energy_efficiency = (
    energy_summary.get(
        "efficiency_pct"
    )
)


max_temperature = (
    temperature_summary.get(
        "maximum_C"
    )
)


k1, k2, k3, k4, k5 = (
    st.columns(5)
)


with k1:
    st.metric(
        "Entladekapazität",
        metric_text(
            discharge_capacity,
            "Ah",
            2,
        ),
    )


with k2:
    st.metric(
        "Entladeenergie",
        metric_text(
            discharge_energy_kWh,
            "kWh",
            2,
        ),
    )


with k3:
    st.metric(
        "Energieeffizienz",
        metric_text(
            energy_efficiency,
            "%",
            2,
        ),
    )


with k4:
    if number_of_cells > 1:
        st.metric(
            "Max. Zellspannungsdifferenz",
            metric_text(
                cell_summary.get(
                    "maximum_spread_mV"
                ),
                "mV",
                2,
            ),
        )

    elif number_of_cells == 1:
        st.metric(
            "Minimale Zellspannung",
            metric_text(
                cell_summary.get(
                    "weakest_cell_voltage_V"
                ),
                "V",
                4,
            ),
        )

    else:
        st.metric(
            "Zellspannungen",
            "–",
        )


with k5:
    st.metric(
        "Maximale Temperatur",
        metric_text(
            max_temperature,
            "°C",
            2,
        ),
    )


# ============================================================
# KPI EXPLANATIONS
# ============================================================

with st.expander(
    "Was bedeuten diese Kennwerte?"
):
    explanation_items = [
        (
            "Entladekapazität",

            get_kpi_explanation(
                summary,
                "capacity",
                "discharge_Ah",
            ),
        ),

        (
            "Entladeenergie",

            get_kpi_explanation(
                summary,
                "energy",
                "discharge_Wh",
            ),
        ),

        (
            "Energieeffizienz",

            get_kpi_explanation(
                summary,
                "energy",
                "efficiency_pct",
            ),
        ),
    ]


    if number_of_cells > 1:
        explanation_items.append(
            (
                "Maximale "
                "Zellspannungsdifferenz",

                get_kpi_explanation(
                    summary,
                    "cells",
                    "maximum_spread_mV",
                ),
            )
        )


    elif number_of_cells == 1:
        explanation_items.append(
            (
                "Minimale Zellspannung",

                get_kpi_explanation(
                    summary,
                    "cells",
                    "weakest_cell_voltage_V",
                ),
            )
        )


    explanation_items.append(
        (
            "Maximale Temperatur",

            get_kpi_explanation(
                summary,
                "temperature",
                "maximum_C",
            ),
        )
    )


    for (
        title,
        explanation,
    ) in explanation_items:

        if not explanation:
            continue

        st.markdown(
            "**"
            + title
            + "**"
        )

        st.write(
            explanation
        )


st.divider()


# ============================================================
# MAIN NAVIGATION
# ============================================================

section = section_selector(
    [
        "Versuchsverlauf",
        "Zellen",
        "Temperatur",
        "Lernen",
        "Analyse",
    ],

    key=(
        selected_test
        + "_capacity_main_section"
    ),
)


st.divider()


# ============================================================
# SECTION:
# VERSUCHSVERLAUF
# ============================================================

if section == "Versuchsverlauf":

    st.subheader(
        "Elektrischer Versuchsverlauf"
    )


    e1, e2, e3 = (
        st.columns(3)
    )


    with e1:
        st.metric(
            "Min. Systemspannung",

            metric_text(
                electrical_summary.get(
                    "minimum_module_voltage_V"
                ),
                "V",
                3,
            ),
        )


    with e2:
        st.metric(
            "Mittlerer Entladestrom",

            metric_text(
                electrical_summary.get(
                    "mean_discharge_current_A"
                ),
                "A",
                2,
            ),
        )


    with e3:
        st.metric(
            "Mittlerer Ladestrom",

            metric_text(
                electrical_summary.get(
                    "mean_charge_current_A"
                ),
                "A",
                2,
            ),
        )


    if (
        electrical is None
        or
        electrical.empty
    ):
        st.warning(
            "Keine elektrischen "
            "Visualisierungsdaten verfügbar."
        )


    else:
        graph_col, info_col = (
            st.columns(
                [
                    4,
                    1.3,
                ]
            )
        )


        with graph_col:
            st.plotly_chart(
                electrical_plot(
                    electrical
                ),
                use_container_width=True,
            )


        with info_col:
            render_graph_explanation(
                get_graph_explanation(
                    learning,
                    "voltage_current_time",
                )
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


        for (
            title,
            key,
        ) in entries:

            explanation = (
                get_kpi_explanation(
                    summary,
                    "electrical",
                    key,
                )
            )


            if explanation:
                st.markdown(
                    "**"
                    + title
                    + "**"
                )

                st.write(
                    explanation
                )


# ============================================================
# SECTION:
# ZELLEN
# ============================================================

elif section == "Zellen":

    st.subheader(
        "Zellverhalten"
    )


    if (
        cells is None
        or
        cells.empty
        or
        not cell_columns
    ):
        st.info(
            "Für diese Messung stehen keine "
            "Einzelzellspannungen zur Verfügung."
        )


    elif number_of_cells == 1:

        single_cell = (
            cell_columns[0]
        )


        c1, c2 = (
            st.columns(2)
        )


        with c1:
            st.metric(
                "Minimale Zellspannung",

                metric_text(
                    cells[
                        single_cell
                    ].min(),
                    "V",
                    4,
                ),
            )


        with c2:
            st.metric(
                "Maximale Zellspannung",

                metric_text(
                    cells[
                        single_cell
                    ].max(),
                    "V",
                    4,
                ),
            )


        graph_col, info_col = (
            st.columns(
                [
                    4,
                    1.3,
                ]
            )
        )


        with graph_col:
            st.plotly_chart(
                cell_voltage_plot(
                    cells,
                    [
                        single_cell
                    ],
                ),
                use_container_width=True,
            )


        with info_col:
            render_graph_explanation(
                get_graph_explanation(
                    learning,
                    "cell_voltages",
                )
            )


        st.info(
            "Bei einer Einzelzelle sind "
            "Mehrzellenkennwerte wie die "
            "Zellspannungsdifferenz nicht definiert."
        )


    else:

        lowest_cell, highest_cell = (
            get_extreme_cells(
                cells,
                cell_columns,
            )
        )


        display_mode = (
            section_selector(
                [
                    "Alle Zellen",
                    "Ausgewählte Zellen",
                    "Extremzellen",
                ],

                key=(
                    selected_test
                    + "_cell_display_mode"
                ),
            )
        )


        if (
            display_mode
            ==
            "Alle Zellen"
        ):
            selected_cells = (
                cell_columns
            )


        elif (
            display_mode
            ==
            "Ausgewählte Zellen"
        ):

            labels = {
                cell_label(
                    column
                ):
                    column

                for column
                in cell_columns
            }


            default_label = (
                cell_label(
                    lowest_cell
                )
                if lowest_cell
                else None
            )


            selected_labels = (
                st.multiselect(
                    "Zellen auswählen",

                    options=list(
                        labels.keys()
                    ),

                    default=(
                        [
                            default_label
                        ]
                        if default_label
                        else []
                    ),

                    key=(
                        selected_test
                        + "_cell_selection"
                    ),
                )
            )


            selected_cells = [
                labels[
                    label
                ]

                for label
                in selected_labels
            ]


        else:

            selected_cells = list(
                dict.fromkeys(
                    cell

                    for cell
                    in (
                        lowest_cell,
                        highest_cell,
                    )

                    if cell
                )
            )


            st.caption(
                "Die Auswahl basiert auf den "
                "minimalen Zellspannungen während "
                "der Hauptentladung."
            )


        if selected_cells:

            graph_col, info_col = (
                st.columns(
                    [
                        4,
                        1.3,
                    ]
                )
            )


            with graph_col:
                st.plotly_chart(
                    cell_voltage_plot(
                        cells,
                        selected_cells,
                    ),
                    use_container_width=True,
                )


            with info_col:
                render_graph_explanation(
                    get_graph_explanation(
                        learning,
                        "cell_voltages",
                    )
                )


        else:
            st.info(
                "Bitte mindestens eine "
                "Zelle auswählen."
            )


        c1, c2, c3 = (
            st.columns(3)
        )


        with c1:
            st.metric(
                "Zelle mit niedrigster Spannung",

                cell_label(
                    cell_summary.get(
                        "weakest_cell"
                    )
                ),
            )


        with c2:
            st.metric(
                "Niedrigste Zellspannung",

                metric_text(
                    cell_summary.get(
                        "weakest_cell_voltage_V"
                    ),
                    "V",
                    4,
                ),
            )


        with c3:
            st.metric(
                "Max. Zellspannungsdifferenz",

                metric_text(
                    cell_summary.get(
                        "maximum_spread_mV"
                    ),
                    "mV",
                    2,
                ),
            )


        spread_figure = (
            cell_spread_plot(
                cells
            )
        )


        if (
            spread_figure
            is not None
        ):

            st.markdown(
                "### Zellspannungsdifferenz"
            )


            graph_col, info_col = (
                st.columns(
                    [
                        4,
                        1.3,
                    ]
                )
            )


            with graph_col:
                st.plotly_chart(
                    spread_figure,
                    use_container_width=True,
                )


            with info_col:
                render_graph_explanation(
                    get_graph_explanation(
                        learning,
                        "cell_spread",
                    )
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
                    "Maximale "
                    "Zellspannungsdifferenz",
                    "maximum_spread_mV",
                ),

                (
                    "Mittlere "
                    "Zellspannungsdifferenz",
                    "mean_spread_mV",
                ),
            ]


            for (
                title,
                key,
            ) in entries:

                explanation = (
                    get_kpi_explanation(
                        summary,
                        "cells",
                        key,
                    )
                )


                if explanation:
                    st.markdown(
                        "**"
                        + title
                        + "**"
                    )

                    st.write(
                        explanation
                    )


# ============================================================
# SECTION:
# TEMPERATUR
# ============================================================

elif section == "Temperatur":

    st.subheader(
        "Thermisches Verhalten"
    )


    t1, t2, t3 = (
        st.columns(3)
    )


    with t1:
        st.metric(
            "Maximale Temperatur",

            metric_text(
                temperature_summary.get(
                    "maximum_C"
                ),
                "°C",
                2,
            ),
        )


    with t2:
        st.metric(
            "Temperaturänderung Start–Ende",

            metric_text(
                temperature_summary.get(
                    "temperature_change_C"
                ),
                "°C",
                2,
            ),
        )


    with t3:
        st.metric(
            "Max. Temperaturdifferenz",

            metric_text(
                temperature_summary.get(
                    "maximum_spread_C"
                ),
                "°C",
                2,
            ),
        )


    if (
        temperature is None
        or
        temperature.empty
    ):
        st.warning(
            "Keine Temperaturdaten verfügbar."
        )


    else:
        graph_col, info_col = (
            st.columns(
                [
                    4,
                    1.3,
                ]
            )
        )


        with graph_col:
            st.plotly_chart(
                temperature_plot(
                    temperature
                ),
                use_container_width=True,
            )


        with info_col:
            render_graph_explanation(
                get_graph_explanation(
                    learning,
                    "temperature_progress",
                )
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


        for (
            title,
            key,
        ) in entries:

            explanation = (
                get_kpi_explanation(
                    summary,
                    "temperature",
                    key,
                )
            )


            if explanation:
                st.markdown(
                    "**"
                    + title
                    + "**"
                )

                st.write(
                    explanation
                )


# ============================================================
# SECTION:
# LERNEN
# ============================================================

elif section == "Lernen":

    st.subheader(
        "Lernmodus"
    )


    objectives = (
        learning.get(
            "learning_objectives",
            [],
        )
    )


    if objectives:

        st.markdown(
            "### Lernziele"
        )


        for objective in objectives:
            st.write(
                "• "
                + str(
                    objective
                )
            )


    factual = (
        learning.get(
            "factual_knowledge",
            [],
        )
    )


    if factual:

        st.markdown(
            "### Grundlagen"
        )


        for item in factual:

            with st.expander(
                item.get(
                    "title",
                    "Lerninhalt",
                )
            ):

                st.write(
                    item.get(
                        "text",
                        "",
                    )
                )


                if item.get(
                    "formula"
                ):
                    st.markdown(
                        "**Formel**"
                    )

                    st.write(
                        item[
                            "formula"
                        ]
                    )


                if item.get(
                    "unit"
                ):
                    st.caption(
                        "Einheit: "
                        + str(
                            item[
                                "unit"
                            ]
                        )
                    )


    conceptual = (
        learning.get(
            "conceptual_knowledge",
            [],
        )
    )


    if conceptual:

        st.markdown(
            "### Zusammenhänge verstehen"
        )


        for item in conceptual:

            with st.expander(
                item.get(
                    "question",
                    "Erklärung",
                )
            ):

                st.write(
                    item.get(
                        "answer",
                        "",
                    )
                )


    procedural = (
        learning.get(
            "procedural_knowledge",
            [],
        )
    )


    if procedural:

        st.markdown(
            "### Vorgehen"
        )


        for item in procedural:

            with st.expander(
                item.get(
                    "title",
                    "Vorgehen",
                )
            ):

                for (
                    number,
                    step,
                ) in enumerate(
                    item.get(
                        "steps",
                        [],
                    ),
                    start=1,
                ):

                    st.write(
                        f"{number}. "
                        + str(
                            step
                        )
                    )


                if item.get(
                    "formula"
                ):
                    st.caption(
                        "Formel: "
                        + str(
                            item[
                                "formula"
                            ]
                        )
                    )


    quizzes = (
        learning.get(
            "quizzes",
            [],
        )
    )


    if quizzes:

        st.markdown(
            "### Quiz"
        )


        for (
            position,
            quiz,
        ) in enumerate(
            quizzes,
            start=1,
        ):

            with st.container(
                border=True
            ):

                st.caption(
                    f"Frage {position}"
                )

                render_quiz(
                    quiz,
                    selected_test,
                )


    reflections = (
        learning.get(
            "reflection_questions",
            [],
        )
    )


    if reflections:

        st.markdown(
            "### Reflexion"
        )


        for question in reflections:

            with st.container(
                border=True
            ):

                render_reflection(
                    question,
                    selected_test,
                )


    transfer_tasks = (
        learning.get(
            "transfer_tasks",
            [],
        )
    )


    if transfer_tasks:

        st.markdown(
            "### Transfer"
        )


        for task in transfer_tasks:

            with st.container(
                border=True
            ):

                render_transfer_task(
                    task,
                    selected_test,
                )


    takeaways = (
        learning.get(
            "key_takeaways",
            [],
        )
    )


    if takeaways:

        st.markdown(
            "### Zentrale Erkenntnisse"
        )


        for takeaway in takeaways:
            st.write(
                "• "
                + str(
                    takeaway
                )
            )


# ============================================================
# SECTION:
# ANALYSE
# ============================================================

elif section == "Analyse":

    st.subheader(
        "Erweiterte Analyse"
    )


    st.write(
        "Hier werden die Ereignissegmentierung, "
        "die Kennwerte des Hauptzyklus, die "
        "Prüfstandsvalidierung sowie Zell- und "
        "Temperaturkennwerte technisch "
        "nachvollziehbar dargestellt."
    )


    # --------------------------------------------------------
    # Additional analysis CSV files are loaded ONLY here.
    # --------------------------------------------------------

    main_cycle_table = (
        read_optional_export_csv(
            "main_cycle.csv",
            selected_test,
        )
    )


    validation_table = (
        read_optional_export_csv(
            "validation.csv",
            selected_test,
        )
    )


    cell_summary_table = (
        read_optional_export_csv(
            "cell_summary.csv",
            selected_test,
        )
    )


    temperature_summary_table = (
        read_optional_export_csv(
            "temperature_summary.csv",
            selected_test,
        )
    )


    # --------------------------------------------------------
    # CALCULATION BASICS
    # --------------------------------------------------------

    st.markdown(
        "### Berechnungsgrundlagen"
    )


    st.latex(
        r"""
        Q_{\mathrm{Ah}}
        =
        \frac{1}{3600}
        \left|
        \int_{t_0}^{t_1}
        I(t)\,\mathrm{d}t
        \right|
        """
    )


    st.latex(
        r"""
        E_{\mathrm{Wh}}
        =
        \frac{1}{3600}
        \int_{t_0}^{t_1}
        U(t)\,|I(t)|\,\mathrm{d}t
        """
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


    if number_of_cells > 1:

        st.latex(
            r"""
            \Delta V(t)
            =
            V_{\mathrm{max}}(t)
            -
            V_{\mathrm{min}}(t)
            """
        )


    # --------------------------------------------------------
    # EVENT TABLE
    # --------------------------------------------------------

    st.markdown(
        "### Ereignisübersicht"
    )


    st.caption(
        "Alle erkannten Lade- und Entladeereignisse "
        "werden getrennt ausgewertet. Die Tabelle "
        "enthält die Python-Ergebnisse und – sofern "
        "verfügbar – die zugehörigen "
        "Prüfstandsabweichungen."
    )


    if (
        events is None
        or
        events.empty
    ):

        st.info(
            "Keine Ereignistabelle verfügbar."
        )


    else:

        event_table = (
            events.copy()
        )


        event_table = (
            event_table.rename(
                columns={
                    "event_type":
                        "Ereignistyp",

                    "event":
                        "Nr.",

                    "event_number":
                        "Nr.",

                    "start_s":
                        "Start [s]",

                    "end_s":
                        "Ende [s]",

                    "duration_s":
                        "Dauer [s]",

                    "active_duration_s":
                        "Aktive Dauer [s]",

                    "python_capacity_Ah":
                        "Python Kapazität [Ah]",

                    "tester_capacity_Ah_for_validation":
                        "Prüfstand Kapazität [Ah]",

                    "quantity_difference_div3600_pct":
                        "Kapazitätsabweichung [%]",

                    "python_energy_Wh":
                        "Python Energie [Wh]",

                    "tester_energy_Wh_for_validation":
                        "Prüfstand Energie [Wh]",

                    "energy_difference_div3600_pct":
                        "Energieabweichung [%]",

                    "mean_current_A":
                        "Mittlerer Strom [A]",

                    "minimum_voltage_V":
                        "Min. Spannung [V]",

                    "maximum_voltage_V":
                        "Max. Spannung [V]",
                }
            )
        )


        st.dataframe(
            event_table,
            use_container_width=True,
            hide_index=True,
        )


    # --------------------------------------------------------
    # MAIN CYCLE TABLE
    # --------------------------------------------------------

    st.markdown(
        "### Kennwerte des Hauptzyklus"
    )


    if (
        main_cycle_table
        is not None
        and
        not main_cycle_table.empty
    ):

        display_table = (
            main_cycle_table.copy()
        )


        display_table = (
            display_table.rename(
                columns={
                    "phase":
                        "Phase",

                    "event":
                        "Ereignis",

                    "start_s":
                        "Start [s]",

                    "end_s":
                        "Ende [s]",

                    "duration_s":
                        "Dauer [s]",

                    "active_duration_s":
                        "Aktive Dauer [s]",

                    "capacity_Ah":
                        "Kapazität [Ah]",

                    "energy_Wh":
                        "Energie [Wh]",

                    "mean_current_A":
                        "Mittlerer Strom [A]",

                    "minimum_voltage_V":
                        "Min. Spannung [V]",

                    "maximum_voltage_V":
                        "Max. Spannung [V]",
                }
            )
        )


        st.dataframe(
            display_table,
            use_container_width=True,
            hide_index=True,
        )


    else:

        c1, c2, c3, c4 = (
            st.columns(4)
        )


        with c1:
            st.metric(
                "Entladekapazität",

                metric_text(
                    discharge_capacity,
                    "Ah",
                    3,
                ),
            )


        with c2:
            st.metric(
                "Ladekapazität",

                metric_text(
                    capacity_summary.get(
                        "recharge_Ah"
                    ),
                    "Ah",
                    3,
                ),
            )


        with c3:
            st.metric(
                "Energieeffizienz",

                metric_text(
                    energy_efficiency,
                    "%",
                    3,
                ),
            )


        with c4:
            st.metric(
                "Kapazitätsbilanz",

                metric_text(
                    capacity_summary.get(
                        "capacity_balance_pct"
                    ),
                    "%",
                    2,
                ),
            )


    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    st.markdown(
        "### Prüfstandsvalidierung"
    )


    st.write(
        "Die Prüfstandswerte werden ausschließlich "
        "nach der Python-KPI-Berechnung zur "
        "Validierung herangezogen."
    )


    if (
        validation_table
        is not None
        and
        not validation_table.empty
    ):

        display_validation = (
            validation_table.copy()
        )


        display_validation = (
            display_validation.rename(
                columns={
                    "metric":
                        "Kennwert",

                    "python_value":
                        "Python",

                    "tester_value":
                        "Prüfstand",

                    "difference":
                        "Differenz",

                    "deviation_pct":
                        "Abweichung [%]",

                    "unit":
                        "Einheit",
                }
            )
        )


        st.dataframe(
            display_validation,
            use_container_width=True,
            hide_index=True,
        )


    else:

        fallback_validation = (
            pd.DataFrame(
                {
                    "Kennwert": [
                        "Ladekapazität",
                        "Ladeenergie",
                        "Entladekapazität",
                        "Entladeenergie",
                        "Energieeffizienz",
                    ],

                    "Abweichung [%]": [
                        validation_summary.get(
                            "charge_capacity_difference_pct"
                        ),

                        validation_summary.get(
                            "charge_energy_difference_pct"
                        ),

                        validation_summary.get(
                            "discharge_capacity_difference_pct"
                        ),

                        validation_summary.get(
                            "discharge_energy_difference_pct"
                        ),

                        validation_summary.get(
                            "energy_efficiency_difference_pct"
                        ),
                    ],
                }
            )
        )


        st.dataframe(
            fallback_validation,
            use_container_width=True,
            hide_index=True,
        )


    tester_efficiency = (
        validation_summary.get(
            "tester_energy_efficiency_pct"
        )
    )


    if (
        tester_efficiency
        is not None
    ):

        st.caption(
            "Vom Prüfstand gespeicherte "
            "Energieeffizienz: "
            +
            metric_text(
                tester_efficiency,
                "%",
                3,
            )
        )


    # --------------------------------------------------------
    # CELL SUMMARY
    # --------------------------------------------------------

    st.markdown(
        "### Zellkennwerte"
    )


    if (
        cell_summary_table
        is not None
        and
        not cell_summary_table.empty
    ):

        display_cells = (
            cell_summary_table.copy()
        )


        display_cells = (
            display_cells.rename(
                columns={
                    "metric":
                        "Kennwert",

                    "value":
                        "Wert",

                    "unit":
                        "Einheit",
                }
            )
        )


        st.dataframe(
            display_cells,
            use_container_width=True,
            hide_index=True,
        )


    else:

        fallback_cells = [
            {
                "Kennwert":
                    "Anzahl erkannter Zellen",

                "Wert":
                    number_of_cells,

                "Einheit":
                    "",
            }
        ]


        if number_of_cells > 0:

            fallback_cells.extend(
                [
                    {
                        "Kennwert":
                            "Zelle mit "
                            "niedrigster Spannung",

                        "Wert":
                            cell_label(
                                cell_summary.get(
                                    "weakest_cell"
                                )
                            ),

                        "Einheit":
                            "",
                    },

                    {
                        "Kennwert":
                            "Niedrigste Zellspannung",

                        "Wert":
                            cell_summary.get(
                                "weakest_cell_voltage_V"
                            ),

                        "Einheit":
                            "V",
                    },
                ]
            )


        if number_of_cells > 1:

            fallback_cells.extend(
                [
                    {
                        "Kennwert":
                            "Maximale "
                            "Zellspannungsdifferenz",

                        "Wert":
                            cell_summary.get(
                                "maximum_spread_mV"
                            ),

                        "Einheit":
                            "mV",
                    },

                    {
                        "Kennwert":
                            "Mittlere "
                            "Zellspannungsdifferenz",

                        "Wert":
                            cell_summary.get(
                                "mean_spread_mV"
                            ),

                        "Einheit":
                            "mV",
                    },
                ]
            )


        st.dataframe(
            pd.DataFrame(
                fallback_cells
            ),
            use_container_width=True,
            hide_index=True,
        )


    # --------------------------------------------------------
    # TEMPERATURE SUMMARY
    # --------------------------------------------------------

    st.markdown(
        "### Temperaturkennwerte"
    )


    if (
        temperature_summary_table
        is not None
        and
        not temperature_summary_table.empty
    ):

        display_temperature = (
            temperature_summary_table.copy()
        )


        display_temperature = (
            display_temperature.rename(
                columns={
                    "metric":
                        "Kennwert",

                    "value":
                        "Wert",

                    "unit":
                        "Einheit",
                }
            )
        )


        st.dataframe(
            display_temperature,
            use_container_width=True,
            hide_index=True,
        )


    else:

        fallback_temperature = (
            pd.DataFrame(
                [
                    {
                        "Kennwert":
                            "Maximale Temperatur",

                        "Wert":
                            temperature_summary.get(
                                "maximum_C"
                            ),

                        "Einheit":
                            "°C",
                    },

                    {
                        "Kennwert":
                            "Temperaturänderung",

                        "Wert":
                            temperature_summary.get(
                                "temperature_change_C"
                            ),

                        "Einheit":
                            "°C",
                    },

                    {
                        "Kennwert":
                            "Maximale "
                            "Temperaturdifferenz",

                        "Wert":
                            temperature_summary.get(
                                "maximum_spread_C"
                            ),

                        "Einheit":
                            "°C",
                    },
                ]
            )
        )


        st.dataframe(
            fallback_temperature,
            use_container_width=True,
            hide_index=True,
        )


    # --------------------------------------------------------
    # DATA BASIS
    # --------------------------------------------------------

    st.markdown(
        "### Datenbasis des Dashboards"
    )


    st.write(
        "Das Dashboard verwendet ausschließlich "
        "bereits aufbereitete CSV- und JSON-Dateien. "
        "Die analytischen Berechnungen werden nicht "
        "erneut in Streamlit durchgeführt."
    )


    analysis_info = (
        manifest.get(
            "analysis",
            {},
        )
    )


    def status_text(
        value,
    ):
        if value is True:
            return "Ja"

        if value is False:
            return "Nein"

        if value is None:
            return "–"

        return str(
            value
        )


    if analysis_info:

        meta_left, meta_right = (
            st.columns(2)
        )


        with meta_left:

            with st.container(
                border=True
            ):

                st.markdown(
                    "#### Analyse"
                )


                st.markdown(
                    "**KPI-Berechnung aus "
                    "Vollauflösung**"
                )

                st.caption(
                    status_text(
                        analysis_info.get(
                            "kpis_calculated_from_full_resolution_data"
                        )
                    )
                )


                st.markdown(
                    "**Native Zeitstempel "
                    "verwendet**"
                )

                st.caption(
                    status_text(
                        analysis_info.get(
                            "native_timestamps_used_for_analysis"
                        )
                    )
                )


                st.markdown(
                    "**Ereignisbasierte "
                    "Segmentierung**"
                )

                st.caption(
                    status_text(
                        analysis_info.get(
                            "event_based_segmentation"
                        )
                    )
                )


                st.markdown(
                    "**Prüfstandsvalidierung**"
                )

                st.caption(
                    status_text(
                        analysis_info.get(
                            "tester_validation_included"
                        )
                    )
                )


        with meta_right:

            with st.container(
                border=True
            ):

                st.markdown(
                    "#### Visualisierung"
                )


                st.markdown(
                    "**Visualisierungsdaten "
                    "reduziert**"
                )

                st.caption(
                    status_text(
                        analysis_info.get(
                            "visualization_data_downsampled"
                        )
                    )
                )


                maximum_rows = (
                    analysis_info.get(
                        "maximum_visualization_rows"
                    )
                )


                st.markdown(
                    "**Maximale "
                    "Visualisierungszeilen**"
                )


                if (
                    maximum_rows
                    is not None
                ):

                    st.caption(
                        f"{int(maximum_rows):,}"
                        .replace(
                            ",",
                            ".",
                        )
                    )


                else:

                    st.caption(
                        "–"
                    )


                st.markdown(
                    "**Analytische Neuberechnung "
                    "in Streamlit**"
                )


                dashboard_recalculates = (
                    analysis_info.get(
                        "dashboard_recalculates_kpis"
                    )
                )


                if (
                    dashboard_recalculates
                    is False
                ):
                    st.caption(
                        "Nein"
                    )


                else:
                    st.caption(
                        status_text(
                            dashboard_recalculates
                        )
                    )


    st.markdown(
        """
        <div class="green-note">
            <strong>
                Trennung von Analyse und Visualisierung:
            </strong>
            Die vollständigen Messdaten werden für die
            Ereigniserkennung und KPI-Berechnung verwendet.
            Erst danach werden reduzierte Visualisierungsdaten
            exportiert. Die Prüfstandswerte dienen ausschließlich
            der nachträglichen Validierung.
        </div>
        """,
        unsafe_allow_html=True,
    )


    # --------------------------------------------------------
    # EXPORT FILES
    # --------------------------------------------------------

    with st.expander(
        "Exportdateien"
    ):

        st.caption(
            "Diese Dateien bilden gleichzeitig "
            "die Schnittstelle für die spätere "
            "DiBaLa-/Unity-Integration."
        )


        d1, d2, d3, d4 = (
            st.columns(4)
        )


        with d1:
            show_download_button(
                "Kennwerte",
                "capacity_summary.json",
                "application/json",
                selected_test,
            )


        with d2:
            show_download_button(
                "Ereignisse",
                "events.csv",
                "text/csv",
                selected_test,
            )


        with d3:
            show_download_button(
                "Validierung",
                "validation.csv",
                "text/csv",
                selected_test,
            )


        with d4:
            show_download_button(
                "Lerninhalte",
                "learning_content.json",
                "application/json",
                selected_test,
            )