# src/app.py

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st
import yaml


ERROR_CATALOGUE_PATH = Path(
    "config/error/monitaudit.errors"
)

ALL = "All"


def load_catalogue(
    path: Path,
) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Error catalogue not found: {path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Error catalogue path is not a file: {path}"
        )

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = yaml.safe_load(file)

    except yaml.YAMLError as exception:
        raise ValueError(
            f"Invalid error catalogue YAML: {path}"
        ) from exception

    except OSError as exception:
        raise OSError(
            f"Could not read error catalogue: {path}"
        ) from exception

    if not isinstance(
        data,
        dict,
    ):
        raise ValueError(
            "Error catalogue root must be a mapping."
        )

    if not isinstance(
        data.get("catalogue"),
        dict,
    ):
        raise ValueError(
            "Error catalogue must contain a "
            "'catalogue' mapping."
        )

    if not isinstance(
        data.get("errors"),
        dict,
    ):
        raise ValueError(
            "Error catalogue must contain an "
            "'errors' mapping."
        )

    return data


def get_errors(
    catalogue: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    raw_errors = catalogue.get(
        "errors",
        {},
    )

    if not isinstance(
        raw_errors,
        dict,
    ):
        return {}

    errors: dict[
        str,
        dict[str, Any],
    ] = {}

    for code, value in raw_errors.items():
        if not isinstance(
            code,
            str,
        ):
            continue

        if not isinstance(
            value,
            dict,
        ):
            continue

        errors[code] = value

    return errors


def values_for(
    errors: dict[str, dict[str, Any]],
    field: str,
) -> list[str]:
    return sorted(
        {
            str(error[field])
            for error in errors.values()
            if error.get(field) is not None
        }
    )


def sequence_values(
    value: Any,
) -> list[str]:
    if not isinstance(
        value,
        (list, tuple),
    ):
        return []

    return [
        str(item)
        for item in value
    ]


def matches_search(
    code: str,
    error: dict[str, Any],
    search: str,
) -> bool:
    query = search.strip().casefold()

    if not query:
        return True

    tags = sequence_values(
        error.get("tags")
    )

    context = sequence_values(
        error.get("context")
    )

    fields = [
        code,
        str(
            error.get(
                "title",
                "",
            )
        ),
        str(
            error.get(
                "description",
                "",
            )
        ),
        str(
            error.get(
                "solution",
                "",
            )
        ),
        str(
            error.get(
                "category",
                "",
            )
        ),
        str(
            error.get(
                "severity",
                "",
            )
        ),
        str(
            error.get(
                "status",
                "",
            )
        ),
        str(
            error.get(
                "exception",
                "",
            )
        ),
        " ".join(tags),
        " ".join(context),
    ]

    searchable = " ".join(
        fields
    ).casefold()

    return query in searchable


def filter_errors(
    errors: dict[str, dict[str, Any]],
    *,
    search: str,
    category: str,
    severity: str,
    status: str,
) -> dict[str, dict[str, Any]]:
    filtered: dict[
        str,
        dict[str, Any],
    ] = {}

    for code, error in errors.items():
        if (
            category != ALL
            and str(
                error.get(
                    "category",
                    "",
                )
            )
            != category
        ):
            continue

        if (
            severity != ALL
            and str(
                error.get(
                    "severity",
                    "",
                )
            )
            != severity
        ):
            continue

        if (
            status != ALL
            and str(
                error.get(
                    "status",
                    "",
                )
            )
            != status
        ):
            continue

        if not matches_search(
            code,
            error,
            search,
        ):
            continue

        filtered[code] = error

    return filtered


def display_catalogue_metadata(
    catalogue: dict[str, Any],
    error_count: int,
) -> None:
    metadata = catalogue.get(
        "catalogue",
        {},
    )

    if not isinstance(
        metadata,
        dict,
    ):
        return

    st.sidebar.header(
        "Catalogue"
    )

    st.sidebar.write(
        "**Name:**",
        str(
            metadata.get(
                "name",
                "MonitAudit",
            )
        ),
    )

    st.sidebar.write(
        "**Version:**",
        str(
            metadata.get(
                "version",
                "unknown",
            )
        ),
    )

    st.sidebar.write(
        "**Prefix:**",
        str(
            metadata.get(
                "code_prefix",
                "MTA",
            )
        ),
    )

    st.sidebar.metric(
        "Error definitions",
        error_count,
    )


def display_context(
    error: dict[str, Any],
) -> None:
    context = sequence_values(
        error.get("context")
    )

    st.subheader(
        "Runtime context"
    )

    if not context:
        st.caption(
            "No runtime context fields defined."
        )
        return

    for field in context:
        st.code(
            field,
            language=None,
        )


def display_tags(
    error: dict[str, Any],
) -> None:
    tags = sequence_values(
        error.get("tags")
    )

    st.subheader(
        "Tags"
    )

    if not tags:
        st.caption(
            "No tags defined."
        )
        return

    st.write(
        ", ".join(tags)
    )


def display_error(
    code: str,
    error: dict[str, Any],
) -> None:
    title = str(
        error.get(
            "title",
            "Untitled error",
        )
    )

    st.header(
        f"{code} · {title}"
    )

    category_column, severity_column, status_column = (
        st.columns(3)
    )

    category_column.metric(
        "Category",
        str(
            error.get(
                "category",
                "-",
            )
        ),
    )

    severity_column.metric(
        "Severity",
        str(
            error.get(
                "severity",
                "-",
            )
        ),
    )

    status_column.metric(
        "Status",
        str(
            error.get(
                "status",
                "-",
            )
        ),
    )

    st.subheader(
        "Description"
    )

    st.write(
        str(
            error.get(
                "description",
                "-",
            )
        )
    )

    st.subheader(
        "Solution"
    )

    st.write(
        str(
            error.get(
                "solution",
                "-",
            )
        )
    )

    st.divider()

    technical_column, lifecycle_column = (
        st.columns(2)
    )

    with technical_column:
        st.subheader(
            "Technical"
        )

        exception = error.get(
            "exception"
        )

        st.write(
            "**Exception:**",
            (
                str(exception)
                if exception is not None
                else "None"
            ),
        )

        st.write(
            "**Retryable:**",
            bool(
                error.get(
                    "retryable",
                    False,
                )
            ),
        )

        st.write(
            "**Introduced:**",
            str(
                error.get(
                    "introduced",
                    "-",
                )
            ),
        )

    with lifecycle_column:
        st.subheader(
            "Lifecycle"
        )

        (
            "deprecated"
        )

        replaced_by = error.get(
            "replaced_by"
        )

        documentation = error.get(
            "documentation"
        )

        st.write(
            "**Deprecated:**",
            (
                str(deprecated)
                if deprecated is not None
                else "No"
            ),
        )

        st.write(
            "**Replaced by:**",
            (
                str(replaced_by)
                if replaced_by is not None
                else "None"
            ),
        )

        st.write(
            "**Documentation:**",
            (
                str(documentation)
                if documentation is not None
                else "None"
            ),
        )

    display_context(
        error
    )

    display_tags(
        error
    )

    with st.expander(
        "Raw catalogue entry"
    ):
        raw_yaml = yaml.safe_dump(
            {
                code: error,
            },
            sort_keys=False,
            allow_unicode=True,
        )

        st.code(
            raw_yaml,
            language="yaml",
        )


def main() -> None:
    st.set_page_config(
        page_title=(
            "MonitAudit Error Catalogue"
        ),
        page_icon="🔎",
        layout="wide",
    )

    st.title(
        "MonitAudit Error Catalogue"
    )

    st.caption(
        str(
            ERROR_CATALOGUE_PATH
        )
    )

    try:
        catalogue = load_catalogue(
            ERROR_CATALOGUE_PATH
        )

    except (
        FileNotFoundError,
        OSError,
        ValueError,
    ) as exception:
        st.error(
            str(exception)
        )
        st.stop()
        return

    errors = get_errors(
        catalogue
    )

    if not errors:
        st.warning(
            "The error catalogue contains "
            "no error definitions."
        )
        return

    display_catalogue_metadata(
        catalogue,
        len(errors),
    )

    st.sidebar.divider()

    st.sidebar.header(
        "Filters"
    )

    search = st.sidebar.text_input(
        "Search",
        placeholder=(
            "MTA-00419, Delta, "
            "configuration..."
        ),
    )

    category = st.sidebar.selectbox(
        "Category",
        [
            ALL,
            *values_for(
                errors,
                "category",
            ),
        ],
    )

    severity = st.sidebar.selectbox(
        "Severity",
        [
            ALL,
            *values_for(
                errors,
                "severity",
            ),
        ],
    )

    status = st.sidebar.selectbox(
        "Status",
        [
            ALL,
            *values_for(
                errors,
                "status",
            ),
        ],
    )

    filtered_errors = filter_errors(
        errors,
        search=search,
        category=category,
        severity=severity,
        status=status,
    )

    st.sidebar.metric(
        "Matches",
        len(
            filtered_errors
        ),
    )

    if not filtered_errors:
        st.info(
            "No error codes match "
            "the selected filters."
        )
        return

    codes = sorted(
        filtered_errors
    )

    def format_error_code(
        code: str,
    ) -> str:
        title = filtered_errors[
            code
        ].get(
            "title",
            "",
        )

        return (
            f"{code} · {title}"
        )

    selected_code = st.selectbox(
        "Error code",
        options=codes,
        format_func=format_error_code,
    )

    display_error(
        selected_code,
        filtered_errors[
            selected_code
        ],
    )


if __name__ == "__main__":
    main()