from pathlib import Path
import html
import json
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from data_loader import (
    load_ocv_index,
    load_ocv_test,
    load_ocv_temperature_comparison,
    load_ocv_comparison_learning,
)


CELL_COLUMN_PATTERN = re.compile(
    r"^cell_\d+_V$"
)

UNI_GREEN = "#6F9512"


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
    unit,
    decimals=2,
):
    number = format_number(
        value,
        decimals,
    )

    if number == "–":
        return number

    return (
        f"{number} {unit}"
    )


def format_temperature(value):
    value = safe_float(
        value
    )

    if value is None:
        return "–"

    rounded = round(
        value
    )

    if abs(
        value - rounded
    ) < 0.05:
        return (
            f"{rounded:.0f} °C"
        )

    return (
        f"{value:.1f} °C"
    )

def get_test_label(entry):
    return format_temperature(
        entry.get(
            "temperature_C"
        )
    )

def get_graph_explanation(
    learning_content,
    graph_id,
):
    if not learning_content:
        return None

    explanations = (
        learning_content.get(
            "graph_explanations",
            []
        )
    )

    for item in explanations:
        if (
            item.get("id")
            == graph_id
        ):
            return item

    return None


def get_kpi_explanation(
    learning_content,
    kpi_id,
):
    if not learning_content:
        return None

    explanations = (
        learning_content.get(
            "kpi_explanations",
            {}
        )
    )

    return explanations.get(
        kpi_id
    )


