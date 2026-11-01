from pathlib import Path
import html
import re

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from data_loader import (
    load_ocv_index,
    load_ocv_test,
    load_ocv_temperature_comparison,
    load_ocv_comparison_learning,
)


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

    except (
        TypeError,
        ValueError,
    ):
        return None

    if not np.isfinite(
        value
    ):
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


# ============================================================
# LEARNING HELPERS
# ============================================================

def get_graph_explanation(
    learning_content,
    graph_id,
):
    if not learning_content:
        return None

    for item in learning_content.get(
        "graph_explanations",
        [],
    ):
        if (
            item.get("id")
            ==
            graph_id
        ):
            return item

    return None


def get_kpi_explanation(
    learning_content,
    kpi_id,
):
    if not learning_content:
        return None

    return (
        learning_content
        .get(
            "kpi_explanations",
            {},
        )
        .get(
            kpi_id
        )
    )


def render_graph_explanation(
    explanation,
):
    """
    Same graph-description style as the Discharge page:
    one continuous flow text inside a rectangular box.
    """

    if not explanation:
        return

    parts = []

    for key in (
        "what",
        "focus",
        "interpretation",
    ):
        value = explanation.get(
            key
        )

        if value:
            parts.append(
                str(
                    value
                ).strip()
            )

    if not parts:
        return

    safe_text = html.escape(
        " ".join(
            parts
        )
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


# ============================================================
# SECTION SELECTOR
# ============================================================

def section_selector(
    options,
    key,
):
    """
    Only the selected large section is rendered.

    This keeps the OCV page responsive because
    inactive Plotly charts are not rebuilt.
    """

    segmented_control = getattr(
        st,
        "segmented_control",
        None,
    )

    if (
        segmented_control
        is not None
    ):
        selected = (
            segmented_control(
                "Bereich",
                options=options,
                default=options[0],
                key=key,
                label_visibility="collapsed",
            )
        )

        if selected is not None:
            return selected

    return st.radio(
        "Bereich",
        options=options,
        horizontal=True,
        key=(
            key
            + "_fallback"
        ),
        label_visibility="collapsed",
    )


# ============================================================
# CELL HELPERS
# ============================================================

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


# ============================================================
# TIME AXIS
# ============================================================

def get_time_axis(
    dataframe,
):
    if (
        "experiment_time_h"
        in dataframe.columns
    ):
        return dataframe[
            "experiment_time_h"
        ]

    if (
        "timestamp_s"
        in dataframe.columns
        and
        not dataframe.empty
    ):
        return (
            (
                dataframe[
                    "timestamp_s"
                ]
                -
                dataframe[
                    "timestamp_s"
                ].iloc[0]
            )
            /
            3600.0
        )

    return np.arange(
        len(
            dataframe
        )
    )


# ============================================================
# PHASE BACKGROUNDS
# ============================================================

def add_phase_backgrounds(
    figure,
    phases,
    origin_s,
):
    if (
        phases is None
        or
        phases.empty
        or
        origin_s is None
    ):
        return

    colors = {
        "initial_rest":
            "rgba(120, 130, 140, 0.08)",

        "main_discharge":
            "rgba(90, 130, 190, 0.08)",

        "relaxation":
            "rgba(111, 149, 18, 0.10)",
    }

    for row in phases.itertuples(
        index=False
    ):
        role = getattr(
            row,
            "analysis_role",
            None,
        )

        if role not in colors:
            continue

        start_s = safe_float(
            getattr(
                row,
                "start_s",
                None,
            )
        )

        end_s = safe_float(
            getattr(
                row,
                "end_s",
                None,
            )
        )

        if (
            start_s is None
            or
            end_s is None
        ):
            continue

        figure.add_vrect(
            x0=(
                start_s
                -
                origin_s
            )
            /
            3600.0,

            x1=(
                end_s
                -
                origin_s
            )
            /
            3600.0,

            fillcolor=(
                colors[
                    role
                ]
            ),

            line_width=0,

            layer="below",
        )


# ============================================================
# VOLTAGE / CURRENT PLOT
# ============================================================

def build_voltage_current_plot(
    electrical,
    phases,
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

    x_values = get_time_axis(
        electrical
    )

    if (
        "phase_label_de"
        in electrical.columns
    ):
        phase_values = (
            electrical[
                "phase_label_de"
            ]
            .astype(
                str
            )
            .to_numpy()
        )

    else:
        phase_values = np.array(
            [
                "–"
            ]
            *
            len(
                electrical
            )
        )

    customdata = (
        np.column_stack(
            [
                phase_values
            ]
        )
    )

    figure.add_trace(
        go.Scatter(
            x=x_values,

            y=electrical[
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
            x=x_values,

            y=electrical[
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
                "Strom: %{y:.3f} A"
                "<br>"
                "Phase: %{customdata[0]}"
                "<extra></extra>"
            ),
        ),
        secondary_y=True,
    )

    origin_s = None

    if (
        "timestamp_s"
        in electrical.columns
        and
        not electrical.empty
    ):
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


# ============================================================
# DISCHARGE PLOT
# ============================================================

def build_discharge_plot(
    dataframe,
):
    data = (
        dataframe
        .dropna(
            subset=[
                "relative_discharge_progress_pct",
                "voltage_V",
            ]
        )
        .copy()
    )

    def optional_values(
        column,
    ):
        if (
            column
            in data.columns
        ):
            return (
                data[
                    column
                ]
                .to_numpy()
            )

        return np.full(
            len(
                data
            ),
            np.nan,
        )

    customdata = (
        np.column_stack(
            [
                optional_values(
                    "current_A"
                ),

                optional_values(
                    "discharged_capacity_Ah"
                ),

                optional_values(
                    "discharged_energy_Wh"
                ),
            ]
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

            customdata=customdata,

            hovertemplate=(
                "Entladefortschritt: "
                "%{x:.1f} %"
                "<br>"
                "Spannung: %{y:.3f} V"
                "<br>"
                "Strom: %{customdata[0]:.3f} A"
                "<br>"
                "Entnommene Ladung: "
                "%{customdata[1]:.2f} Ah"
                "<br>"
                "Entnommene Energie: "
                "%{customdata[2]:.1f} Wh"
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
            "Relativer "
            "Entladefortschritt [%]"
        ),

        yaxis_title=(
            "Modulspannung [V]"
        ),

        hovermode="closest",

        showlegend=False,
    )

    return figure


# ============================================================
# RELAXATION PLOT
# ============================================================

def build_relaxation_plot(
    dataframe,
):
    data = (
        dataframe
        .dropna(
            subset=[
                "relaxation_time_min",
                "voltage_V",
            ]
        )
        .copy()
    )

    def optional_values(
        column,
    ):
        if (
            column
            in data.columns
        ):
            return (
                data[
                    column
                ]
                .to_numpy()
            )

        return np.full(
            len(
                data
            ),
            np.nan,
        )

    customdata = (
        np.column_stack(
            [
                optional_values(
                    "current_A"
                ),

                optional_values(
                    "voltage_recovery_V"
                ),
            ]
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

            name=(
                "Relaxationsspannung"
            ),

            customdata=customdata,

            hovertemplate=(
                "Relaxationszeit: "
                "%{x:.1f} min"
                "<br>"
                "Spannung: %{y:.3f} V"
                "<br>"
                "Strom: %{customdata[0]:.3f} A"
                "<br>"
                "Spannungserholung: "
                "%{customdata[1]:.3f} V"
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
            maximum_time
            is not None
            and
            minute
            <=
            maximum_time
        ):
            figure.add_vline(
                x=minute,

                line_width=1,

                line_dash="dot",

                line_color=(
                    "#A5AEA0"
                ),

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


# ============================================================
# CELL PLOT
# ============================================================

def build_cell_plot(
    dataframe,
    selected_cells,
    phases,
):
    figure = go.Figure()

    x_values = get_time_axis(
        dataframe
    )

    if (
        "phase_label_de"
        in dataframe.columns
    ):
        phase_values = (
            dataframe[
                "phase_label_de"
            ]
            .astype(
                str
            )
            .to_numpy()
        )

    else:
        phase_values = (
            np.array(
                [
                    "–"
                ]
                *
                len(
                    dataframe
                )
            )
        )

    customdata = (
        np.column_stack(
            [
                phase_values
            ]
        )
    )

    for column in selected_cells:
        figure.add_trace(
            go.Scatter(
                x=x_values,

                y=dataframe[
                    column
                ],

                mode="lines",

                name=column,

                customdata=customdata,

                hovertemplate=(
                    "Zeit: %{x:.2f} h"
                    "<br>"
                    + column
                    + ": %{y:.4f} V"
                    "<br>"
                    "Phase: %{customdata[0]}"
                    "<extra></extra>"
                ),
            )
        )

    origin_s = None

    if (
        "timestamp_s"
        in dataframe.columns
        and
        not dataframe.empty
    ):
        origin_s = safe_float(
            dataframe[
                "timestamp_s"
            ].iloc[0]
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

        legend=dict(
            orientation="h",
            y=1.10,
        ),

        hovermode="closest",
    )

    return figure


# ============================================================
# CELL SPREAD PLOT
# ============================================================

def build_cell_spread_plot(
    dataframe,
):
    if (
        "cell_spread_mV"
        not in dataframe.columns
    ):
        return None

    if (
        "phase_label_de"
        in dataframe.columns
    ):
        phase_values = (
            dataframe[
                "phase_label_de"
            ]
            .astype(
                str
            )
            .to_numpy()
        )

    else:
        phase_values = (
            np.array(
                [
                    "–"
                ]
                *
                len(
                    dataframe
                )
            )
        )

    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=get_time_axis(
                dataframe
            ),

            y=dataframe[
                "cell_spread_mV"
            ],

            mode="lines",

            line=dict(
                color=UNI_GREEN,
                width=2,
            ),

            customdata=(
                phase_values
            ),

            hovertemplate=(
                "Zeit: %{x:.2f} h"
                "<br>"
                "Zellspannungsdifferenz: "
                "%{y:.2f} mV"
                "<br>"
                "Phase: %{customdata}"
                "<extra></extra>"
            ),
        )
    )

    figure.update_layout(
        height=380,

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
            "Zellspannungsdifferenz "
            "[mV]"
        ),

        showlegend=False,
    )

    return figure


# ============================================================
# COMPARISON PLOT
# ============================================================

def build_comparison_plot(
    dataframe,
    value_column,
    title,
    unit,
    decimals=2,
):
    data = (
        dataframe
        .dropna(
            subset=[
                "temperature_C",
                value_column,
            ]
        )
        .sort_values(
            "temperature_C"
        )
    )

    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=data[
                "temperature_C"
            ],

            y=data[
                value_column
            ],

            mode="lines+markers",

            line=dict(
                color=UNI_GREEN,
                width=2,
            ),

            marker=dict(
                size=9,
            ),

            hovertemplate=(
                "Temperatur: "
                "%{x:.0f} °C"
                "<br>"
                + title
                + ": %{y:."
                + str(
                    decimals
                )
                + "f} "
                + unit
                + "<extra></extra>"
            ),
        )
    )

    figure.update_layout(
        height=390,

        margin=dict(
            l=25,
            r=25,
            t=25,
            b=30,
        ),

        xaxis_title=(
            "Prüftemperatur [°C]"
        ),

        yaxis_title=(
            f"{title} [{unit}]"
        ),

        showlegend=False,
    )

    return figure


# ============================================================
# QUIZ
# ============================================================

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

    options = quiz.get(
        "options",
        [],
    )

    with st.form(
        key=(
            key_base
            + "_form"
        ),
        clear_on_submit=False,
    ):
        st.markdown(
            "**"
            +
            quiz.get(
                "question",
                "",
            )
            +
            "**"
        )

        selected = st.radio(
            "Antwort",

            options=options,

            index=None,

            key=(
                key_base
                + "_answer"
            ),

            label_visibility=(
                "collapsed"
            ),
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
            selected_index = (
                options.index(
                    selected
                )
            )

            is_correct = (
                selected_index
                ==
                quiz.get(
                    "correct_option"
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

                (
                    quiz.get(
                        "feedback_correct",
                        "Richtig.",
                    )
                    if is_correct
                    else
                    quiz.get(
                        "feedback_incorrect",
                        (
                            "Noch nicht "
                            "korrekt."
                        ),
                    )
                ),

                quiz.get(
                    "explanation"
                ),
            )

    result = (
        st.session_state.get(
            key_base
            + "_result"
        )
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
# REFLECTION
# ============================================================

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

    minimum = int(
        reflection.get(
            "minimum_input_characters",
            0,
        )
        or 0
    )

    with st.form(
        key=(
            key_base
            + "_form"
        ),
        clear_on_submit=False,
    ):
        answer = st.text_area(
            reflection.get(
                "prompt",
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
                "Bitte zuerst eine "
                "ausreichend ausführliche "
                "eigene Antwort formulieren."
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
            reflection.get(
                "model_answer",
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
# TRANSFER
# ============================================================

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

    options = task.get(
        "options",
        [],
    )

    with st.form(
        key=(
            key_base
            + "_form"
        ),
        clear_on_submit=False,
    ):
        st.markdown(
            "**"
            +
            task.get(
                "question",
                "",
            )
            +
            "**"
        )

        selected = st.radio(
            "Antwort",

            options=options,

            index=None,

            key=(
                key_base
                + "_answer"
            ),

            label_visibility=(
                "collapsed"
            ),
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
            selected_index = (
                options.index(
                    selected
                )
            )

            is_correct = (
                selected_index
                ==
                task.get(
                    "correct_option"
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

                (
                    "Richtig."
                    if is_correct
                    else
                    "Noch nicht ganz."
                ),

                task.get(
                    "explanation"
                ),
            )

    result = (
        st.session_state.get(
            key_base
            + "_result"
        )
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
# ANALYSIS TABLE HELPERS
# ============================================================

def format_analysis_table_value(
    value,
    unit="",
):
    if value is None:
        return "–"

    if isinstance(
        value,
        str,
    ):
        text = value.strip()

        if not text:
            return "–"

        numeric = safe_float(
            text
        )

        if numeric is None:
            return text

        value = numeric

    numeric = safe_float(
        value
    )

    if numeric is None:
        return str(
            value
        )

    if unit == "%":
        return format_number(
            numeric,
            4,
        )

    if unit == "mV/min":
        return format_number(
            numeric,
            4,
        )

    if unit == "mV":
        return format_number(
            numeric,
            3,
        )

    if unit in (
        "V",
        "A",
        "Ah",
        "Wh",
        "h",
        "s",
        "°C",
    ):
        return format_number(
            numeric,
            3,
        )

    if abs(
        numeric
        -
        round(
            numeric
        )
    ) < 1e-12:
        return str(
            int(
                round(
                    numeric
                )
            )
        )

    return format_number(
        numeric,
        3,
    )


def prepare_metric_summary_table(
    dataframe,
):
    if (
        dataframe is None
        or
        dataframe.empty
    ):
        return None

    display = (
        dataframe.copy()
    )

    if (
        "metric"
        in display.columns
    ):
        display[
            "metric"
        ] = (
            display[
                "metric"
            ]
            .fillna("")
            .astype(str)
        )

    if (
        "value"
        in display.columns
    ):
        if (
            "unit"
            in display.columns
        ):
            display[
                "value"
            ] = [
                format_analysis_table_value(
                    value,
                    unit,
                )

                for value, unit
                in zip(
                    display[
                        "value"
                    ],
                    display[
                        "unit"
                    ],
                )
            ]

        else:
            display[
                "value"
            ] = (
                display[
                    "value"
                ]
                .apply(
                    format_analysis_table_value
                )
            )

    display = (
        display.rename(
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

    return display


def prepare_validation_table(
    dataframe,
):
    if (
        dataframe is None
        or
        dataframe.empty
    ):
        return None

    display = (
        dataframe.copy()
    )

    if (
        "unit"
        in display.columns
    ):
        unit_series = (
            display[
                "unit"
            ]
        )

    else:
        unit_series = (
            [
                ""
            ]
            *
            len(
                display
            )
        )

    for column in (
        "python_value",
        "tester_value",
        "difference",
    ):
        if (
            column
            not in display.columns
        ):
            continue

        display[
            column
        ] = [
            format_analysis_table_value(
                value,
                unit,
            )

            for value, unit
            in zip(
                display[
                    column
                ],
                unit_series,
            )
        ]

    if (
        "error_pct"
        in display.columns
    ):
        display[
            "error_pct"
        ] = [
            format_analysis_table_value(
                value,
                "%",
            )

            for value
            in display[
                "error_pct"
            ]
        ]

    display = (
        display.rename(
            columns={
                "metric":
                    "Kennwert",

                "python_value":
                    "Python",

                "tester_value":
                    "Prüfstand",

                "difference":
                    "Differenz",

                "error_pct":
                    "Abweichung [%]",

                "unit":
                    "Einheit",
            }
        )
    )

    return display


def prepare_phase_table(
    dataframe,
):
    if (
        dataframe is None
        or
        dataframe.empty
    ):
        return None

    preferred_columns = [
        "event_number",
        "phase_label_de",
        "analysis_role",
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
        in dataframe.columns
    ]

    display = (
        dataframe[
            available_columns
        ]
        .copy()
    )

    for column in (
        "start_s",
        "end_s",
        "duration_s",
        "mean_current_A",
    ):
        if (
            column
            in display.columns
        ):
            display[
                column
            ] = (
                display[
                    column
                ]
                .apply(
                    lambda value:
                        format_number(
                            value,
                            3,
                        )
                )
            )

    display = (
        display.rename(
            columns={
                "event_number":
                    "Ereignis",

                "phase_label_de":
                    "Phase",

                "analysis_role":
                    "Analyse-Rolle",

                "start_s":
                    "Start [s]",

                "end_s":
                    "Ende [s]",

                "duration_s":
                    "Dauer [s]",

                "mean_current_A":
                    "Mittlerer Strom [A]",
            }
        )
    )

    return display


# ============================================================
# OCV INDEX
# ============================================================

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

    for item
    in tests
]


test_labels = {
    item[
        "test_id"
    ]:
        format_temperature(
            item.get(
                "temperature_C"
            )
        )

    for item
    in tests
}


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown(
        "---"
    )

    st.caption(
        "OCV Messung"
    )

    selected_test = (
        st.radio(
            "OCV Messung auswählen",

            options=test_ids,

            format_func=(
                lambda test_id:
                    test_labels.get(
                        test_id,
                        test_id,
                    )
            ),

            key=(
                "ocv_test_selector"
            ),

            label_visibility=(
                "collapsed"
            ),
        )
    )


# ============================================================
# LOAD BASIC TEST DATA
# ============================================================

bundle = load_ocv_test(
    selected_test,

    data_keys=[
        "electrical",
        "discharge",
        "relaxation",
        "cells",
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


manifest = (
    bundle.get(
        "manifest",
        {},
    )
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


comparison = (
    load_ocv_temperature_comparison()
)


comparison_learning = (
    load_ocv_comparison_learning()
    or {}
)


# ============================================================
# SUMMARY PARTS
# ============================================================

test_condition = (
    summary.get(
        "test_condition",
        {},
    )
)


discharge_summary = (
    summary.get(
        "discharge",
        {},
    )
)


relaxation_summary = (
    summary.get(
        "relaxation",
        {},
    )
)


cell_summary = (
    summary.get(
        "cells",
        {},
    )
)


module_summary = (
    summary.get(
        "module",
        {},
    )
)


validation = (
    summary.get(
        "validation",
        {},
    )
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


if number_of_cells <= 0:
    number_of_cells = len(
        get_cell_columns(
            cells
        )
    )


source_file = (
    summary.get(
        "source_file",
        "",
    )
)


if source_file:
    source_file = (
        Path(
            str(
                source_file
            )
        )
        .name
    )


# ============================================================
# HEADER
# ============================================================

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
        f" · {number_of_cells} "
        f"Zellen Modul"
    )


if source_file:
    metadata_text += (
        " · "
        +
        source_file
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
        Gleichgewichts-OCV gleichgesetzt. Der relative
        Entladefortschritt ist eine messungsbezogene Größe
        und kein absolut kalibrierter SOC.
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# CENTRAL KPIs
# ============================================================

energy_Wh = safe_float(
    discharge_summary.get(
        "energy_Wh"
    )
)


energy_kWh = (
    energy_Wh
    /
    1000.0

    if energy_Wh
    is not None

    else None
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


# ============================================================
# KPI EXPLANATIONS
# ============================================================

with st.expander(
    "Was bedeuten diese Kennwerte?"
):
    kpi_items = [
        (
            "Prüftemperatur",
            "test_temperature_C",
        ),

        (
            "Entnommene Ladung",
            "discharge_capacity_Ah",
        ),

        (
            "Entnommene Energie",
            "discharge_energy_Wh",
        ),

        (
            "Spannungserholung",
            "total_recovery_V",
        ),

        (
            "Entladedauer",
            "discharge_duration_h",
        ),
    ]

    for (
        title,
        key,
    ) in kpi_items:

        explanation = (
            get_kpi_explanation(
                learning,
                key,
            )
        )

        if not explanation:
            continue

        st.markdown(
            "**"
            +
            title
            +
            "**"
        )

        short = (
            explanation.get(
                "short"
            )
        )

        if short:
            st.write(
                short
            )

        formula = (
            explanation.get(
                "formula"
            )
        )

        if formula:
            st.caption(
                "Formel: "
                +
                formula
            )

        interpretation = (
            explanation.get(
                "interpretation"
            )
        )

        if interpretation:
            st.caption(
                interpretation
            )


st.divider()


# ============================================================
# MAIN NAVIGATION
# ============================================================

section = section_selector(
    [
        "Versuchsphasen",
        "Entladung",
        "Relaxation",
        "Zellen",
        "Vergleich",
        "Lernen",
        "Analyse",
    ],

    key=(
        "ocv_main_section"
    ),
)


st.divider()


# ============================================================
# VERSUCHSPHASEN
# ============================================================

if section == "Versuchsphasen":
    st.subheader(
        "Versuchsphasen"
    )

    if (
        electrical is None
        or
        electrical.empty
    ):
        st.warning(
            "Für diesen Test sind keine "
            "elektrischen Visualisierungsdaten "
            "verfügbar."
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
                build_voltage_current_plot(
                    electrical,
                    phases,
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

    if (
        phases is not None
        and
        not phases.empty
    ):
        with st.expander(
            "Erkannte Versuchsphasen anzeigen"
        ):
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


# ============================================================
# ENTLADUNG
# ============================================================

elif section == "Entladung":
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

    if (
        discharge is None
        or
        discharge.empty
    ):
        st.warning(
            "Keine exportierten "
            "Entladedaten verfügbar."
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
                build_discharge_plot(
                    discharge
                ),
                use_container_width=True,
            )

        with info_col:
            render_graph_explanation(
                get_graph_explanation(
                    learning,
                    "voltage_relative_discharge",
                )
            )


# ============================================================
# RELAXATION
# ============================================================

elif section == "Relaxation":
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
        relaxation is None
        or
        relaxation.empty
    ):
        st.warning(
            "Keine exportierten "
            "Relaxationsdaten verfügbar."
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
                build_relaxation_plot(
                    relaxation
                ),
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
            "### Gemeinsame Relaxationszeitpunkte"
        )

        c1, c2, c3, c4 = (
            st.columns(4)
        )

        checkpoints = [
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
        ) in checkpoints:

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


# ============================================================
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
    ):
        st.info(
            "Für diesen Test sind keine "
            "Einzelzellspannungen verfügbar."
        )

    else:
        cell_columns = (
            get_cell_columns(
                cells
            )
        )

        if not cell_columns:
            st.info(
                "Es wurden keine normalisierten "
                "Zellspannungssignale gefunden."
            )

        else:
            default_cells = list(
                cell_columns[
                    :
                    min(
                        3,
                        len(
                            cell_columns
                        ),
                    )
                ]
            )

            lowest_cell = (
                cell_summary.get(
                    "lowest_cell"
                )
            )

            if (
                lowest_cell
                in cell_columns
                and
                lowest_cell
                not in default_cells
            ):
                default_cells.append(
                    lowest_cell
                )

            selected_cells = (
                st.multiselect(
                    "Zellen auswählen",

                    options=(
                        cell_columns
                    ),

                    default=(
                        default_cells
                    ),

                    key=(
                        "ocv_cell_selector_"
                        +
                        selected_test
                    ),
                )
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
                        build_cell_plot(
                            cells,
                            selected_cells,
                            phases,
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
                    "Bitte mindestens "
                    "eine Zelle auswählen."
                )

            cell_k1, cell_k2 = (
                st.columns(2)
            )

            with cell_k1:
                render_metric(
                    "Niedrigste Zellspannung",

                    metric_text(
                        cell_summary.get(
                            "lowest_cell_voltage_V"
                        ),
                        "V",
                        4,
                    ),

                    get_kpi_explanation(
                        learning,
                        "lowest_cell_voltage_V",
                    ),
                )

                if lowest_cell:
                    st.caption(
                        "Betroffene Zelle: "
                        +
                        str(
                            lowest_cell
                        )
                    )

            with cell_k2:
                if number_of_cells > 1:
                    render_metric(
                        "Maximale "
                        "Zellspannungsdifferenz",

                        metric_text(
                            cell_summary.get(
                                "maximum_spread_discharge_mV"
                            ),
                            "mV",
                            2,
                        ),

                        get_kpi_explanation(
                            learning,
                            "maximum_cell_spread_discharge_mV",
                        ),
                    )

            if (
                number_of_cells > 1
                and
                "cell_spread_mV"
                in cells.columns
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
                        build_cell_spread_plot(
                            cells
                        ),
                        use_container_width=True,
                    )

                with info_col:
                    render_graph_explanation(
                        get_graph_explanation(
                            learning,
                            "cell_spread",
                        )
                    )


# ============================================================
# VERGLEICH
# ============================================================

elif section == "Vergleich":
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
        or
        comparison.empty
    ):
        st.warning(
            "Keine Vergleichsdaten verfügbar."
        )

    else:
        comparison_data = (
            comparison.copy()
        )

        if (
            "discharge_energy_Wh"
            in comparison_data.columns
        ):
            comparison_data[
                "discharge_energy_kWh"
            ] = (
                comparison_data[
                    "discharge_energy_Wh"
                ]
                /
                1000.0
            )

        left, right = (
            st.columns(2)
        )

        with left:
            st.markdown(
                "#### Entnommene Ladung"
            )

            if (
                "discharge_capacity_Ah"
                in comparison_data.columns
            ):
                st.plotly_chart(
                    build_comparison_plot(
                        comparison_data,
                        "discharge_capacity_Ah",
                        "Entnommene Ladung",
                        "Ah",
                        2,
                    ),
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

            if (
                "discharge_energy_kWh"
                in comparison_data.columns
            ):
                st.plotly_chart(
                    build_comparison_plot(
                        comparison_data,
                        "discharge_energy_kWh",
                        "Entnommene Energie",
                        "kWh",
                        2,
                    ),
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

            if (
                "total_recovery_V"
                in comparison_data.columns
            ):
                st.plotly_chart(
                    build_comparison_plot(
                        comparison_data,
                        "total_recovery_V",
                        "Spannungserholung",
                        "V",
                        3,
                    ),
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

            if (
                "relaxation_60min_V"
                in comparison_data.columns
            ):
                st.plotly_chart(
                    build_comparison_plot(
                        comparison_data,
                        "relaxation_60min_V",
                        "Spannung nach 60 min",
                        "V",
                        3,
                    ),
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


# ============================================================
# LERNEN
# ============================================================

elif section == "Lernen":
    st.subheader(
        "Lernmodus"
    )

    learning_scope = (
        section_selector(
            [
                "Aktueller Versuch",
                "Temperaturvergleich",
            ],
            key=(
                "ocv_learning_scope"
            ),
        )
    )

    if (
        learning_scope
        ==
        "Aktueller Versuch"
    ):
        active_learning = (
            learning
        )

        learning_prefix = (
            "ocv_"
            +
            selected_test
        )

    else:
        active_learning = (
            comparison_learning
        )

        learning_prefix = (
            "ocv_comparison"
        )

    objectives = (
        active_learning.get(
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
                +
                objective.get(
                    "text",
                    "",
                )
            )

    theory = (
        active_learning.get(
            "theory",
            [],
        )
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

                formula = (
                    item.get(
                        "formula"
                    )
                )

                if formula:
                    st.caption(
                        "Formel: "
                        +
                        formula
                    )

    quizzes = (
        active_learning.get(
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
                    learning_prefix,
                )

    reflections = (
        active_learning.get(
            "reflections",
            [],
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
                    learning_prefix,
                )

    transfer_tasks = (
        active_learning.get(
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
                    learning_prefix,
                )


# ============================================================
# ANALYSE
# ============================================================

elif section == "Analyse":
    st.subheader(
        "Erweiterte Analyse"
    )

    st.write(
        "Hier werden die Phasenerkennung, die "
        "Kennwerte der Hauptentladung und "
        "Relaxation, Zell- und Temperaturkennwerte "
        "sowie die Prüfstandsvalidierung technisch "
        "nachvollziehbar dargestellt."
    )

    # --------------------------------------------------------
    # Load extra analysis tables only here.
    # This avoids unnecessary loading in the normal
    # visualization and learning sections.
    # --------------------------------------------------------

    analysis_bundle = (
        load_ocv_test(
            selected_test,

            data_keys=[
                "discharge_summary",
                "relaxation_summary",
                "cell_summary",
                "temperature_summary",
                "validation",
                "phase_quality",
            ],
        )
    )

    discharge_summary_table = (
        analysis_bundle.get(
            "discharge_summary"
        )
    )

    relaxation_summary_table = (
        analysis_bundle.get(
            "relaxation_summary"
        )
    )

    cell_summary_table = (
        analysis_bundle.get(
            "cell_summary"
        )
    )

    temperature_summary_table = (
        analysis_bundle.get(
            "temperature_summary"
        )
    )

    validation_table = (
        analysis_bundle.get(
            "validation"
        )
    )

    phase_quality_table = (
        analysis_bundle.get(
            "phase_quality"
        )
    )

    # --------------------------------------------------------
    # BERECHNUNGSGRUNDLAGEN
    # --------------------------------------------------------

    st.markdown(
        "### Berechnungsgrundlagen"
    )

    st.latex(
        r"""
        Q_\mathrm{dis}
        =
        -\frac{1}{3600}
        \int I(t)\,\mathrm{d}t
        """
    )

    st.latex(
        r"""
        E_\mathrm{dis}
        =
        -\frac{1}{3600}
        \int U(t)I(t)\,\mathrm{d}t
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

    if number_of_cells > 1:
        st.latex(
            r"""
            \Delta V_\mathrm{cell}(t)
            =
            V_\mathrm{cell,max}(t)
            -
            V_\mathrm{cell,min}(t)
            """
        )

    # --------------------------------------------------------
    # PHASENÜBERSICHT
    # --------------------------------------------------------

    st.markdown(
        "### Phasenübersicht"
    )

    st.caption(
        "Die Tabelle zeigt die im OCV Versuch "
        "erkannten Ereignisse. Hauptentladung und "
        "anschließende Relaxation werden für die "
        "weiteren Kennwerte gezielt ausgewählt."
    )

    phase_table = (
        prepare_phase_table(
            phases
        )
    )

    if phase_table is None:
        st.info(
            "Keine Phasentabelle verfügbar."
        )

    else:
        st.dataframe(
            phase_table,
            use_container_width=True,
            hide_index=True,
        )

    # --------------------------------------------------------
    # ENTLADUNGSKENNWERTE
    # --------------------------------------------------------

    st.markdown(
        "### Entladekennwerte"
    )

    st.caption(
        "Kennwerte der automatisch ausgewählten "
        "Hauptentladung. Die Kapazitäts- und "
        "Energieberechnung verwendet die vollständigen "
        "Messdaten und die nativen Zeitstempel."
    )

    display_discharge = (
        prepare_metric_summary_table(
            discharge_summary_table
        )
    )

    if display_discharge is None:
        st.info(
            "Keine exportierte Tabelle mit "
            "Entladekennwerten verfügbar."
        )

    else:
        st.dataframe(
            display_discharge,
            use_container_width=True,
            hide_index=True,
        )

    # --------------------------------------------------------
    # RELAXATIONSKENNWERTE
    # --------------------------------------------------------

    st.markdown(
        "### Relaxationskennwerte"
    )

    st.caption(
        "Die Relaxation wird nach dem Ende der "
        "Hauptentladung ausgewertet. Neben der "
        "sofortigen und weiteren Spannungserholung "
        "werden gemeinsame Zeitpunkte bei 1, 10, "
        "30 und 60 Minuten betrachtet."
    )

    display_relaxation = (
        prepare_metric_summary_table(
            relaxation_summary_table
        )
    )

    if display_relaxation is None:
        st.info(
            "Keine exportierte Tabelle mit "
            "Relaxationskennwerten verfügbar."
        )

    else:
        st.dataframe(
            display_relaxation,
            use_container_width=True,
            hide_index=True,
        )

    # --------------------------------------------------------
    # ZELLKENNWERTE
    # --------------------------------------------------------

    st.markdown(
        "### Zellkennwerte"
    )

    display_cells = (
        prepare_metric_summary_table(
            cell_summary_table
        )
    )

    if display_cells is None:
        st.info(
            "Keine exportierte Tabelle mit "
            "Zellkennwerten verfügbar."
        )

    else:
        st.dataframe(
            display_cells,
            use_container_width=True,
            hide_index=True,
        )

    # --------------------------------------------------------
    # TEMPERATURKENNWERTE
    # --------------------------------------------------------

    st.markdown(
        "### Temperaturkennwerte"
    )

    st.caption(
        "Die Temperaturtabelle beschreibt die "
        "gemessene Prüfbedingung sowie das thermische "
        "Verhalten während Hauptentladung und "
        "anschließender Relaxation."
    )

    display_temperature = (
        prepare_metric_summary_table(
            temperature_summary_table
        )
    )

    if display_temperature is None:
        st.info(
            "Keine exportierte Tabelle mit "
            "Temperaturkennwerten verfügbar."
        )

    else:
        st.dataframe(
            display_temperature,
            use_container_width=True,
            hide_index=True,
        )

    # --------------------------------------------------------
    # PRÜFSTANDSVALIDIERUNG
    # --------------------------------------------------------

    st.markdown(
        "### Prüfstandsvalidierung"
    )

    st.write(
        "Die Python Ergebnisse werden nach der "
        "Berechnung mit den gespeicherten "
        "Prüfstandswerten verglichen. Die "
        "Prüfstandswerte beeinflussen die "
        "Python-KPI-Berechnung nicht."
    )

    display_validation = (
        prepare_validation_table(
            validation_table
        )
    )

    if display_validation is None:
        st.info(
            "Keine exportierte "
            "Prüfstandsvalidierung verfügbar."
        )

    else:
        st.dataframe(
            display_validation,
            use_container_width=True,
            hide_index=True,
        )

    # --------------------------------------------------------
    # PHASENQUALITÄT
    # --------------------------------------------------------

    st.markdown(
        "### Qualitätsprüfung der Phasenerkennung"
    )

    st.caption(
        "Diese Kennwerte unterstützen die Prüfung, "
        "ob die erkannte Ruhephase tatsächlich direkt "
        "auf die Hauptentladung folgt und für die "
        "Relaxationsauswertung geeignet ist."
    )

    display_phase_quality = (
        prepare_metric_summary_table(
            phase_quality_table
        )
    )

    if display_phase_quality is None:
        st.info(
            "Keine exportierte Qualitätsprüfung "
            "der Phasenerkennung verfügbar."
        )

    else:
        st.dataframe(
            display_phase_quality,
            use_container_width=True,
            hide_index=True,
        )

    # --------------------------------------------------------
    # DATENBASIS
    # --------------------------------------------------------

    st.markdown(
        "### Datenbasis des Dashboards"
    )

    st.write(
        "Das Dashboard greift ausschließlich auf die "
        "bereits aufbereiteten CSV- und JSON-Dateien zu. "
        "Die Berechnung der Kennwerte erfolgt vor dem "
        "Dashboard in der Python-basierten Analysepipeline."
    )

    analysis_info = (
        manifest.get(
            "analysis",
            {},
        )
    )

    def status_text(value):
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
                    "Phasenerkennung**"
                )

                st.caption(
                    status_text(
                        analysis_info.get(
                            "event_based_phase_detection"
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
            Phasenerkennung und analytische Berechnung
            verwendet. Erst anschließend werden reduzierte
            Visualisierungsdaten für das Dashboard exportiert.
            Die Tabellen im Analysebereich enthalten bereits
            berechnete Ergebnisse; Streamlit berechnet diese
            Kennwerte nicht erneut.
        </div>
        """,
        unsafe_allow_html=True,
    )