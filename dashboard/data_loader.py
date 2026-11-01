from pathlib import Path
import json

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]

EXPORT_ROOT = (
    PROJECT_ROOT
    / "export"
    / "dibala"
)


@st.cache_data(show_spinner=False)
def read_json(path):
    path = Path(path)

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


@st.cache_data(show_spinner=False)
def read_csv(path):
    path = Path(path)

    return pd.read_csv(path)


def collection_root(test_type):
    valid_types = {
        "capacity",
        "ocv",
        "discharge",
    }

    if test_type not in valid_types:
        raise ValueError(
            f"Unknown test type: {test_type}"
        )

    return (
        EXPORT_ROOT
        / test_type
    )


def load_index(
    test_type,
    required=True,
):
    path = (
        collection_root(test_type)
        / "index.json"
    )

    if not path.exists():
        if required:
            raise FileNotFoundError(
                f"Export index not found: {path}"
            )

        return {
            "schema_version": None,
            "test_type": test_type,
            "number_of_tests": 0,
            "tests": [],
        }

    return read_json(path)


def _path_parent_name(value):
    if not value:
        return None

    path = Path(
        str(value)
    )

    if path.parent.name:
        return path.parent.name

    return None


def _normalise_test_entry(
    test_type,
    entry,
    position,
):
    """
    Normalise older Capacity index entries and newer
    OCV index entries to one dashboard representation.
    """
    entry = dict(
        entry
    )

    test_id = (
        entry.get("test_id")
        or entry.get("id")
        or entry.get("name")
    )

    folder = (
        entry.get("folder")
        or entry.get("directory")
        or entry.get("test_folder")
    )

    if folder is None:
        folder = _path_parent_name(
            entry.get(
                "summary"
            )
        )

    if folder is None:
        folder = _path_parent_name(
            entry.get(
                "manifest"
            )
        )

    if test_id is None:
        test_id = folder

    if test_id is None:
        source_file = entry.get(
            "source_file"
        )

        if source_file:
            test_id = Path(
                source_file
            ).stem

    if test_id is None:
        test_id = (
            f"{test_type}_{position + 1}"
        )

    if folder is None:
        folder = test_id

    entry[
        "test_id"
    ] = str(
        test_id
    )

    entry[
        "folder"
    ] = str(
        folder
    )

    return entry


def list_tests(test_type):
    index = load_index(
        test_type,
        required=False,
    )

    tests = index.get(
        "tests",
        [],
    )

    normalised = []

    for position, entry in enumerate(
        tests
    ):
        normalised.append(
            _normalise_test_entry(
                test_type,
                entry,
                position,
            )
        )

    return normalised


def get_test_ids(test_type):
    return [
        item["test_id"]
        for item in list_tests(
            test_type
        )
    ]


def get_test_entry(
    test_type,
    test_id,
):
    for item in list_tests(
        test_type
    ):
        if (
            item["test_id"]
            == test_id
        ):
            return item

    raise KeyError(
        f"Test '{test_id}' not found "
        f"in {test_type}/index.json"
    )


def get_default_test_id(
    test_type,
):
    test_ids = get_test_ids(
        test_type
    )

    if not test_ids:
        return None

    return test_ids[0]


def _test_directory(
    test_type,
    test_id,
):
    entry = get_test_entry(
        test_type,
        test_id,
    )

    folder = entry[
        "folder"
    ]

    return (
        collection_root(
            test_type
        )
        / folder
    )


def _entry_file_path(
    test_type,
    test_id,
    key,
):
    entry = get_test_entry(
        test_type,
        test_id,
    )

    relative_path = entry.get(
        key
    )

    if not relative_path:
        return None

    return (
        collection_root(
            test_type
        )
        / relative_path
    )


def _declared_filename(
    value,
):
    if value is None:
        return None

    if isinstance(
        value,
        str,
    ):
        return value

    if isinstance(
        value,
        dict,
    ):
        return value.get(
            "file"
        )

    return None