def render_graph_explanation(
    explanation,
):
    """
    Combine the exported graph explanation into one
    compact learning box.

    The JSON structure remains unchanged.
    """
    if not explanation:
        return

    parts = []

    what = explanation.get(
        "what"
    )

    focus = explanation.get(
        "focus"
    )

    interpretation = (
        explanation.get(
            "interpretation"
        )
    )

    if what:
        parts.append(
            what.strip()
        )

    if focus:
        parts.append(
            focus.strip()
        )

    if interpretation:
        parts.append(
            interpretation.strip()
        )

    if not parts:
        return

    text = " ".join(
        parts
    )

    safe_text = html.escape(
        text
    )

    st.markdown(
        f"""
        <div class="learn-box">
            <div class="learn-box-title">
                Kurz erklärt
            </div>
            <div class="learn-box-text">
                {safe_text}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric(
    label,
    value,
    explanation=None,
):
    st.metric(
        label,
        value,
    )

    if explanation:
        short = explanation.get(
            "short"
        )

        if short:
            st.caption(
                short
            )


def get_cell_columns(
    dataframe,
):
    if dataframe is None:
        return []

    return [
        column
        for column in dataframe.columns
        if CELL_COLUMN_PATTERN.match(
            column
        )
    ]


def build_phase_hover(
    dataframe,
):
    hover_text = []

    for _, row in dataframe.iterrows():
        time_h = safe_float(
            row.get(
                "experiment_time_h"
            )
        )

        voltage = safe_float(
            row.get(
                "voltage_V"
            )
        )

        current = safe_float(
            row.get(
                "current_A"
            )
        )

        phase = row.get(
            "phase_label_de",
            "–",
        )

        relaxation_time = (
            safe_float(
                row.get(
                    "relaxation_time_min"
                )
            )
        )

        lines = []

        if time_h is not None:
            lines.append(
                "Zeit: "
                + format_number(
                    time_h,
                    2,
                )
                + " h"
            )

        if voltage is not None:
            lines.append(
                "Spannung: "
                + format_number(
                    voltage,
                    3,
                )
                + " V"
            )

        if current is not None:
            lines.append(
                "Strom: "
                + format_number(
                    current,
                    3,
                )
                + " A"
            )

        lines.append(
            "Phase: "
            + str(
                phase
            )
        )

        if relaxation_time is not None:
            lines.append(
                "Relaxationszeit: "
                + format_number(
                    relaxation_time,
                    1,
                )
                + " min"
            )

        hover_text.append(
            "<br>".join(
                lines
            )
        )

    return hover_text


def add_phase_backgrounds(
    figure,
    phases,
    origin_s,
):
    if phases is None:
        return

    if phases.empty:
        return

    if origin_s is None:
        return

    colors = {
        "initial_rest":
            "rgba(120, 130, 140, 0.08)",

        "main_discharge":
            "rgba(90, 130, 190, 0.08)",

        "relaxation":
            "rgba(111, 149, 18, 0.10)",
    }

    for _, row in phases.iterrows():
        role = row.get(
            "analysis_role"
        )

        if role not in colors:
            continue

        start_s = safe_float(
            row.get(
                "start_s"
            )
        )

        end_s = safe_float(
            row.get(
                "end_s"
            )
        )

        if (
            start_s is None
            or end_s is None
        ):
            continue

        x0 = (
            start_s
            - origin_s
        ) / 3600

        x1 = (
            end_s
            - origin_s
        ) / 3600

        figure.add_vrect(
            x0=x0,
            x1=x1,
            fillcolor=colors[
                role
            ],
            line_width=0,
            layer="below",
        )


def build_voltage_current_plot(
    electrical,
    phases,
):
    figure = make_subplots(
        specs=[
            [
                {
                    "secondary_y": True
                }
            ]
        ]
    )

    hover_text = (
        build_phase_hover(
            electrical
        )
    )

    figure.add_trace(
        go.Scatter(
            x=electrical[
                "experiment_time_h"
            ],
            y=electrical[
                "voltage_V"
            ],
            mode="lines",
            name="Spannung",
            line=dict(
                color=UNI_GREEN,
                width=2,
            ),
            hovertext=hover_text,
            hovertemplate=(
                "%{hovertext}"
                "<extra></extra>"
            ),
        ),
        secondary_y=False,
    )

    figure.add_trace(
        go.Scatter(
            x=electrical[
                "experiment_time_h"
            ],
            y=electrical[
                "current_A"
            ],
            mode="lines",
            name="Strom",
            line=dict(
                color="#59636E",
                width=1.4,
            ),
            hovertext=hover_text,
            hovertemplate=(
                "%{hovertext}"
                "<extra></extra>"
            ),
        ),
        secondary_y=True,
    )

    origin_s = safe_float(
        electrical[
            "timestamp_s"
        ].iloc[0]
    )

    add_phase_backgrounds(
        figure,
        phases,
        origin_s,
    )

    figure.update_xaxes(
        title_text=(
            "Versuchszeit [h]"
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


def build_discharge_plot(
    discharge,
):
    data = discharge.dropna(
        subset=[
            "relative_discharge_progress_pct",
            "voltage_V",
        ]
    ).copy()

    hover_text = []

    for _, row in data.iterrows():
        progress = safe_float(
            row.get(
                "relative_discharge_progress_pct"
            )
        )

        voltage = safe_float(
            row.get(
                "voltage_V"
            )
        )

        current = safe_float(
            row.get(
                "current_A"
            )
        )

        capacity = safe_float(
            row.get(
                "discharged_capacity_Ah"
            )
        )

        energy = safe_float(
            row.get(
                "discharged_energy_Wh"
            )
        )

        lines = [
            (
                "Entladefortschritt: "
                + format_number(
                    progress,
                    1,
                )
                + " %"
            ),
            (
                "Spannung: "
                + format_number(
                    voltage,
                    3,
                )
                + " V"
            ),
        ]

        if current is not None:
            lines.append(
                "Strom: "
                + format_number(
                    current,
                    3,
                )
                + " A"
            )

        if capacity is not None:
            lines.append(
                "Entnommene Ladung: "
                + format_number(
                    capacity,
                    2,
                )
                + " Ah"
            )

        if energy is not None:
            lines.append(
                "Entnommene Energie: "
                + format_number(
                    energy / 1000,
                    3,
                )
                + " kWh"
            )

        hover_text.append(
            "<br>".join(
                lines
            )
        )

    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=data[
                "relative_discharge_progress_pct"
            ],
            y=data[
                "voltage_V"
            ],
            mode="lines",
            line=dict(
                color=UNI_GREEN,
                width=2,
            ),
            name="Modulspannung",
            hovertext=hover_text,
            hovertemplate=(
                "%{hovertext}"
                "<extra></extra>"
            ),
        )
    )

    figure.update_layout(
        height=440,
        margin=dict(
            l=25,
            r=25,
            t=30,
            b=30,
        ),
        xaxis_title=(
            "Relativer Entladefortschritt [%]"
        ),
        yaxis_title=(
            "Modulspannung [V]"
        ),
        hovermode="closest",
        showlegend=False,
    )

    return figure


def build_relaxation_plot(
    relaxation,
):
    data = relaxation.dropna(
        subset=[
            "relaxation_time_min",
            "voltage_V",
        ]
    ).copy()

    hover_text = []

    for _, row in data.iterrows():
        time_min = safe_float(
            row.get(
                "relaxation_time_min"
            )
        )

        voltage = safe_float(
            row.get(
                "voltage_V"
            )
        )

        current = safe_float(
            row.get(
                "current_A"
            )
        )

        recovery = safe_float(
            row.get(
                "voltage_recovery_V"
            )
        )

        lines = [
            (
                "Relaxationszeit: "
                + format_number(
                    time_min,
                    1,
                )
                + " min"
            ),
            (
                "Spannung: "
                + format_number(
                    voltage,
                    3,
                )
                + " V"
            ),
        ]

        if current is not None:
            lines.append(
                "Strom: "
                + format_number(
                    current,
                    3,
                )
                + " A"
            )

        if recovery is not None:
            lines.append(
                "Spannungserholung: "
                + format_number(
                    recovery,
                    3,
                )
                + " V"
            )

        hover_text.append(
            "<br>".join(
                lines
            )
        )

    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=data[
                "relaxation_time_min"
            ],
            y=data[
                "voltage_V"
            ],
            mode="lines",
            line=dict(
                color=UNI_GREEN,
                width=2.2,
            ),
            name="Relaxationsspannung",
            hovertext=hover_text,
            hovertemplate=(
                "%{hovertext}"
                "<extra></extra>"
            ),
        )
    )

    maximum_time = safe_float(
        data[
            "relaxation_time_min"
        ].max()
    )

    for minute in (
        1,
        10,
        30,
        60,
    ):
        if (
            maximum_time is not None
            and minute <= maximum_time
        ):
            figure.add_vline(
                x=minute,
                line_width=1,
                line_dash="dot",
                line_color="#A5AEA0",
                annotation_text=(
                    f"{minute} min"
                ),
                annotation_position=(
                    "top"
                ),
            )

    figure.update_layout(
        height=440,
        margin=dict(
            l=25,
            r=25,
            t=40,
            b=30,
        ),
        xaxis_title=(
            "Relaxationszeit [min]"
        ),
        yaxis_title=(
            "Modulspannung [V]"
        ),
        hovermode="closest",
        showlegend=False,
    )

    return figure


def build_cell_plot(
    cells,
    selected_cells,
    phases,
):
    figure = go.Figure()

    if "phase_label_de" in cells.columns:
        phase_values = (
            cells[
                "phase_label_de"
            ]
        )

    else:
        phase_values = pd.Series(
            ["–"] * len(cells)
        )

    origin_s = None

    if (
        "timestamp_s"
        in cells.columns
        and not cells.empty
    ):
        origin_s = safe_float(
            cells[
                "timestamp_s"
            ].iloc[0]
        )

    for column in selected_cells:
        hover_text = []

        for position, value in enumerate(
            cells[column]
        ):
            time_h = safe_float(
                cells[
                    "experiment_time_h"
                ].iloc[position]
            )

            voltage = safe_float(
                value
            )

            phase = (
                phase_values.iloc[
                    position
                ]
            )

            text = (
                "Zeit: "
                + format_number(
                    time_h,
                    2,
                )
                + " h"
                + "<br>Zelle: "
                + column
                + "<br>Zellspannung: "
                + format_number(
                    voltage,
                    4,
                )
                + " V"
                + "<br>Phase: "
                + str(
                    phase
                )
            )

            hover_text.append(
                text
            )

        figure.add_trace(
            go.Scatter(
                x=cells[
                    "experiment_time_h"
                ],
                y=cells[
                    column
                ],
                mode="lines",
                name=column,
                hovertext=hover_text,
                hovertemplate=(
                    "%{hovertext}"
                    "<extra></extra>"
                ),
            )
        )

    add_phase_backgrounds(
        figure,
        phases,
        origin_s,
    )

    figure.update_layout(
        height=460,
        margin=dict(
            l=25,
            r=25,
            t=40,
            b=30,
        ),
        xaxis_title=(
            "Versuchszeit [h]"
        ),
        yaxis_title=(
            "Zellspannung [V]"
        ),
        hovermode="closest",
        legend=dict(
            orientation="h",
            y=1.10,
        ),
    )

    return figure


def build_cell_spread_plot(
    cells,
):
    if (
        "phase_label_de"
        in cells.columns
    ):
        customdata = (
            cells[
                "phase_label_de"
            ]
        )

    else:
        customdata = (
            ["–"] * len(cells)
        )

    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=cells[
                "experiment_time_h"
            ],
            y=cells[
                "cell_spread_mV"
            ],
            mode="lines",
            line=dict(
                color=UNI_GREEN,
                width=2,
            ),
            name=(
                "Zellspannungsdifferenz"
            ),
            customdata=customdata,
            hovertemplate=(
                "Zeit: %{x:.2f} h"
                "<br>Zellspannungsdifferenz: "
                "%{y:.2f} mV"
                "<br>Phase: %{customdata}"
                "<extra></extra>"
            ),
        )
    )

    figure.update_layout(
        height=370,
        margin=dict(
            l=25,
            r=25,
            t=30,
            b=30,
        ),
        xaxis_title=(
            "Versuchszeit [h]"
        ),
        yaxis_title=(
            "Zellspannungsdifferenz [mV]"
        ),
        showlegend=False,
    )

    return figure


def build_comparison_plot(
    dataframe,
    y_column,
    y_title,
    value_unit,
    decimals=2,
):
    data = dataframe.dropna(
        subset=[
            "temperature_C",
            y_column,
        ]
    ).copy()

    data = data.sort_values(
        "temperature_C"
    )

    hover_text = []

    for _, row in data.iterrows():
        temperature = safe_float(
            row[
                "temperature_C"
            ]
        )

        value = safe_float(
            row[
                y_column
            ]
        )

        hover_text.append(
            (
                "Temperatur: "
                + format_temperature(
                    temperature
                )
                + "<br>"
                + y_title
                + ": "
                + format_number(
                    value,
                    decimals,
                )
                + " "
                + value_unit
            )
        )

    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=data[
                "temperature_C"
            ],
            y=data[
                y_column
            ],
            mode="lines+markers",
            line=dict(
                color=UNI_GREEN,
                width=2,
            ),
            marker=dict(
                size=9,
            ),
            hovertext=hover_text,
            hovertemplate=(
                "%{hovertext}"
                "<extra></extra>"
            ),
        )
    )

    figure.update_layout(
        height=340,
        margin=dict(
            l=25,
            r=20,
            t=20,
            b=30,
        ),
        xaxis_title=(
            "Prüftemperatur [°C]"
        ),
        yaxis_title=(
            f"{y_title} [{value_unit}]"
        ),
        showlegend=False,
    )

    return figure


def render_quiz(
    quiz,
    prefix,
):
    quiz_id = quiz.get(
        "id",
        "quiz",
    )

    key_base = (
        f"{prefix}_{quiz_id}"
    )

    question = quiz.get(
        "question",
        ""
    )

    options = quiz.get(
        "options",
        []
    )

    correct_option = quiz.get(
        "correct_option"
    )

    st.markdown(
        "**"
        + question
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

    if st.button(
        "Antwort prüfen",
        key=(
            key_base
            + "_check"
        ),
    ):
        if selected is None:
            st.warning(
                "Bitte zuerst eine "
                "Antwort auswählen."
            )

        else:
            selected_index = (
                options.index(
                    selected
                )
            )

            st.session_state[
                key_base
                + "_checked"
            ] = True

            st.session_state[
                key_base
                + "_correct"
            ] = (
                selected_index
                == correct_option
            )

    if st.session_state.get(
        key_base
        + "_checked"
    ):
        if st.session_state.get(
            key_base
            + "_correct"
        ):
            st.success(
                quiz.get(
                    "feedback_correct",
                    "Richtig.",
                )
            )

        else:
            st.error(
                quiz.get(
                    "feedback_incorrect",
                    "Noch nicht korrekt.",
                )
            )

        explanation = quiz.get(
            "explanation"
        )

        if explanation:
            st.info(
                explanation
            )


def render_reflection(
    reflection,
    prefix,
):
    reflection_id = (
        reflection.get(
            "id",
            "reflection",
        )
    )

    key_base = (
        f"{prefix}_{reflection_id}"
    )

    prompt = reflection.get(
        "prompt",
        ""
    )

    minimum = int(
        reflection.get(
            "minimum_input_characters",
            0,
        )
        or 0
    )

    answer = st.text_area(
        prompt,
        key=(
            key_base
            + "_text"
        ),
        height=120,
    )

    if st.button(
        "Musterantwort anzeigen",
        key=(
            key_base
            + "_show"
        ),
    ):
        if len(
            answer.strip()
        ) < minimum:
            st.warning(
                "Bitte zuerst eine "
                "eigene Antwort formulieren."
            )

        else:
            st.session_state[
                key_base
                + "_revealed"
            ] = True

    if st.session_state.get(
        key_base
        + "_revealed"
    ):
        st.markdown(
            "**Mögliche Antwort**"
        )

        st.info(
            reflection.get(
                "model_answer",
                "",
            )
        )


def render_transfer_task(
    task,
    prefix,
):
    task_id = task.get(
        "id",
        "transfer",
    )

    key_base = (
        f"{prefix}_{task_id}"
    )

    scenario = task.get(
        "scenario"
    )

    if scenario:
        st.caption(
            scenario
        )

    question = task.get(
        "question",
        ""
    )

    options = task.get(
        "options",
        []
    )

    correct_option = task.get(
        "correct_option"
    )

    st.markdown(
        "**"
        + question
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

    if st.button(
        "Antwort prüfen",
        key=(
            key_base
            + "_check"
        ),
    ):
        if selected is None:
            st.warning(
                "Bitte zuerst eine "
                "Antwort auswählen."
            )

        else:
            selected_index = (
                options.index(
                    selected
                )
            )

            st.session_state[
                key_base
                + "_checked"
            ] = True

            st.session_state[
                key_base
                + "_correct"
            ] = (
                selected_index
                == correct_option
            )

    if st.session_state.get(
        key_base
        + "_checked"
    ):
        if st.session_state.get(
            key_base
            + "_correct"
        ):
            st.success(
                "Richtig."
            )

        else:
            st.error(
                "Noch nicht ganz."
            )

        explanation = task.get(
            "explanation"
        )

        if explanation:
            st.info(
                explanation
            )


index = load_ocv_index(
    required=False
)

tests = index.get(
    "tests",
    [],
)


if not tests:
    st.title(
        "OCV Verhalten"
    )

    st.warning(
        "Es sind noch keine "
        "OCV Exportdaten verfügbar."
    )

    st.stop()


test_ids = [
    item[
        "test_id"
    ]
    for item in tests
]


test_labels = {
    item[
        "test_id"
    ]:
        get_test_label(
            item
        )
    for item in tests
}

with st.sidebar:
    st.markdown("---")

    st.caption(
        "OCV Messung"
    )

    selected_test = st.radio(
        "OCV Messung auswählen",
        options=test_ids,
        format_func=lambda test_id: (
            test_labels.get(
                test_id,
                test_id,
            )
        ),
        key="ocv_test_selector",
        label_visibility="collapsed",
    )


bundle = load_ocv_test(
    selected_test,
    data_keys=[
        "electrical",
        "discharge",
        "relaxation",
        "cells",
        "temperature",
        "phases",
    ],
)


summary = bundle[
    "summary"
]

learning = (
    bundle.get(
        "learning_content"
    )
    or {}
)

electrical = bundle.get(
    "electrical"
)

discharge = bundle.get(
    "discharge"
)

relaxation = bundle.get(
    "relaxation"
)

cells = bundle.get(
    "cells"
)

phases = bundle.get(
    "phases"
)

manifest = bundle[
    "manifest"
]


comparison = (
    load_ocv_temperature_comparison()
)

comparison_learning = (
    load_ocv_comparison_learning()
    or {}
)


test_condition = summary.get(
    "test_condition",
    {},
)

discharge_summary = summary.get(
    "discharge",
    {},
)

relaxation_summary = summary.get(
    "relaxation",
    {},
)

cell_summary = summary.get(
    "cells",
    {},
)

module_summary = summary.get(
    "module",
    {},
)

validation = summary.get(
    "validation",
    {},
)


test_temperature = (
    test_condition.get(
        "temperature_C"
    )
)

number_of_cells = int(
    module_summary.get(
        "number_of_cells",
        0,
    )
    or 0
)

source_file = summary.get(
    "source_file",
    "",
)

if source_file:
    source_file = Path(
        str(
            source_file
        )
    ).name


st.title(
    "OCV Verhalten und Spannungsrelaxation"
)

st.write(
    "Temperaturabhängige Entladung und "
    "Spannungsrelaxation nach dem "
    "Abschalten des Entladestroms."
)


metadata_text = (
    format_temperature(
        test_temperature
    )
)

if number_of_cells == 1:
    metadata_text += (
        " · Einzelzelle"
    )

elif number_of_cells > 1:
    metadata_text += (
        f" · {number_of_cells} Zellen Modul"
    )

if source_file:
    metadata_text += (
        " · "
        + source_file
    )

st.caption(
    metadata_text
)


st.markdown(
    """
    <div class="green-note">
        Die Spannung während der Ruhephase wird als
        Relaxationsspannung ausgewertet. Sie wird nicht
        automatisch mit einer vollständig eingestellten
        Gleichgewichts OCV gleichgesetzt.
    </div>
    """,
    unsafe_allow_html=True,
)


k1, k2, k3, k4, k5 = (
    st.columns(5)
)


with k1:
    render_metric(
        "Prüftemperatur",
        format_temperature(
            test_temperature
        ),
        get_kpi_explanation(
            learning,
            "test_temperature_C",
        ),
    )


with k2:
    render_metric(
        "Entnommene Ladung",
        metric_text(
            discharge_summary.get(
                "capacity_Ah"
            ),
            "Ah",
            2,
        ),
        get_kpi_explanation(
            learning,
            "discharge_capacity_Ah",
        ),
    )


with k3:
    energy_Wh = safe_float(
        discharge_summary.get(
            "energy_Wh"
        )
    )

    if energy_Wh is not None:
        energy_kWh = (
            energy_Wh
            / 1000
        )

    else:
        energy_kWh = None

    render_metric(
        "Entnommene Energie",
        metric_text(
            energy_kWh,
            "kWh",
            2,
        ),
        get_kpi_explanation(
            learning,
            "discharge_energy_Wh",
        ),
    )


with k4:
    render_metric(
        "Spannungserholung",
        metric_text(
            relaxation_summary.get(
                "total_recovery_V"
            ),
            "V",
            3,
        ),
        get_kpi_explanation(
            learning,
            "total_recovery_V",
        ),
    )


with k5:
    render_metric(
        "Entladedauer",
        metric_text(
            discharge_summary.get(
                "duration_h"
            ),
            "h",
            2,
        ),
        get_kpi_explanation(
            learning,
            "discharge_duration_h",
        ),
    )


st.divider()


(
    phase_tab,
    discharge_tab,
    relaxation_tab,
    cells_tab,
    comparison_tab,
    learning_tab,
    advanced_tab,
) = st.tabs(
    [
        "Versuchsphasen",
        "Entladung",
        "Relaxation",
        "Zellverhalten",
        "Temperaturvergleich",
        "Lernmodus",
        "Erweiterte Analyse",
    ]
)


with phase_tab:
    st.subheader(
        "Versuchsphasen"
    )

    if (
        electrical is not None
        and not electrical.empty
    ):
        figure = (
            build_voltage_current_plot(
                electrical,
                phases,
            )
        )

        graph_col, info_col = (
            st.columns(
                [4, 1.3]
            )
        )

        with graph_col:
            st.plotly_chart(
                figure,
                use_container_width=True,
            )

        with info_col:
            render_graph_explanation(
                get_graph_explanation(
                    learning,
                    "voltage_current_time",
                )
            )

    else:
        st.warning(
            "Für diesen Test sind "
            "keine elektrischen "
            "Visualisierungsdaten verfügbar."
        )


with discharge_tab:
    st.subheader(
        "Entladeverhalten"
    )

    d1, d2, d3 = (
        st.columns(3)
    )

    with d1:
        st.metric(
            "Mittlerer Entladestrom",
            metric_text(
                discharge_summary.get(
                    "mean_current_A"
                ),
                "A",
                2,
            ),
        )

    with d2:
        st.metric(
            "Minimale Modulspannung",
            metric_text(
                discharge_summary.get(
                    "minimum_voltage_V"
                ),
                "V",
                2,
            ),
        )

    with d3:
        st.metric(
            "Entladedauer",
            metric_text(
                discharge_summary.get(
                    "duration_h"
                ),
                "h",
                2,
            ),
        )

    if (
        discharge is not None
        and not discharge.empty
    ):
        figure = (
            build_discharge_plot(
                discharge
            )
        )

        graph_col, info_col = (
            st.columns(
                [4, 1.3]
            )
        )

        with graph_col:
            st.plotly_chart(
                figure,
                use_container_width=True,
            )

        with info_col:
            render_graph_explanation(
                get_graph_explanation(
                    learning,
                    "voltage_relative_discharge",
                )
            )

    else:
        st.warning(
            "Keine exportierten "
            "Entladedaten verfügbar."
        )


with relaxation_tab:
    st.subheader(
        "Spannungsrelaxation"
    )

    r1, r2, r3 = (
        st.columns(3)
    )

    with r1:
        render_metric(
            "Sofortige Erholung",
            metric_text(
                relaxation_summary.get(
                    "immediate_recovery_V"
                ),
                "V",
                3,
            ),
            get_kpi_explanation(
                learning,
                "immediate_recovery_V",
            ),
        )

    with r2:
        render_metric(
            "Weitere Relaxation",
            metric_text(
                relaxation_summary.get(
                    "slow_relaxation_V"
                ),
                "V",
                3,
            ),
            get_kpi_explanation(
                learning,
                "slow_relaxation_V",
            ),
        )

    with r3:
        render_metric(
            "Gesamte Erholung",
            metric_text(
                relaxation_summary.get(
                    "total_recovery_V"
                ),
                "V",
                3,
            ),
            get_kpi_explanation(
                learning,
                "total_recovery_V",
            ),
        )

    if (
        relaxation is not None
        and not relaxation.empty
    ):
        figure = (
            build_relaxation_plot(
                relaxation
            )
        )

        graph_col, info_col = (
            st.columns(
                [4, 1.3]
            )
        )

        with graph_col:
            st.plotly_chart(
                figure,
                use_container_width=True,
            )

        with info_col:
            render_graph_explanation(
                get_graph_explanation(
                    learning,
                    "relaxation_voltage_time",
                )
            )

        st.markdown(
            "#### Gemeinsame Relaxationszeitpunkte"
        )

        c1, c2, c3, c4 = (
            st.columns(4)
        )

        checkpoint_values = [
            (
                c1,
                "1 min",
                "voltage_after_1min_V",
            ),
            (
                c2,
                "10 min",
                "voltage_after_10min_V",
            ),
            (
                c3,
                "30 min",
                "voltage_after_30min_V",
            ),
            (
                c4,
                "60 min",
                "voltage_after_60min_V",
            ),
        ]

        for (
            column,
            label,
            key,
        ) in checkpoint_values:
            with column:
                st.metric(
                    label,
                    metric_text(
                        relaxation_summary.get(
                            key
                        ),
                        "V",
                        3,
                    ),
                )

    else:
        st.warning(
            "Keine exportierten "
            "Relaxationsdaten verfügbar."
        )


with cells_tab:
    st.subheader(
        "Zellverhalten"
    )

    if (
        cells is None
        or cells.empty
    ):
        st.info(
            "Für diesen Test sind "
            "keine Einzelzellspannungen "
            "verfügbar."
        )

    else:
        cell_columns = (
            get_cell_columns(
                cells
            )
        )

        if not cell_columns:
            st.info(
                "Es wurden keine "
                "normalisierten "
                "Zellspannungssignale gefunden."
            )

        else:
            if len(
                cell_columns
            ) == 1:
                default_cells = (
                    cell_columns
                )

            else:
                default_cells = (
                    cell_columns[:3]
                )

                lowest_cell = (
                    cell_summary.get(
                        "lowest_cell"
                    )
                )

                if (
                    lowest_cell
                    in cell_columns
                    and lowest_cell
                    not in default_cells
                ):
                    default_cells.append(
                        lowest_cell
                    )

            selected_cells = (
                st.multiselect(
                    "Zellen auswählen",
                    options=cell_columns,
                    default=default_cells,
                    key=(
                        "ocv_cell_selector_"
                        + selected_test
                    ),
                )
            )

            if not selected_cells:
                st.info(
                    "Bitte mindestens "
                    "eine Zelle auswählen."
                )

            else:
                figure = (
                    build_cell_plot(
                        cells,
                        selected_cells,
                        phases,
                    )
                )

                graph_col, info_col = (
                    st.columns(
                        [4, 1.3]
                    )
                )

                with graph_col:
                    st.plotly_chart(
                        figure,
                        use_container_width=True,
                    )

                with info_col:
                    render_graph_explanation(
                        get_graph_explanation(
                            learning,
                            "cell_voltages",
                        )
                    )

            cell_k1, cell_k2 = (
                st.columns(2)
            )

            with cell_k1:
                st.metric(
                    "Niedrigste Zellspannung",
                    metric_text(
                        cell_summary.get(
                            "lowest_cell_voltage_V"
                        ),
                        "V",
                        4,
                    ),
                )

                lowest_cell = (
                    cell_summary.get(
                        "lowest_cell"
                    )
                )

                if lowest_cell:
                    st.caption(
                        "Betroffene Zelle: "
                        + str(
                            lowest_cell
                        )
                    )

            with cell_k2:
                if number_of_cells > 1:
                    st.metric(
                        "Maximale "
                        "Zellspannungsdifferenz",
                        metric_text(
                            cell_summary.get(
                                "maximum_spread_discharge_mV"
                            ),
                            "mV",
                            2,
                        ),
                    )

            if (
                number_of_cells > 1
                and "cell_spread_mV"
                in cells.columns
            ):
                st.markdown(
                    "#### Zellspannungsdifferenz"
                )

                spread_figure = (
                    build_cell_spread_plot(
                        cells
                    )
                )

                graph_col, info_col = (
                    st.columns(
                        [4, 1.3]
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


with comparison_tab:
    st.subheader(
        "Temperaturvergleich"
    )

    st.write(
        "Die verfügbaren OCV Messungen "
        "werden anhand ihrer gemessenen "
        "Prüftemperatur miteinander verglichen."
    )

    st.info(
        "Die Unterschiede zeigen zunächst "
        "das Verhalten unter den jeweiligen "
        "Versuchsbedingungen. Eine einzelne "
        "Ursache kann daraus nicht direkt "
        "abgeleitet werden."
    )

    if (
        comparison is None
        or comparison.empty
    ):
        st.warning(
            "Keine Vergleichsdaten verfügbar."
        )

    else:
        comparison_plot_data = (
            comparison.copy()
        )

        comparison_plot_data[
            "discharge_energy_kWh"
        ] = (
            comparison_plot_data[
                "discharge_energy_Wh"
            ]
            / 1000
        )

        left, right = (
            st.columns(2)
        )

        with left:
            st.markdown(
                "#### Entnommene Ladung"
            )

            figure = (
                build_comparison_plot(
                    comparison_plot_data,
                    "discharge_capacity_Ah",
                    "Entnommene Ladung",
                    "Ah",
                    2,
                )
            )

            st.plotly_chart(
                figure,
                use_container_width=True,
            )

            render_graph_explanation(
                get_graph_explanation(
                    comparison_learning,
                    "capacity_temperature",
                )
            )

        with right:
            st.markdown(
                "#### Entnommene Energie"
            )

            figure = (
                build_comparison_plot(
                    comparison_plot_data,
                    "discharge_energy_kWh",
                    "Entnommene Energie",
                    "kWh",
                    2,
                )
            )

            st.plotly_chart(
                figure,
                use_container_width=True,
            )

            render_graph_explanation(
                get_graph_explanation(
                    comparison_learning,
                    "energy_temperature",
                )
            )

        left, right = (
            st.columns(2)
        )

        with left:
            st.markdown(
                "#### Gesamte Spannungserholung"
            )

            figure = (
                build_comparison_plot(
                    comparison_plot_data,
                    "total_recovery_V",
                    "Spannungserholung",
                    "V",
                    3,
                )
            )

            st.plotly_chart(
                figure,
                use_container_width=True,
            )

            render_graph_explanation(
                get_graph_explanation(
                    comparison_learning,
                    "recovery_temperature",
                )
            )

        with right:
            st.markdown(
                "#### Spannung nach 60 Minuten"
            )

            figure = (
                build_comparison_plot(
                    comparison_plot_data,
                    "relaxation_60min_V",
                    "Spannung nach 60 min",
                    "V",
                    3,
                )
            )

            st.plotly_chart(
                figure,
                use_container_width=True,
            )

            render_graph_explanation(
                get_graph_explanation(
                    comparison_learning,
                    "relaxation_60min_temperature",
                )
            )

        with st.expander(
            "Vergleichstabelle anzeigen"
        ):
            display_columns = [
                "temperature_C",
                "discharge_duration_h",
                "discharge_capacity_Ah",
                "discharge_energy_Wh",
                "total_recovery_V",
                "relaxation_60min_V",
            ]

            available_columns = [
                column
                for column
                in display_columns
                if column
                in comparison.columns
            ]

            st.dataframe(
                comparison[
                    available_columns
                ],
                use_container_width=True,
                hide_index=True,
            )


with learning_tab:
    st.subheader(
        "Lernmodus"
    )

    current_learning_tab, comparison_learning_tab = (
        st.tabs(
            [
                "Aktueller Versuch",
                "Temperaturvergleich",
            ]
        )
    )

    with current_learning_tab:
        objectives = (
            learning.get(
                "learning_objectives",
                []
            )
        )

        if objectives:
            st.markdown(
                "### Lernziele"
            )

            for objective in objectives:
                st.write(
                    "• "
                    + objective.get(
                        "text",
                        "",
                    )
                )

        theory = learning.get(
            "theory",
            []
        )

        if theory:
            st.markdown(
                "### Kurz erklärt"
            )

            for item in theory:
                with st.expander(
                    item.get(
                        "title",
                        "Erklärung",
                    )
                ):
                    st.write(
                        item.get(
                            "text",
                            "",
                        )
                    )

        quizzes = learning.get(
            "quizzes",
            []
        )

        if quizzes:
            st.markdown(
                "### Quiz"
            )

            for position, quiz in enumerate(
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
                        (
                            "ocv_"
                            + selected_test
                        ),
                    )

        reflections = (
            learning.get(
                "reflections",
                []
            )
        )

        if reflections:
            st.markdown(
                "### Reflexion"
            )

            for reflection in reflections:
                with st.container(
                    border=True
                ):
                    render_reflection(
                        reflection,
                        (
                            "ocv_"
                            + selected_test
                        ),
                    )

        transfer_tasks = (
            learning.get(
                "transfer_tasks",
                []
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
                        (
                            "ocv_"
                            + selected_test
                        ),
                    )

    with comparison_learning_tab:
        comparison_quizzes = (
            comparison_learning.get(
                "quizzes",
                []
            )
        )

        comparison_reflections = (
            comparison_learning.get(
                "reflections",
                []
            )
        )

        comparison_transfer = (
            comparison_learning.get(
                "transfer_tasks",
                []
            )
        )

        if comparison_quizzes:
            st.markdown(
                "### Quiz zum Temperaturvergleich"
            )

            for position, quiz in enumerate(
                comparison_quizzes,
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
                        "ocv_comparison",
                    )

        if comparison_reflections:
            st.markdown(
                "### Reflexion"
            )

            for reflection in (
                comparison_reflections
            ):
                with st.container(
                    border=True
                ):
                    render_reflection(
                        reflection,
                        "ocv_comparison",
                    )

        if comparison_transfer:
            st.markdown(
                "### Transfer"
            )

            for task in (
                comparison_transfer
            ):
                with st.container(
                    border=True
                ):
                    render_transfer_task(
                        task,
                        "ocv_comparison",
                    )


with advanced_tab:
    st.subheader(
        "Erweiterte Analyse"
    )

    st.write(
        "Hier stehen zusätzliche technische "
        "Informationen zur Phasenerkennung, "
        "Validierung und Berechnung der "
        "Kennwerte zur Verfügung."
    )

    st.markdown(
        "### Berechnungsgrundlagen"
    )

    st.latex(
        r"""
        Q_\mathrm{dis}
        =
        -\frac{1}{3600}
        \int I(t)\,dt
        """
    )

    st.latex(
        r"""
        E_\mathrm{dis}
        =
        -\frac{1}{3600}
        \int U(t)I(t)\,dt
        """
    )

    st.latex(
        r"""
        \Delta V_\mathrm{total}
        =
        V_\mathrm{relax,end}
        -
        V_\mathrm{load,end}
        """
    )

    phase_validation = (
        validation.get(
            "phase_detection",
            {}
        )
    )

    st.markdown(
        "### Phasenerkennung"
    )

    v1, v2, v3 = (
        st.columns(3)
    )

    with v1:
        st.metric(
            "Zeitabstand zur Relaxation",
            metric_text(
                phase_validation.get(
                    "time_gap_to_relaxation_s"
                ),
                "s",
                3,
            ),
        )

    with v2:
        st.metric(
            "Maximaler Strombetrag in Relaxation",
            metric_text(
                phase_validation.get(
                    "maximum_absolute_relaxation_current_A"
                ),
                "A",
                3,
            ),
        )

    with v3:
        later_events = (
            phase_validation.get(
                "non_rest_events_after_relaxation"
            )
        )

        if later_events is None:
            later_events_text = "–"

        else:
            later_events_text = str(
                int(
                    later_events
                )
            )

        st.metric(
            "Spätere Belastungsereignisse",
            later_events_text,
        )

    tester = validation.get(
        "tester_comparison",
        {},
    )

    st.markdown(
        "### Vergleich mit Prüfstand"
    )

    t1, t2, t3, t4 = (
        st.columns(4)
    )

    with t1:
        st.metric(
            "Python Kapazität",
            metric_text(
                tester.get(
                    "python_discharge_capacity_Ah"
                ),
                "Ah",
                3,
            ),
        )

    with t2:
        st.metric(
            "Prüfstand Kapazität",
            metric_text(
                tester.get(
                    "tester_discharge_capacity_Ah"
                ),
                "Ah",
                3,
            ),
        )

    with t3:
        st.metric(
            "Kapazitätsabweichung",
            metric_text(
                tester.get(
                    "capacity_error_pct"
                ),
                "%",
                4,
            ),
        )

    with t4:
        st.metric(
            "Energieabweichung",
            metric_text(
                tester.get(
                    "energy_error_pct"
                ),
                "%",
                4,
            ),
        )

    if (
        phases is not None
        and not phases.empty
    ):
        st.markdown(
            "### Erkannte Ereignisse"
        )

        preferred_columns = [
            "event_number",
            "phase",
            "analysis_role",
            "phase_label_de",
            "start_s",
            "end_s",
            "duration_s",
            "mean_current_A",
        ]

        available_columns = [
            column
            for column
            in preferred_columns
            if column
            in phases.columns
        ]

        st.dataframe(
            phases[
                available_columns
            ],
            use_container_width=True,
            hide_index=True,
        )

    st.markdown(
        "### Export Informationen"
    )

    analysis_info = (
        manifest.get(
            "analysis",
            {}
        )
    )

    st.write(
        "Kennwerte aus vollständigen Messdaten: "
        + (
            "Ja"
            if analysis_info.get(
                "kpis_calculated_from_full_resolution_data"
            )
            else "Nein"
        )
    )

    st.write(
        "Originale Zeitstempel für die Analyse: "
        + (
            "Ja"
            if analysis_info.get(
                "native_timestamps_used_for_analysis"
            )
            else "Nein"
        )
    )

    st.write(
        "Visualisierungsdaten reduziert: "
        + (
            "Ja"
            if analysis_info.get(
                "visualization_data_downsampled"
            )
            else "Nein"
        )
    )

    maximum_rows = (
        analysis_info.get(
            "maximum_visualization_rows"
        )
    )

    if maximum_rows is not None:
        st.write(
            "Maximale Anzahl an Zeilen pro "
            "Visualisierungsdatei: "
            + str(
                maximum_rows
            )
        )

    st.markdown(
        "### Dateien herunterladen"
    )

    download_1, download_2 = (
        st.columns(2)
    )

    with download_1:
        summary_json = json.dumps(
            summary,
            ensure_ascii=False,
            indent=2,
        )

        st.download_button(
            "OCV Summary herunterladen",
            data=summary_json,
            file_name=(
                selected_test
                + "_ocv_summary.json"
            ),
            mime="application/json",
        )

    with download_2:
        if learning:
            learning_json = json.dumps(
                learning,
                ensure_ascii=False,
                indent=2,
            )

            st.download_button(
                "Lerninhalte herunterladen",
                data=learning_json,
                file_name=(
                    selected_test
                    + "_learning_content.json"
                ),
                mime="application/json",
            )