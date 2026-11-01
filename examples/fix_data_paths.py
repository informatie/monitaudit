# examples/fix_data_paths.py

from __future__ import annotations

import re
from pathlib import Path


EXAMPLES_DIR = Path(__file__).resolve().parent

EXAMPLE_FILES = tuple(
    sorted(
        EXAMPLES_DIR.rglob("main_*.py")
    )
)


EXAMPLES_DIR_PATTERN = re.compile(
    r"""
    ^EXAMPLES_DIR
    \s*=\s*
    Path\(__file__\)
    (?:\.resolve\(\))?
    \.parent
    \s*$
    """,
    flags=re.MULTILINE | re.VERBOSE,
)


DATASET_PATH_PATTERN = re.compile(
    r"""
    EXAMPLES_DIR
    (?=
        \s*
        /
        \s*
        ["']data["']
    )
    """,
    flags=re.VERBOSE,
)


def update_file(
    path: Path,
) -> list[str]:
    source = path.read_text(
        encoding="utf-8"
    )

    updated = source
    changes: list[str] = []

    updated, count = EXAMPLES_DIR_PATTERN.subn(
        (
            "EXAMPLES_DIR = "
            "Path(__file__).resolve().parents[1]"
        ),
        updated,
    )

    if count:
        changes.append(
            "EXAMPLES_DIR definition -> EXAMPLES_DIR"
        )

    updated, count = DATASET_PATH_PATTERN.subn(
        "EXAMPLES_DIR",
        updated,
    )

    if count:
        changes.append(
            "dataset path -> examples/data"
        )

    if updated != source:
        path.write_text(
            updated,
            encoding="utf-8",
        )

    return changes


def show_remaining_data_references() -> None:
    print()
    print("=" * 72)
    print("REMAINING DATA REFERENCES")
    print("=" * 72)

    found = False

    for path in EXAMPLE_FILES:
        source = path.read_text(
            encoding="utf-8"
        )

        if (
            '"data"' not in source
            and "'data'" not in source
            and "data/" not in source
        ):
            continue

        relative = path.relative_to(
            EXAMPLES_DIR
        )

        print(
            f"CHECK    {relative}"
        )

        found = True

    if not found:
        print(
            "No remaining data references found."
        )


def main() -> None:
    print()
    print("MonitAudit example data path migration")
    print("=" * 72)

    changed_files = 0

    for path in EXAMPLE_FILES:
        changes = update_file(
            path
        )

        relative = path.relative_to(
            EXAMPLES_DIR
        )

        if not changes:
            print(
                f"OK       {relative}"
            )
            continue

        changed_files += 1

        print(
 f"UPDATED  {relative}"
        )

        for change in changes:
            print(
                f"         - {change}"
            )

    print()
    print("=" * 72)
    print(
        f"Updated {changed_files} file(s)."
    )

    show_remaining_data_references()


if __name__ == "__main__":
    main()