def load_test_manifest(
    test_type,
    test_id,
):
    path = _entry_file_path(
        test_type,
        test_id,
        "manifest",
    )

    if path is None:
        path = (
            _test_directory(
                test_type,
                test_id,
            )
            / "manifest.json"
        )

    if not path.exists():
        raise FileNotFoundError(
            f"Manifest not found: {path}"
        )

    return read_json(
        path
    )


def load_test_summary(
    test_type,
    test_id,
):
    path = _entry_file_path(
        test_type,
        test_id,
        "summary",
    )

    if path is not None:
        if path.exists():
            return read_json(
                path
            )

    manifest = load_test_manifest(
        test_type,
        test_id,
    )

    filename = _declared_filename(
        manifest.get(
            "files",
            {}
        ).get(
            "summary"
        )
    )

    if filename:
        path = (
            _test_directory(
                test_type,
                test_id,
            )
            / filename
        )

        if path.exists():
            return read_json(
                path
            )

    default_names = {
        "capacity":
            "capacity_summary.json",
        "ocv":
            "ocv_summary.json",
        "discharge":
            "discharge_summary.json",
    }

    default_name = (
        default_names.get(
            test_type
        )
    )

    if default_name:
        path = (
            _test_directory(
                test_type,
                test_id,
            )
            / default_name
        )

        if path.exists():
            return read_json(
                path
            )

    raise FileNotFoundError(
        f"Summary not found for "
        f"{test_id}"
    )


def load_test_learning_content(
    test_type,
    test_id,
):
    path = _entry_file_path(
        test_type,
        test_id,
        "learning_content",
    )

    if (
        path is not None
        and path.exists()
    ):
        return read_json(
            path
        )

    manifest = load_test_manifest(
        test_type,
        test_id,
    )

    filename = _declared_filename(
        manifest.get(
            "files",
            {}
        ).get(
            "learning_content"
        )
    )

    if filename:
        path = (
            _test_directory(
                test_type,
                test_id,
            )
            / filename
        )

        if path.exists():
            return read_json(
                path
            )

    path = (
        _test_directory(
            test_type,
            test_id,
        )
        / "learning_content.json"
    )

    if path.exists():
        return read_json(
            path
        )

    return None


def load_test_csv(
    test_type,
    test_id,
    data_key,
    required=False,
):
    manifest = load_test_manifest(
        test_type,
        test_id,
    )

    filename = _declared_filename(
        manifest.get(
            "files",
            {}
        ).get(
            data_key
        )
    )

    if not filename:
        default_names = {
            "electrical":
                "electrical.csv",
            "cells":
                "cells.csv",
            "temperature":
                "temperature.csv",
            "events":
                "events.csv",
            "discharge":
                "discharge.csv",
            "relaxation":
                "relaxation.csv",
            "phases":
                "phases.csv",
        }

        filename = (
            default_names.get(
                data_key
            )
        )

    if not filename:
        if required:
            raise FileNotFoundError(
                f"No export filename "
                f"defined for '{data_key}'"
            )

        return None

    path = (
        _test_directory(
            test_type,
            test_id,
        )
        / filename
    )

    if not path.exists():
        if required:
            raise FileNotFoundError(
                f"Data file not found: "
                f"{path}"
            )

        return None

    return read_csv(
        path
    )


def load_test_bundle(
    test_type,
    test_id,
    data_keys=None,
):
    if data_keys is None:
        data_keys = []

    bundle = {
        "test_id":
            test_id,

        "manifest":
            load_test_manifest(
                test_type,
                test_id,
            ),

        "summary":
            load_test_summary(
                test_type,
                test_id,
            ),

        "learning_content":
            load_test_learning_content(
                test_type,
                test_id,
            ),
    }

    for key in data_keys:
        bundle[key] = (
            load_test_csv(
                test_type,
                test_id,
                key,
                required=False,
            )
        )

    return bundle


# Capacity


def capacity_test_label(
    entry,
):
    source_file = entry.get(
        "source_file"
    )

    if source_file:
        return Path(
            source_file
        ).stem

    return entry.get(
        "test_id",
        "Kapazitätstest",
    )


