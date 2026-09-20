from pathlib import Path
import json

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CAPACITY_DIR = (
    PROJECT_ROOT
    / "export"
    / "dibala"
    / "capacity"
)


def read_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


@st.cache_data(show_spinner=False)
def load_capacity_data():
    required_files = [
        "capacity_summary.json",
        "electrical.csv",
        "cells.csv",
        "temperature.csv",
        "events.csv",
        "learning_content.json",
        "manifest.json",
    ]

    missing = [
        name
        for name in required_files
        if not (CAPACITY_DIR / name).exists()
    ]

    if missing:
        raise FileNotFoundError(
            "Folgende Exportdateien fehlen: "
            + ", ".join(missing)
        )

    return {
        "summary": read_json(
            CAPACITY_DIR / "capacity_summary.json"
        ),
        "electrical": pd.read_csv(
            CAPACITY_DIR / "electrical.csv"
        ),
        "cells": pd.read_csv(
            CAPACITY_DIR / "cells.csv"
        ),
        "temperature": pd.read_csv(
            CAPACITY_DIR / "temperature.csv"
        ),
        "events": pd.read_csv(
            CAPACITY_DIR / "events.csv"
        ),
        "learning": read_json(
            CAPACITY_DIR / "learning_content.json"
        ),
        "manifest": read_json(
            CAPACITY_DIR / "manifest.json"
        ),
    }


def capacity_export_path(filename):
    return CAPACITY_DIR / filename