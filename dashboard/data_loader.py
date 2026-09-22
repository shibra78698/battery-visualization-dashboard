from pathlib import Path
import json

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]

CAPACITY_EXPORT_DIR = (
    PROJECT_ROOT
    / "export"
    / "dibala"
    / "capacity"
)


def read_json(path):
    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


@st.cache_data
def load_capacity_index():
    index_path = (
        CAPACITY_EXPORT_DIR
        / "index.json"
    )

    if not index_path.exists():
        raise FileNotFoundError(
            "Capacity index was not found. "
            "Run run_capacity_export.py first."
        )

    return read_json(
        index_path
    )


def capacity_export_path(
    filename,
    test_id,
):
    return (
        CAPACITY_EXPORT_DIR
        / test_id
        / filename
    )


@st.cache_data
def load_capacity_data(test_id):
    test_dir = (
        CAPACITY_EXPORT_DIR
        / test_id
    )

    if not test_dir.exists():
        raise FileNotFoundError(
            f"Capacity export folder does not exist: "
            f"{test_dir}"
        )

    summary = read_json(
        test_dir
        / "capacity_summary.json"
    )

    manifest = read_json(
        test_dir
        / "manifest.json"
    )

    learning = read_json(
        test_dir
        / "learning_content.json"
    )

    electrical = pd.read_csv(
        test_dir
        / "electrical.csv"
    )

    cells = pd.read_csv(
        test_dir
        / "cells.csv"
    )

    temperature = pd.read_csv(
        test_dir
        / "temperature.csv"
    )

    events = pd.read_csv(
        test_dir
        / "events.csv"
    )

    return {
        "summary": summary,
        "manifest": manifest,
        "learning": learning,
        "electrical": electrical,
        "cells": cells,
        "temperature": temperature,
        "events": events,
    }

def select_capacity_test():
    index = load_capacity_index()

    tests = index.get(
        "tests",
        [],
    )

    if not tests:
        st.error(
            "Keine Kapazitätsmessungen verfügbar."
        )
        st.stop()

    test_ids = [
        test["id"]
        for test in tests
    ]

    test_names = {
        test["id"]: test["display_name"]
        for test in tests
    }

    if (
        "selected_capacity_test"
        not in st.session_state
        or st.session_state[
            "selected_capacity_test"
        ] not in test_ids
    ):
        st.session_state[
            "selected_capacity_test"
        ] = test_ids[0]

    selected_test = st.sidebar.selectbox(
        "Kapazitätsmessung",
        options=test_ids,
        format_func=lambda test_id: (
            test_names.get(
                test_id,
                test_id,
            )
        ),
        key="selected_capacity_test",
    )

    return selected_test