def select_capacity_test():
    """
    Show the Capacity measurement selector in the sidebar.

    Supports both the older Capacity index schema and
    the newer common dashboard schema.
    """
    tests = list_tests(
        "capacity"
    )

    if not tests:
        return None

    test_ids = [
        test["test_id"]
        for test in tests
    ]

    labels = {
        test["test_id"]:
            capacity_test_label(
                test
            )
        for test in tests
    }

    with st.sidebar:
        st.markdown("---")

        st.caption(
            "Kapazitätsmessung"
        )

        selected_test = st.selectbox(
            "Kapazitätsmessung auswählen",
            options=test_ids,
            format_func=lambda test_id: (
                labels.get(
                    test_id,
                    test_id,
                )
            ),
            key="capacity_test_selector",
            label_visibility="collapsed",
        )

    return selected_test


def get_current_capacity_test_id():
    available = get_test_ids(
        "capacity"
    )

    selected = st.session_state.get(
        "capacity_test_selector"
    )

    if selected in available:
        return selected

    return get_default_test_id(
        "capacity"
    )


def capacity_export_path(
    filename,
    test_id=None,
):
    if test_id is None:
        test_id = (
            get_current_capacity_test_id()
        )

    if test_id is None:
        raise FileNotFoundError(
            "No Capacity test available."
        )

    return (
        _test_directory(
            "capacity",
            test_id,
        )
        / filename
    )


def load_capacity_data(
    test_id=None,
):
    if test_id is None:
        test_id = (
            get_current_capacity_test_id()
        )

    if test_id is None:
        raise FileNotFoundError(
            "No Capacity test available."
        )

    bundle = load_test_bundle(
        "capacity",
        test_id,
        data_keys=[
            "electrical",
            "cells",
            "temperature",
            "events",
        ],
    )

    return {
        "test_id":
            test_id,

        "summary":
            bundle["summary"],

        "electrical":
            bundle.get(
                "electrical"
            ),

        "cells":
            bundle.get(
                "cells"
            ),

        "temperature":
            bundle.get(
                "temperature"
            ),

        "events":
            bundle.get(
                "events"
            ),

        "learning":
            bundle.get(
                "learning_content"
            ),

        "manifest":
            bundle["manifest"],
    }


def load_capacity_index(
    required=True,
):
    return load_index(
        "capacity",
        required=required,
    )


def get_capacity_test_ids():
    return get_test_ids(
        "capacity"
    )


def load_capacity_summary(
    test_id,
):
    return load_test_summary(
        "capacity",
        test_id,
    )


def load_capacity_test(
    test_id,
    data_keys=None,
):
    return load_test_bundle(
        "capacity",
        test_id,
        data_keys=data_keys,
    )


# OCV


def load_ocv_index(
    required=True,
):
    return load_index(
        "ocv",
        required=required,
    )


def get_ocv_test_ids():
    return get_test_ids(
        "ocv"
    )


def load_ocv_summary(
    test_id,
):
    return load_test_summary(
        "ocv",
        test_id,
    )


def load_ocv_test(
    test_id,
    data_keys=None,
):
    return load_test_bundle(
        "ocv",
        test_id,
        data_keys=data_keys,
    )


def load_ocv_temperature_comparison():
    index = load_index(
        "ocv",
        required=False,
    )

    filename = index.get(
        "comparison_file",
        "temperature_comparison.csv",
    )

    path = (
        collection_root(
            "ocv"
        )
        / filename
    )

    if not path.exists():
        return pd.DataFrame()

    return read_csv(
        path
    )


def load_ocv_comparison_learning():
    index = load_index(
        "ocv",
        required=False,
    )

    filename = index.get(
        "comparison_learning_file",
        "comparison_learning_content.json",
    )

    path = (
        collection_root(
            "ocv"
        )
        / filename
    )

    if not path.exists():
        return None

    return read_json(
        path
    )


# Discharge


def load_discharge_index(
    required=True,
):
    return load_index(
        "discharge",
        required=required,
    )


