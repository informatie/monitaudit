# examples/fix_example_paths.py

from __future__ import annotations

import re
from pathlib import Path


EXAMPLES_ROOT = Path(__file__).resolve().parent


def update_file(path: Path) -> list[str]:
    source = path.read_text(encoding="utf-8")
    updated = source
    changes: list[str] = []

    # ------------------------------------------------------------------
    # EXAMPLE_DIR -> EXAMPLES_DIR
    # ------------------------------------------------------------------

    updated, count = re.subn(
        r"\bEXAMPLE_DIR\b",
        "EXAMPLES_DIR",
        updated,
    )

    if count:
        changes.append(
            f"EXAMPLE_DIR -> EXAMPLES_DIR ({count})"
        )

    # ------------------------------------------------------------------
    # Normalise EXAMPLES_DIR definition
    # ------------------------------------------------------------------

    patterns = (
        r"^EXAMPLES_DIR\s*=\s*Path\(__file__\)\.parent\s*$",
        r"^EXAMPLES_DIR\s*=\s*Path\(__file__\)\.resolve\(\)\.parent\s*$",
    )

    for pattern in patterns:
        updated, count = re.subn(
            pattern,
            (
                "EXAMPLES_DIR = "
                "Path(__file__).resolve().parents[1]"
            ),
            updated,
            flags=re.MULTILINE,
        )

        if count:
            changes.append(
                "normalised EXAMPLES_DIR"
            )

    # ------------------------------------------------------------------
    # Ensure CONFIG_DIR exists when required
    # ------------------------------------------------------------------

    uses_config = bool(
        re.search(
            r"""
            CONFIG_PATH
            |
            EXAMPLES_DIR\s*/\s*["']config["']
            |
            / \s* ["']config["']
            """,
            updated,
            flags=re.VERBOSE,
        )
    )

    has_config_dir = bool(
        re.search(
            r"^CONFIG_DIR\s*=",
            updated,
            flags=re.MULTILINE,
        )
    )

    # ------------------------------------------------------------------
    # Ensure DATA_DIR exists when required
    # ------------------------------------------------------------------

    uses_data = bool(
        re.search(
            r"""
            DATASET_PATH
            |
            DATA_PATH
            |
            EXAMPLES_DIR\s*/\s*["']data["']
            |
            / \s* ["']data["']
            """,
            updated,
            flags=re.VERBOSE,
        )
    )

    has_data_dir = bool(
        re.search(
            r"^DATA_DIR\s*=",
            updated,
            flags=re.MULTILINE,
        )
    )

    additions: list[str] = []

    if uses_config and not has_config_dir:
        additions.append(
            'CONFIG_DIR = EXAMPLES_DIR / "config"'
        )

    if uses_data and not has_data_dir:
        additions.append(
            'DATA_DIR = EXAMPLES_DIR / "data"'
        )

    if additions:
        examples_definition = (
            "EXAMPLES_DIR = "
            "Path(__file__).resolve().parents[1]"
        )

        replacement = (
            examples_definition
            + "\n"
            + "\n".join(additions)
        )

        updated = updated.replace(
            examples_definition,
            replacement,
            1,
        )

        changes.extend(
            f"added {line.split(' = ', 1)[0]}"
            for line in additions
        )

    # ------------------------------------------------------------------
    # Replace direct EXAMPLES_DIR / data
    # ------------------------------------------------------------------

    updated, count = re.subn(
        r'EXAMPLES_DIR\s*/\s*["\']data["\']',
        "DATA_DIR",
        updated,
    )

    if count:
        changes.append(
            f"EXAMPLES_DIR/data -> DATA_DIR ({count})"
        )

    # ------------------------------------------------------------------
    # Replace direct EXAMPLES_DIR / config
    # ------------------------------------------------------------------

    updated, count = re.subn(
        r'EXAMPLES_DIR\s*/\s*["\']config["\']',
        "CONFIG_DIR",
        updated,
    )

    if count:
        changes.append(
            f"EXAMPLES_DIR/config -> CONFIG_DIR ({count})"
        )

    # -------------------------------------------------------
    # Write only when changed
    # ------------------------------------------------------------------

    if updated != source:
        path.write_text(
            updated,
            encoding="utf-8",
        )

    return changes


def main() -> None:
    files = sorted(
        EXAMPLES_ROOT.rglob("main_*.py")
    )

    print()
    print("MonitAudit example path migration")
    print("=" * 72)

    changed_files = 0

    for path in files:
        relative = path.relative_to(
            EXAMPLES_ROOT
        )

        changes = update_file(
            path
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
        f"Checked {len(files)} file(s)."
    )
    print(
        f"Updated {changed_files} file(s)."
    )


if __name__ == "__main__":
    main()