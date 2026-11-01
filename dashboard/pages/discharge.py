from pathlib import Path
import html
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from data_loader import (
    load_discharge_index,
    load_discharge_test,
    load_discharge_temperature_comparison,
    load_discharge_comparison_learning,
)


UNI_GREEN = "#6F9512"
DARK_GREY = "#59636E"

CELL_RE = re.compile(
    r"^cell_\d+_V$"
)


# ============================================================
# BASIC HELPERS
# ============================================================


def safe_float(value):
    try:
        value = float(value)

    except (
        TypeError,
        ValueError,
    ):
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

    if not unit:
        return number

    return (
        f"{number} {unit}"
    )


def format_temperature(
    value,
):
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


def get_graph_explanation(
    learning,
    graph_id,
):
    if not learning:
        return None

    explanations = (
        learning.get(
            "graph_explanations",
            [],
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
    learning,
    kpi_id,
):
    if not learning:
        return None

    return (
        learning
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
    Display the graph explanation as one continuous
    text inside a compact information box.
    """

    if not explanation:
        return

    text_parts = []

    what = explanation.get(
        "what"
    )

    focus = explanation.get(
        "focus"
    )

    interpretation = explanation.get(
        "interpretation"
    )

    if what:
        text_parts.append(
            str(what).strip()
        )

    if focus:
        text_parts.append(
            str(focus).strip()
        )

    if interpretation:
        text_parts.append(
            str(interpretation).strip()
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

    return sorted(
        column

        for column
        in dataframe.columns

        if CELL_RE.fullmatch(
            column
        )
    )


def cell_label(
    column,
):
    match = re.search(
        r"cell_(\d+)_V",
        str(
            column
        ),
    )

    if not match:
        return str(
            column
        )

    return (
        f"Zelle "
        f"{int(match.group(1))}"
    )


def get_temperature_columns(
    dataframe,
):
    if dataframe is None:
        return []

    columns = []

    for column in dataframe.columns:

        name = column.lower()

        if column in (
            "timestamp_s",
            "experiment_time_h",
            "cycle_id",
        ):
            continue

        if (
            "temp" not in name
            and
            "temperature" not in name
        ):
            continue

        if any(
            word in name

            for word in (
                "spread",
                "delta",
                "minimum",
                "maximum",
            )
        ):
            continue

        columns.append(
            column
        )

    return columns


def temperature_label(
    column,
):
    name = str(
        column
    ).lower()

    if (
        "climate" in name
        or
        "clima" in name
    ):
        return (
            "Klimatemperatur"
        )

    match = re.search(
        r"(\d+)",
        str(
            column
        ),
    )

    if match:

        return (
            f"Temperatur "
            f"{int(match.group(1))}"
        )

    return str(
        column
    )


def section_selector(
    options,
    key,
):
    """
    Only one large dashboard section is rendered
    at a time.

    This keeps the page faster than rendering every
    Plotly graph simultaneously inside st.tabs().
    """

    segmented_control = getattr(
        st,
        "segmented_control",
        None,
    )

    if segmented_control is not None:

        selected = (
            segmented_control(
                "Bereich",
                options=options,
                default=options[0],
                key=key,
                label_visibility=(
                    "collapsed"
                ),
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
        label_visibility=(
            "collapsed"
        ),
    )


def time_axis(
    dataframe,
):
    if (
        "experiment_time_h"
        in dataframe.columns
    ):
        return (
            dataframe[
                "experiment_time_h"
            ]
        )

    if (
        "timestamp_s"
        in dataframe.columns
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

    return pd.Series(
        np.arange(
            len(
                dataframe
            )
        ),
        index=(
            dataframe.index
        ),
    )


# ============================================================
# PLOT:
# VOLTAGE + CURRENT
# ============================================================


def voltage_current_plot(
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

    x_values = time_axis(
        dataframe
    )

    if (
        "phase_label_de"
        in dataframe.columns
    ):
        phases = (
            dataframe[
                "phase_label_de"
            ]
        )

    else:
        phases = pd.Series(
            ["–"] * len(dataframe),
            index=dataframe.index,
        )

    if (
        "cycle_id"
        in dataframe.columns
    ):
        cycles = (
            dataframe[
                "cycle_id"
            ]
        )

    else:
        cycles = pd.Series(
            [np.nan] * len(dataframe),
            index=dataframe.index,
        )

    customdata = (
        np.column_stack(
            [
                phases,
                cycles,
            ]
        )
    )

    figure.add_trace(
        go.Scatter(
            x=x_values,
            y=dataframe[
                "voltage_V"
            ],
            mode="lines",
            name="Spannung",
            line=dict(
                color=UNI_GREEN,
                width=2,
            ),
            customdata=(
                customdata
            ),
            hovertemplate=(
                "Zeit: %{x:.2f} h"
                "<br>"
                "Spannung: %{y:.3f} V"
                "<br>"
                "Phase: %{customdata[0]}"
                "<br>"
                "Zyklus: %{customdata[1]}"
                "<extra></extra>"
            ),
        ),
        secondary_y=False,
    )

    figure.add_trace(
        go.Scatter(
            x=x_values,
            y=dataframe[
                "current_A"
            ],
            mode="lines",
            name="Strom",
            line=dict(
                color=DARK_GREY,
                width=1.3,
            ),
            customdata=(
                customdata
            ),
            hovertemplate=(
                "Zeit: %{x:.2f} h"
                "<br>"
                "Strom: %{y:.2f} A"
                "<br>"
                "Phase: %{customdata[0]}"
                "<br>"
                "Zyklus: %{customdata[1]}"
                "<extra></extra>"
            ),
        ),
        secondary_y=True,
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
# PLOT:
# END VOLTAGE VS DISCHARGE PROGRESS
# ============================================================


def cycle_voltage_plot(
    dataframe,
):
    data = (
        dataframe
        .dropna(
            subset=[
                "relative_discharge_progress_pct",
                "main_discharge_end_voltage_V",
            ]
        )
        .copy()
    )

    removed_charge = (
        data.get(
            "removed_charge_at_diagnostic_Ah",
            pd.Series(
                [np.nan] * len(data),
                index=data.index,
            ),
        )
    )

    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=data[
                "relative_discharge_progress_pct"
            ],
            y=data[
                "main_discharge_end_voltage_V"
            ],
            mode=(
                "lines+markers"
            ),
            line=dict(
                color=UNI_GREEN,
                width=2,
            ),
            marker=dict(
                size=8
            ),
            customdata=(
                np.column_stack(
                    [
                        data[
                            "cycle_id"
                        ],
                        removed_charge,
                    ]
                )
            ),
            hovertemplate=(
                "Entladefortschritt: "
                "%{x:.1f} %"
                "<br>"
                "Endspannung: "
                "%{y:.3f} V"
                "<br>"
                "Zyklus: "
                "%{customdata[0]}"
                "<br>"
                "Entnommene Ladung: "
                "%{customdata[1]:.2f} Ah"
                "<extra></extra>"
            ),
        )
    )

    figure.update_layout(
        height=410,
        margin=dict(
            l=25,
            r=25,
            t=25,
            b=30,
        ),
        xaxis_title=(
            "Relativer "
            "Entladefortschritt [%]"
        ),
        yaxis_title=(
            "Modulspannung [V]"
        ),
        showlegend=False,
    )

    return figure


# ============================================================
# PLOT:
# VOLTAGE RECOVERY
# ============================================================


def recovery_plot(
    dataframe,
):
    data = (
        dataframe
        .dropna(
            subset=[
                "relative_discharge_progress_pct",
                "total_voltage_recovery_V",
            ]
        )
        .copy()
    )

    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=data[
                "relative_discharge_progress_pct"
            ],
            y=data[
                "total_voltage_recovery_V"
            ],
            mode="lines+markers",
            line=dict(
                color=UNI_GREEN,
                width=2,
            ),
            marker=dict(
                size=8
            ),
            customdata=(
                data[
                    [
                        "cycle_id"
                    ]
                ]
            ),
            hovertemplate=(
                "Entladefortschritt: "
                "%{x:.1f} %"
                "<br>"
                "Spannungserholung: "
                "%{y:.3f} V"
                "<br>"
                "Zyklus: "
                "%{customdata[0]}"
                "<extra></extra>"
            ),
        )
    )

    figure.update_layout(
        height=410,
        margin=dict(
            l=25,
            r=25,
            t=25,
            b=30,
        ),
        xaxis_title=(
            "Relativer "
            "Entladefortschritt [%]"
        ),
        yaxis_title=(
            "Spannungserholung [V]"
        ),
        showlegend=False,
    )

    return figure


# ============================================================
# PLOT:
# PULSE RESISTANCE
# ============================================================


def resistance_plot(
    dataframe,
):
    figure = go.Figure()

    resistance_columns = [
        (
            "dch_pulse_R_0p1s_mOhm",
            "0,1 s",
        ),
        (
            "dch_pulse_R_2s_mOhm",
            "2 s",
        ),
        (
            "dch_pulse_R_10s_mOhm",
            "10 s",
        ),
        (
            "dch_pulse_R_18s_mOhm",
            "18 s",
        ),
    ]

    for (
        column,
        label,
    ) in resistance_columns:

        if (
            column
            not in dataframe.columns
        ):
            continue

        data = (
            dataframe
            .dropna(
                subset=[
                    "relative_discharge_progress_pct",
                    column,
                ]
            )
        )

        figure.add_trace(
            go.Scatter(
                x=data[
                    "relative_discharge_progress_pct"
                ],
                y=data[
                    column
                ],
                mode=(
                    "lines+markers"
                ),
                name=label,
                customdata=(
                    data[
                        [
                            "cycle_id"
                        ]
                    ]
                ),
                hovertemplate=(
                    "Entladefortschritt: "
                    "%{x:.1f} %"
                    "<br>"
                    "Widerstand: "
                    "%{y:.3f} mΩ"
                    "<br>"
                    "Zyklus: "
                    "%{customdata[0]}"
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
            b=30,
        ),
        xaxis_title=(
            "Relativer "
            "Entladefortschritt [%]"
        ),
        yaxis_title=(
            "Pulswiderstand [mΩ]"
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


def cell_plot(
    dataframe,
    selected_cells,
):
    figure = go.Figure()

    x_values = time_axis(
        dataframe
    )

    for column in selected_cells:

        figure.add_trace(
            go.Scatter(
                x=x_values,
                y=dataframe[
                    column
                ],
                mode="lines",
                name=(
                    cell_label(
                        column
                    )
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


def cell_spread_plot(
    dataframe,
):
    if (
        "cell_spread_mV"
        not in dataframe.columns
    ):
        return None

    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=time_axis(
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
            hovertemplate=(
                "Zeit: %{x:.2f} h"
                "<br>"
                "Differenz: %{y:.2f} mV"
                "<extra></extra>"
            ),
        )
    )

    figure.update_layout(
        height=400,
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


# ============================================================
# PLOT:
# TEMPERATURE
# ============================================================


def temperature_plot(
    dataframe,
):
    figure = go.Figure()

    x_values = time_axis(
        dataframe
    )

    for column in (
        get_temperature_columns(
            dataframe
        )
    ):

        figure.add_trace(
            go.Scatter(
                x=x_values,
                y=dataframe[
                    column
                ],
                mode="lines",
                name=(
                    temperature_label(
                        column
                    )
                ),
                hovertemplate=(
                    "Zeit: %{x:.2f} h"
                    "<br>"
                    "Temperatur: "
                    "%{y:.2f} °C"
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
            b=30,
        ),
        xaxis_title=(
            "Versuchszeit [h]"
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
# EIS PLOTS
# ============================================================


def nyquist_plot(
    dataframe,
    scale_factor,
    impedance_unit,
):
    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=(
                dataframe[
                    "z_real"
                ]
                *
                scale_factor
            ),
            y=(
                dataframe[
                    "nyquist_imag"
                ]
                *
                scale_factor
            ),
            mode=(
                "lines+markers"
            ),
            line=dict(
                color=UNI_GREEN,
                width=2,
            ),
            marker=dict(
                size=7
            ),
            customdata=(
                np.column_stack(
                    [
                        dataframe[
                            "frequency_Hz"
                        ],
                        (
                            dataframe[
                                "z_magnitude"
                            ]
                            *
                            scale_factor
                        ),
                        dataframe[
                            "phase_deg"
                        ],
                    ]
                )
            ),
            hovertemplate=(
                "Z': %{x:.4f} "
                + impedance_unit
                + "<br>"
                "-Z'': %{y:.4f} "
                + impedance_unit
                + "<br>"
                "Frequenz: "
                "%{customdata[0]:.3g} Hz"
                + "<br>"
                "|Z|: "
                "%{customdata[1]:.4f} "
                + impedance_unit
                + "<br>"
                "Phase: "
                "%{customdata[2]:.2f}°"
                + "<extra></extra>"
            ),
        )
    )

    figure.update_layout(
        height=470,
        margin=dict(
            l=25,
            r=25,
            t=30,
            b=30,
        ),
        xaxis_title=(
            f"Z' "
            f"[{impedance_unit}]"
        ),
        yaxis_title=(
            f"-Z'' "
            f"[{impedance_unit}]"
        ),
        showlegend=False,
    )

    return figure


def bode_magnitude_plot(
    dataframe,
    scale_factor,
    impedance_unit,
):
    data = (
        dataframe
        .sort_values(
            "frequency_Hz"
        )
    )

    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=data[
                "frequency_Hz"
            ],
            y=(
                data[
                    "z_magnitude"
                ]
                *
                scale_factor
            ),
            mode=(
                "lines+markers"
            ),
            line=dict(
                color=UNI_GREEN,
                width=2,
            ),
            marker=dict(
                size=6
            ),
            hovertemplate=(
                "Frequenz: "
                "%{x:.3g} Hz"
                "<br>"
                "|Z|: %{y:.4f} "
                + impedance_unit
                + "<extra></extra>"
            ),
        )
    )

    figure.update_xaxes(
        type="log",
        title_text=(
            "Frequenz [Hz]"
        ),
    )

    figure.update_yaxes(
        title_text=(
            f"|Z| "
            f"[{impedance_unit}]"
        )
    )

    figure.update_layout(
        height=420,
        margin=dict(
            l=25,
            r=25,
            t=30,
            b=30,
        ),
        showlegend=False,
    )

    return figure


def bode_phase_plot(
    dataframe,
):
    data = (
        dataframe
        .sort_values(
            "frequency_Hz"
        )
    )

    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=data[
                "frequency_Hz"
            ],
            y=data[
                "phase_deg"
            ],
            mode=(
                "lines+markers"
            ),
            line=dict(
                color=UNI_GREEN,
                width=2,
            ),
            marker=dict(
                size=6
            ),
            hovertemplate=(
                "Frequenz: "
                "%{x:.3g} Hz"
                "<br>"
                "Phase: %{y:.2f}°"
                "<extra></extra>"
            ),
        )
    )

    figure.update_xaxes(
        type="log",
        title_text=(
            "Frequenz [Hz]"
        ),
    )

    figure.update_yaxes(
        title_text=(
            "Phase [°]"
        )
    )

    figure.update_layout(
        height=420,
        margin=dict(
            l=25,
            r=25,
            t=30,
            b=30,
        ),
        showlegend=False,
    )

    return figure


# ============================================================
# COMPARISON PLOT
# ============================================================


def comparison_plot(
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
            mode=(
                "lines+markers"
            ),
            line=dict(
                color=UNI_GREEN,
                width=2,
            ),
            marker=dict(
                size=9
            ),
            hovertemplate=(
                "Temperatur: "
                "%{x:.0f} °C"
                "<br>"
                + title
                + ": %{y:."
                + str(decimals)
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
# LEARNING INTERACTIONS
#
# IMPORTANT:
# Widgets are inside st.form().
#
# Therefore typing in text fields does NOT trigger a complete
# Streamlit rerun after every edit.
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

            correct_option = (
                quiz.get(
                    "correct_option"
                )
            )

            selected_index = (
                options.index(
                    selected
                )
            )

            is_correct = (
                selected_index
                ==
                correct_option
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
                    else quiz.get(
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
        f"{prefix}_"
        f"{reflection_id}"
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


def render_transfer(
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

    options = task.get(
        "options",
        [],
    )

    scenario = task.get(
        "scenario"
    )

    if scenario:

        st.caption(
            scenario
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
            + task.get(
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

            correct_option = (
                task.get(
                    "correct_option"
                )
            )

            selected_index = (
                options.index(
                    selected
                )
            )

            is_correct = (
                selected_index
                ==
                correct_option
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
                    else (
                        "Noch nicht ganz."
                    )
                ),
                task.get(
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
# LOAD AVAILABLE DISCHARGE TESTS
# ============================================================


index = load_discharge_index(
    required=False
)

tests = index.get(
    "tests",
    [],
)


if not tests:

    st.title(
        "Entladung & EIS"
    )

    st.warning(
        "Es sind noch keine "
        "exportierten Entladungsdaten "
        "verfügbar."
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
        format_temperature(
            item.get(
                "temperature_C"
            )
        )

    for item in tests
}


# ============================================================
# SIDEBAR TEST SELECTOR
# ============================================================


with st.sidebar:

    st.markdown(
        "---"
    )

    st.caption(
        "Entladungsmessung"
    )

    selected_test = st.radio(
        "Entladungsmessung auswählen",
        options=test_ids,
        format_func=(
            lambda test_id:
                test_labels.get(
                    test_id,
                    test_id,
                )
        ),
        key=(
            "discharge_test_selector"
        ),
        label_visibility=(
            "collapsed"
        ),
    )


# ============================================================
# LOAD SELECTED TEST
# ============================================================


bundle = load_discharge_test(
    selected_test,
    data_keys=[
        "electrical",
        "cycles",
        "resistance",
        "cells",
        "temperature",
        "phases",
        "diagnostic_cycles",
        "eis_points",
        "eis_scan",
        "validation",
        "validation_summary",
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

cycles = bundle.get(
    "cycles"
)

resistance = bundle.get(
    "resistance"
)

cells = bundle.get(
    "cells"
)

temperature = bundle.get(
    "temperature"
)

phases = bundle.get(
    "phases"
)

diagnostic_cycles = (
    bundle.get(
        "diagnostic_cycles"
    )
)

eis_points = bundle.get(
    "eis_points"
)

eis_scan = bundle.get(
    "eis_scan"
)

validation = bundle.get(
    "validation"
)

validation_summary = (
    bundle.get(
        "validation_summary"
    )
)


comparison = (
    load_discharge_temperature_comparison()
)

comparison_learning = (
    load_discharge_comparison_learning()
    or {}
)


# ============================================================
# BASIC METADATA
# ============================================================


test_temperature = safe_float(
    summary.get(
        "temperature_C"
    )
)


if test_temperature is None:

    test_temperature = (
        safe_float(
            summary.get(
                "mean_climate_temperature_C"
            )
        )
    )


number_of_cells = int(
    summary.get(
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


source_file = summary.get(
    "source_file",
    "",
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
    "Entladung & EIS"
)


st.write(
    "Analyse des dynamischen Entladeverhaltens, "
    "der diagnostischen Pulswiderstände, der "
    "Zell- und Temperaturverläufe sowie der "
    "elektrochemischen Impedanzspektroskopie."
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
        f" · "
        f"{number_of_cells} "
        f"Zellen Modul"
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
        EIS ist Bestandteil der Entladungsanalyse.
        Die Rohwerte von Zre und Zim bleiben
        unverändert; im Nyquist-Diagramm wird
        -Z'' dargestellt. Der relative
        Entladefortschritt ist eine messungsbezogene
        Größe und kein absolut kalibrierter SOC.
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# CENTRAL KPIs
# ============================================================


energy_Wh = safe_float(
    summary.get(
        "total_main_discharge_energy_Wh"
    )
)


if energy_Wh is not None:

    energy_kWh = (
        energy_Wh
        /
        1000.0
    )

else:

    energy_kWh = None


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
        "Hauptentladekapazität",
        metric_text(
            summary.get(
                "total_main_discharge_capacity_Ah"
            ),
            "Ah",
            2,
        ),
        get_kpi_explanation(
            learning,
            "total_main_discharge_capacity_Ah",
        ),
    )


with k3:

    render_metric(
        "Hauptentladeenergie",
        metric_text(
            energy_kWh,
            "kWh",
            2,
        ),
        get_kpi_explanation(
            learning,
            "total_main_discharge_energy_Wh",
        ),
    )


with k4:

    render_metric(
        "R nach 0,1 s",
        metric_text(
            summary.get(
                "mean_dch_pulse_R_0p1s_mOhm"
            ),
            "mΩ",
            2,
        ),
        get_kpi_explanation(
            learning,
            "mean_dch_pulse_R_0p1s_mOhm",
        ),
    )


with k5:

    render_metric(
        "Min. Modulspannung",
        metric_text(
            summary.get(
                "minimum_module_voltage_V"
            ),
            "V",
            2,
        ),
        get_kpi_explanation(
            learning,
            "minimum_module_voltage_V",
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
            "Hauptentladekapazität",
            "total_main_discharge_capacity_Ah",
        ),
        (
            "Hauptentladeenergie",
            "total_main_discharge_energy_Wh",
        ),
        (
            "Pulswiderstand nach 0,1 s",
            "mean_dch_pulse_R_0p1s_mOhm",
        ),
        (
            "Minimale Modulspannung",
            "minimum_module_voltage_V",
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
            + title
            + "**"
        )

        short = explanation.get(
            "short"
        )

        if short:

            st.write(
                short
            )

        formula = explanation.get(
            "formula"
        )

        if formula:

            st.caption(
                "Formel: "
                + formula
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
# MAIN PAGE NAVIGATION
#
# Only the selected section is executed/rendered.
# ============================================================


section = section_selector(
    [
        "Entladung",
        "Widerstand",
        "Zellen",
        "Temperatur",
        "EIS",
        "Vergleich",
        "Lernen",
        "Analyse",
    ],
    key=(
        "discharge_main_section"
    ),
)


st.divider()


# ============================================================
# SECTION:
# DISCHARGE
# ============================================================


if section == "Entladung":

    st.subheader(
        "Entladeverhalten"
    )

    d1, d2, d3, d4 = (
        st.columns(4)
    )


    with d1:

        render_metric(
            "Mittlerer Entladestrom",
            metric_text(
                summary.get(
                    "mean_main_discharge_current_A"
                ),
                "A",
                2,
            ),
            get_kpi_explanation(
                learning,
                "mean_main_discharge_current_A",
            ),
        )


    with d2:

        render_metric(
            "Netto entnommene Ladung",
            metric_text(
                summary.get(
                    "total_net_removed_charge_Ah"
                ),
                "Ah",
                2,
            ),
            get_kpi_explanation(
                learning,
                "total_net_removed_charge_Ah",
            ),
        )


    with d3:

        render_metric(
            "Max. Spannungserholung",
            metric_text(
                summary.get(
                    "maximum_voltage_recovery_V"
                ),
                "V",
                3,
            ),
            get_kpi_explanation(
                learning,
                "maximum_voltage_recovery_V",
            ),
        )


    with d4:

        render_metric(
            "Diagnosezyklen",
            metric_text(
                summary.get(
                    "number_of_cycles"
                ),
                "",
                0,
            ),
            get_kpi_explanation(
                learning,
                "number_of_cycles",
            ),
        )


    st.markdown(
        "### Spannung und Strom"
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
                voltage_current_plot(
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


    if (
        cycles is not None
        and
        not cycles.empty
    ):

        st.markdown(
            "### Verlauf über den "
            "Entladefortschritt"
        )


        left, right = (
            st.columns(2)
        )


        with left:

            st.markdown(
                "#### Spannung am Ende "
                "der Hauptentladung"
            )

            st.plotly_chart(
                cycle_voltage_plot(
                    cycles
                ),
                use_container_width=True,
            )

            render_graph_explanation(
                get_graph_explanation(
                    learning,
                    "voltage_relative_discharge",
                )
            )


        with right:

            st.markdown(
                "#### Spannungserholung"
            )

            st.plotly_chart(
                recovery_plot(
                    cycles
                ),
                use_container_width=True,
            )

            render_graph_explanation(
                get_graph_explanation(
                    learning,
                    "voltage_recovery_cycle",
                )
            )


# ============================================================
# SECTION:
# RESISTANCE
# ============================================================


elif section == "Widerstand":

    st.subheader(
        "Diagnostischer Pulswiderstand"
    )


    r1, r2, r3 = (
        st.columns(3)
    )


    with r1:

        render_metric(
            "R nach 0,1 s",
            metric_text(
                summary.get(
                    "mean_dch_pulse_R_0p1s_mOhm"
                ),
                "mΩ",
                2,
            ),
            get_kpi_explanation(
                learning,
                "mean_dch_pulse_R_0p1s_mOhm",
            ),
        )


    with r2:

        render_metric(
            "R nach 10 s",
            metric_text(
                summary.get(
                    "mean_dch_pulse_R_10s_mOhm"
                ),
                "mΩ",
                2,
            ),
            get_kpi_explanation(
                learning,
                "mean_dch_pulse_R_10s_mOhm",
            ),
        )


    with r3:

        render_metric(
            "R nach 18 s",
            metric_text(
                summary.get(
                    "mean_dch_pulse_R_18s_mOhm"
                ),
                "mΩ",
                2,
            ),
            get_kpi_explanation(
                learning,
                "mean_dch_pulse_R_18s_mOhm",
            ),
        )


    st.markdown(
        """
        <div class="green-note">
            Der Pulswiderstand wird als |ΔU/ΔI|
            bestimmt. Die Werte nach 0,1 s, 2 s,
            10 s und 18 s gehören zu
            unterschiedlichen Zeitpunkten der
            dynamischen Spannungsantwort.
        </div>
        """,
        unsafe_allow_html=True,
    )


    if (
        resistance is None
        or
        resistance.empty
    ):

        st.warning(
            "Keine exportierten "
            "Widerstandsdaten verfügbar."
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
                resistance_plot(
                    resistance
                ),
                use_container_width=True,
            )


        with info_col:

            render_graph_explanation(
                get_graph_explanation(
                    learning,
                    "pulse_resistance_progress",
                )
            )


        with st.expander(
            "Widerstandswerte pro "
            "Diagnosezyklus anzeigen"
        ):

            display_columns = [
                "cycle_id",
                "relative_discharge_progress_pct",
                "dch_pulse_R_0p1s_mOhm",
                "dch_pulse_R_2s_mOhm",
                "dch_pulse_R_10s_mOhm",
                "dch_pulse_R_18s_mOhm",
            ]

            display_columns = [
                column

                for column
                in display_columns

                if column
                in resistance.columns
            ]

            st.dataframe(
                resistance[
                    display_columns
                ],
                use_container_width=True,
                hide_index=True,
            )


# ============================================================
# SECTION:
# CELLS
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

            selected_cells = (
                st.multiselect(
                    "Zellen auswählen",
                    options=(
                        cell_columns
                    ),
                    default=(
                        cell_columns[
                            :3
                        ]
                    ),
                    format_func=(
                        cell_label
                    ),
                    key=(
                        "discharge_cells_"
                        + selected_test
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
                        cell_plot(
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
                    "Bitte mindestens "
                    "eine Zelle auswählen."
                )


            c1, c2 = (
                st.columns(2)
            )


            with c1:

                render_metric(
                    "Niedrigste Zellspannung",
                    metric_text(
                        summary.get(
                            "minimum_cell_voltage_V"
                        ),
                        "V",
                        4,
                    ),
                    get_kpi_explanation(
                        learning,
                        "minimum_cell_voltage_V",
                    ),
                )


            with c2:

                render_metric(
                    (
                        "Max. "
                        "Zellspannungsdifferenz"
                    ),
                    metric_text(
                        summary.get(
                            "maximum_cell_spread_mV"
                        ),
                        "mV",
                        2,
                    ),
                    get_kpi_explanation(
                        learning,
                        "maximum_cell_spread_mV",
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
                    "### "
                    "Zellspannungsdifferenz"
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


# ============================================================
# SECTION:
# TEMPERATURE
# ============================================================


elif section == "Temperatur":

    st.subheader(
        "Thermisches Verhalten"
    )


    t1, t2 = (
        st.columns(2)
    )


    with t1:

        render_metric(
            "Mittlere Klimatemperatur",
            format_temperature(
                summary.get(
                    "mean_climate_temperature_C"
                )
            ),
            get_kpi_explanation(
                learning,
                "test_temperature_C",
            ),
        )


    with t2:

        render_metric(
            "Maximale Modultemperatur",
            metric_text(
                summary.get(
                    "maximum_module_temperature_C"
                ),
                "°C",
                2,
            ),
            get_kpi_explanation(
                learning,
                "maximum_module_temperature_C",
            ),
        )


    if (
        temperature is None
        or
        temperature.empty
    ):

        st.warning(
            "Keine exportierten "
            "Temperaturdaten verfügbar."
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
                    "module_temperature_progress",
                )
            )


# ============================================================
# SECTION:
# EIS
# ============================================================


elif section == "EIS":

    st.subheader(
        "Elektrochemische "
        "Impedanzspektroskopie"
    )


    eis_summary = (
        summary.get(
            "eis",
            {},
        )
        or {}
    )


    eis_display = (
        summary.get(
            "eis_display",
            {},
        )
        or {}
    )


    e1, e2, e3 = (
        st.columns(3)
    )


    with e1:

        render_metric(
            "Vollständige EIS-Scans",
            metric_text(
                eis_summary.get(
                    "number_of_eis_scan_sweeps"
                ),
                "",
                0,
            ),
            get_kpi_explanation(
                learning,
                "eis_scan_sweeps",
            ),
        )


    with e2:

        render_metric(
            "EIS-Messpunkte",
            metric_text(
                eis_summary.get(
                    "number_of_eis_scan_points"
                ),
                "",
                0,
            ),
            get_kpi_explanation(
                learning,
                "eis_scan_points",
            ),
        )


    with e3:

        minimum_frequency = (
            safe_float(
                eis_summary.get(
                    "minimum_frequency_Hz"
                )
            )
        )

        maximum_frequency = (
            safe_float(
                eis_summary.get(
                    "maximum_frequency_Hz"
                )
            )
        )


        if (
            minimum_frequency
            is None
            or
            maximum_frequency
            is None
        ):

            frequency_text = "–"


        else:

            frequency_text = (
                format_number(
                    minimum_frequency,
                    1,
                )
                +
                " – "
                +
                format_number(
                    maximum_frequency,
                    0,
                )
                +
                " Hz"
            )


        render_metric(
            "Frequenzbereich",
            frequency_text,
            get_kpi_explanation(
                learning,
                "eis_frequency_range",
            ),
        )


    st.markdown(
        """
        <div class="green-note">
            Für Nyquist, Bode-Betrag und
            Bode-Phase wird der vollständige
            EIS-Scan verwendet. Einzelne
            Spektralbereiche werden ohne
            zusätzliches Modell bewusst nicht
            eindeutig einem bestimmten
            elektrochemischen Prozess zugeordnet.
        </div>
        """,
        unsafe_allow_html=True,
    )


    if (
        eis_scan is None
        or
        eis_scan.empty
    ):

        st.warning(
            "Für diesen Test sind keine "
            "vollständigen EIS-Scans verfügbar."
        )


    else:

        available_cycles = sorted(
            int(
                value
            )

            for value
            in (
                eis_scan[
                    "cycle_id"
                ]
                .dropna()
                .unique()
            )
        )


        selected_cycle = (
            st.selectbox(
                "Diagnosezyklus auswählen",
                options=(
                    available_cycles
                ),
                key=(
                    "eis_cycle_"
                    + selected_test
                ),
            )
        )


        cycle_eis = (
            eis_scan[
                eis_scan[
                    "cycle_id"
                ]
                ==
                selected_cycle
            ]
            .copy()
        )


        progress = None


        if (
            not cycle_eis.empty
            and
            "relative_discharge_progress_pct"
            in cycle_eis.columns
        ):

            progress = safe_float(
                cycle_eis[
                    "relative_discharge_progress_pct"
                ].iloc[0]
            )


        if progress is not None:

            st.caption(
                "Relativer Entladefortschritt "
                "dieses Diagnosezyklus: "
                f"{progress:.1f} %"
            )


        scale_factor = safe_float(
            eis_display.get(
                "dashboard_scale_factor"
            )
        )


        if scale_factor is None:

            scale_factor = 1.0


        impedance_unit = (
            eis_display.get(
                "recommended_dashboard_unit",
                "Ω",
            )
        )


        # ----------------------------------------------------
        # NYQUIST
        # ----------------------------------------------------

        st.markdown(
            "### Nyquist-Diagramm"
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
                nyquist_plot(
                    cycle_eis,
                    scale_factor,
                    impedance_unit,
                ),
                use_container_width=True,
            )


        with info_col:

            render_graph_explanation(
                get_graph_explanation(
                    learning,
                    "eis_nyquist",
                )
            )


        # ----------------------------------------------------
        # BODE MAGNITUDE
        # ----------------------------------------------------

        st.markdown(
            "### Bode-Betrag"
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
                bode_magnitude_plot(
                    cycle_eis,
                    scale_factor,
                    impedance_unit,
                ),
                use_container_width=True,
            )


        with info_col:

            render_graph_explanation(
                get_graph_explanation(
                    learning,
                    "eis_bode_magnitude",
                )
            )


        # ----------------------------------------------------
        # BODE PHASE
        # ----------------------------------------------------

        st.markdown(
            "### Bode-Phase"
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
                bode_phase_plot(
                    cycle_eis
                ),
                use_container_width=True,
            )


        with info_col:

            render_graph_explanation(
                get_graph_explanation(
                    learning,
                    "eis_bode_phase",
                )
            )


        # ----------------------------------------------------
        # SMALL 3-POINT REFERENCE
        # ----------------------------------------------------

        if (
            eis_points is not None
            and
            not eis_points.empty
        ):

            with st.expander(
                "3-Punkt-EIS-Referenz anzeigen"
            ):

                reference = (
                    eis_points[
                        eis_points[
                            "cycle_id"
                        ]
                        ==
                        selected_cycle
                    ]
                    .copy()
                )


                display_columns = [
                    "frequency_Hz",
                    "z_real",
                    "z_imag",
                    "z_magnitude",
                    "phase_deg",
                    "relative_discharge_progress_pct",
                ]


                display_columns = [
                    column

                    for column
                    in display_columns

                    if column
                    in reference.columns
                ]


                st.dataframe(
                    reference[
                        display_columns
                    ],
                    use_container_width=True,
                    hide_index=True,
                )


# ============================================================
# SECTION:
# TEMPERATURE COMPARISON
# ============================================================


elif section == "Vergleich":

    st.subheader(
        "Temperaturvergleich"
    )


    st.write(
        "Die verfügbaren Entladungsmessungen "
        "werden anhand ihrer gemessenen "
        "Prüftemperatur miteinander verglichen."
    )


    st.info(
        "Die Unterschiede zeigen zunächst das "
        "Verhalten unter den jeweiligen "
        "Versuchsbedingungen. Eine einzelne "
        "Ursache wird daraus nicht direkt "
        "abgeleitet."
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
            "total_main_discharge_energy_Wh"
            in comparison_data.columns
        ):

            comparison_data[
                "total_main_discharge_energy_kWh"
            ] = (
                comparison_data[
                    "total_main_discharge_energy_Wh"
                ]
                /
                1000.0
            )


        # ----------------------------------------------------
        # CAPACITY + ENERGY
        # ----------------------------------------------------

        left, right = (
            st.columns(2)
        )


        with left:

            st.markdown(
                "#### Hauptentladekapazität"
            )


            if (
                "total_main_discharge_capacity_Ah"
                in comparison_data.columns
            ):

                st.plotly_chart(
                    comparison_plot(
                        comparison_data,
                        (
                            "total_main_discharge_"
                            "capacity_Ah"
                        ),
                        "Kapazität",
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
                "#### Hauptentladeenergie"
            )


            if (
                "total_main_discharge_energy_kWh"
                in comparison_data.columns
            ):

                st.plotly_chart(
                    comparison_plot(
                        comparison_data,
                        (
                            "total_main_discharge_"
                            "energy_kWh"
                        ),
                        "Energie",
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


        # ----------------------------------------------------
        # MIN VOLTAGE + RESISTANCE
        # ----------------------------------------------------

        left, right = (
            st.columns(2)
        )


        with left:

            st.markdown(
                "#### Minimale Modulspannung"
            )


            if (
                "minimum_module_voltage_V"
                in comparison_data.columns
            ):

                st.plotly_chart(
                    comparison_plot(
                        comparison_data,
                        "minimum_module_voltage_V",
                        "Minimale Modulspannung",
                        "V",
                        2,
                    ),
                    use_container_width=True,
                )


                render_graph_explanation(
                    get_graph_explanation(
                        comparison_learning,
                        "minimum_voltage_temperature",
                    )
                )


        with right:

            st.markdown(
                "#### Pulswiderstand "
                "nach 0,1 s"
            )


            if (
                "mean_dch_pulse_R_0p1s_mOhm"
                in comparison_data.columns
            ):

                st.plotly_chart(
                    comparison_plot(
                        comparison_data,
                        (
                            "mean_dch_pulse_"
                            "R_0p1s_mOhm"
                        ),
                        "Pulswiderstand",
                        "mΩ",
                        2,
                    ),
                    use_container_width=True,
                )


                render_graph_explanation(
                    get_graph_explanation(
                        comparison_learning,
                        "resistance_temperature",
                    )
                )


        # ----------------------------------------------------
        # CELL SPREAD
        # ----------------------------------------------------

        if (
            "maximum_cell_spread_mV"
            in comparison_data.columns
        ):

            st.markdown(
                "#### Maximale "
                "Zellspannungsdifferenz"
            )


            st.plotly_chart(
                comparison_plot(
                    comparison_data,
                    "maximum_cell_spread_mV",
                    "Zellspannungsdifferenz",
                    "mV",
                    2,
                ),
                use_container_width=True,
            )


            render_graph_explanation(
                get_graph_explanation(
                    comparison_learning,
                    "cell_spread_temperature",
                )
            )


        with st.expander(
            "Vergleichstabelle anzeigen"
        ):

            st.dataframe(
                comparison,
                use_container_width=True,
                hide_index=True,
            )


# ============================================================
# SECTION:
# LEARNING
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
                "discharge_learning_scope"
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
            "discharge_"
            + selected_test
        )


    else:

        active_learning = (
            comparison_learning
        )

        learning_prefix = (
            "discharge_comparison"
        )


    # --------------------------------------------------------
    # LEARNING OBJECTIVES
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # THEORY
    # --------------------------------------------------------

    theory = active_learning.get(
        "theory",
        [],
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


                formula = item.get(
                    "formula"
                )


                if formula:

                    st.caption(
                        "Formel: "
                        + formula
                    )


    # --------------------------------------------------------
    # QUIZ
    # --------------------------------------------------------

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
                    f"Frage "
                    f"{position}"
                )

                render_quiz(
                    quiz,
                    learning_prefix,
                )


    # --------------------------------------------------------
    # REFLECTION
    # --------------------------------------------------------

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


        for reflection in (
            reflections
        ):

            with st.container(
                border=True
            ):

                render_reflection(
                    reflection,
                    learning_prefix,
                )


    # --------------------------------------------------------
    # TRANSFER
    # --------------------------------------------------------

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


        for task in (
            transfer_tasks
        ):

            with st.container(
                border=True
            ):

                render_transfer(
                    task,
                    learning_prefix,
                )


# ============================================================
# SECTION:
# ADVANCED ANALYSIS
# ============================================================


elif section == "Analyse":

    st.subheader(
        "Erweiterte Analyse"
    )


    st.write(
        "Hier stehen zusätzliche technische "
        "Informationen zur Berechnung, "
        "Ereigniserkennung, Validierung und "
        "Exportstruktur zur Verfügung."
    )


    # --------------------------------------------------------
    # FORMULAS
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
        \int I(t)\,dt
        \right|
        """
    )


    st.latex(
        r"""
        E_{\mathrm{Wh}}
        =
        \frac{1}{3600}
        \left|
        \int U(t)I(t)\,dt
        \right|
        """
    )


    st.latex(
        r"""
        R
        =
        \left|
        \frac{\Delta U}{\Delta I}
        \right|
        """
    )


    st.latex(
        r"""
        Z(f)
        =
        Z'(f)
        +
        jZ''(f)
        """
    )


    st.latex(
        r"""
        |Z|
        =
        \sqrt{
            Z'^2
            +
            Z''^2
        }
        """
    )


    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    st.markdown(
        "### Validierung"
    )


    if (
        validation_summary is None
        or
        validation_summary.empty
    ):

        st.info(
            "Keine "
            "Validierungszusammenfassung "
            "verfügbar."
        )


    else:

        st.dataframe(
            validation_summary,
            use_container_width=True,
            hide_index=True,
        )


    if (
        validation is not None
        and
        not validation.empty
    ):

        with st.expander(
            "Detaillierte "
            "Validierung anzeigen"
        ):

            st.dataframe(
                validation,
                use_container_width=True,
                hide_index=True,
            )


    # --------------------------------------------------------
    # CYCLE KPIs
    # --------------------------------------------------------

    if (
        cycles is not None
        and
        not cycles.empty
    ):

        with st.expander(
            "Zyklus-KPIs anzeigen"
        ):

            st.dataframe(
                cycles,
                use_container_width=True,
                hide_index=True,
            )


    # --------------------------------------------------------
    # DETECTED PHASES
    # --------------------------------------------------------

    if (
        phases is not None
        and
        not phases.empty
    ):

        with st.expander(
            "Erkannte Phasen anzeigen"
        ):

            st.dataframe(
                phases,
                use_container_width=True,
                hide_index=True,
            )


    # --------------------------------------------------------
    # DIAGNOSTIC CYCLES
    # --------------------------------------------------------


    if (
        diagnostic_cycles
        is not None
        and
        not diagnostic_cycles.empty
    ):

        with st.expander(
            "Diagnosezyklen anzeigen"
        ):

            st.dataframe(
                diagnostic_cycles,
                use_container_width=True,
                hide_index=True,
            )

    # --------------------------------------------------------
    # EXPORT / INTERFACE INFORMATION
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
    
    analysis_metadata = (
        manifest.get(
            "analysis",
            {},
        )
    )


    if analysis_metadata:
        meta_left, meta_right = (
            st.columns(2)
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
                    analysis_metadata.get(
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
                    analysis_metadata.get(
                        "native_timestamps_used_for_analysis"
                    )
                )
            )


            st.markdown(
                "**Prüfstandsvalidierung "
                "enthalten**"
            )

            st.caption(
                status_text(
                    analysis_metadata.get(
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
                    analysis_metadata.get(
                        "visualization_data_downsampled"
                    )
                )
            )


            maximum_rows = (
                analysis_metadata.get(
                    "maximum_visualization_rows"
                )
            )

            st.markdown(
                "**Maximale "
                "Visualisierungszeilen**"
            )

            if maximum_rows is not None:

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


            eis_downsampled = (
                analysis_metadata.get(
                    "eis_scan_downsampled"
                )
            )

            st.markdown(
                "**EIS-Scans reduziert**"
            )

            st.caption(
                status_text(
                    eis_downsampled
                )
            )
            
    st.markdown(
        """
        <div class="green-note">
            <strong>Trennung von Analyse und Visualisierung:</strong>
            Die vollständigen Messdaten werden für die
            analytische Berechnung verwendet. Erst anschließend
            werden reduzierte Visualisierungsdaten für das
            Dashboard exportiert. Die EIS-Scans werden aufgrund
            ihrer geringen Datenmenge vollständig übernommen.
        </div>
          """,
        unsafe_allow_html=True,
    )