def get_discharge_test_ids():
    return get_test_ids(
        "discharge"
    )


def load_discharge_summary(
    test_id,
):
    return load_test_summary(
        "discharge",
        test_id,
    )


def load_discharge_test(
    test_id,
    data_keys=None,
):
    return load_test_bundle(
        "discharge",
        test_id,
        data_keys=data_keys,
    )


def load_discharge_temperature_comparison():
    index = load_index(
        "discharge",
        required=False,
    )

    filename = index.get(
        "comparison_file",
        "temperature_comparison.csv",
    )

    path = (
        collection_root(
            "discharge"
        )
        / filename
    )

    if not path.exists():
        return pd.DataFrame()

    return read_csv(
        path
    )


def load_discharge_comparison_learning():
    index = load_index(
        "discharge",
        required=False,
    )

    filename = index.get(
        "comparison_learning_file",
        "comparison_learning_content.json",
    )

    path = (
        collection_root(
            "discharge"
        )
        / filename
    )

    if not path.exists():
        return None

    return read_json(
        path
    )


# Overview


def get_number_of_cells_from_summary(
    summary,
):
    if not summary:
        return None

    value = (
        summary
        .get(
            "module",
            {}
        )
        .get(
            "number_of_cells"
        )
    )

    if value is None:
        return None

    return int(
        value
    )


def get_available_cell_counts():
    cell_counts = []

    for test_type in (
        "capacity",
        "ocv",
    ):
        for entry in list_tests(
            test_type
        ):
            number_of_cells = (
                entry.get(
                    "number_of_cells"
                )
            )

            if number_of_cells is None:
                try:
                    summary = (
                        load_test_summary(
                            test_type,
                            entry[
                                "test_id"
                            ],
                        )
                    )

                    number_of_cells = (
                        get_number_of_cells_from_summary(
                            summary
                        )
                    )

                except (
                    FileNotFoundError,
                    KeyError,
                ):
                    number_of_cells = (
                        None
                    )

            if number_of_cells is not None:
                cell_counts.append(
                    int(
                        number_of_cells
                    )
                )

    return sorted(
        set(
            cell_counts
        )
    )

def get_system_description():
    cell_counts = (
        get_available_cell_counts()
    )

    if not cell_counts:
        return "Batteriemessdaten"

    if len(cell_counts) == 1:
        number_of_cells = (
            cell_counts[0]
        )

        if number_of_cells == 1:
            return "Einzelzelle"

        return (
            f"{number_of_cells} Zellen Batteriemodul"
        )

    minimum = min(
        cell_counts
    )

    maximum = max(
        cell_counts
    )

    return (
        f"Batteriesysteme mit "
        f"{minimum} bis "
        f"{maximum} Zellen"
    )


   
def get_overview_capacity():
    test_id = get_default_test_id(
        "capacity"
    )

    if test_id is None:
        return None

    return {
        "test_id":
            test_id,

        "summary":
            load_test_summary(
                "capacity",
                test_id,
            ),

        "entry":
            get_test_entry(
                "capacity",
                test_id,
            ),
    }


def get_dashboard_status():
    capacity_tests = list_tests(
        "capacity"
    )

    ocv_tests = list_tests(
        "ocv"
    )

    discharge_tests = list_tests(
        "discharge"
    )

    ocv_temperatures = []

    for test in ocv_tests:
        value = test.get(
            "temperature_C"
        )

        if value is not None:
            ocv_temperatures.append(
                float(
                    value
                )
            )

    ocv_temperatures = sorted(
        set(
            ocv_temperatures
        )
    )

    return {
        "capacity_tests":
            len(
                capacity_tests
            ),

        "ocv_tests":
            len(
                ocv_tests
            ),

        "discharge_tests":
            len(
                discharge_tests
            ),

        "ocv_temperatures":
            ocv_temperatures,

        "capacity_available":
            bool(
                capacity_tests
            ),

        "ocv_available":
            bool(
                ocv_tests
            ),

        "discharge_available":
            bool(
                discharge_tests
            ),
    }