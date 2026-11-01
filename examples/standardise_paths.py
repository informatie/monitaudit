# examples/standardise_paths.py

from __future__ import annotations

import re
from pathlib import Path


EXAMPLES_ROOT = Path(__file__).resolve().parent

STANDARD_PATHS = """EXAMPLES_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = EXAMPLES_DIR / "config"
DATA_DIR = EXAMPLES_DIR / "data"
"""


def ensure_path_import(source: str) -> str:
    """Ensure pathlib.Path is imported."""

    if re.search(
        r"^from pathlib import Path$",
        source,
        flags=re.MULTILINE,
    ):
        return source

    future_import = "from __future__ import annotations"

    if future_import in source:
        return source.replace(
            future_import,
            future_import + "\n\nfrom pathlib import Path",
            1,
        )

    return "from pathlib import Path\n\n" + source


def remove_old_path_definitions(source: str) -> str:
    """Remove existing example path constant definitions."""

    names = (
        "EXAMPLE_DIR",
        "EXAMPLES_DIR",
        "CONFIG_DIR",
        "DATA_DIR",
    )

    for name in names:
        source = re.sub(
            rf"^{name}\s*=.*$\n?",
            "",
            source,
            flags=re.MULTILINE,
        )

    return source


def rename_old_references(source: str) -> str:
    """Replace obsolete EXAMPLE_DIR references."""

    return re.sub(
        r"\bEXAMPLE_DIR\b",
        "EXAMPLES_DIR",
        source,
    )


def insert_standard_paths(source: str) -> str:
    """Insert standard example directory definitions."""

    match = re.search(
        r"^from pathlib import Path$",
        source,
        flags=re.MULTILINE,
    )

    if match is None:
        raise RuntimeError(
            "Could not locate pathlib.Path import."
        )

    position = match.end()

    return (
        source[:position]
        + "\n\n\n"
        + STANDARD_PATHS.rstrip()
        + "\n"
        + source[position:]
    )


def update_file(path: Path) -> bool:
    """Standardise paths in one main example."""

    original = path.read_text(
        encoding="utf-8"
    )

    updated = rename_old_references(
        original
    )

    updated = remove_old_path_definitions(
        updated
    )

    updated = ensure_path_import(
        updated
    )

    updated = insert_standard_paths(
        updated
    )

    if updated == original:
        return False

    path.write_text(
        updated,
        encoding="utf-8",
    )

    return True


def main() -> None:
    files = sorted(
        EXAMPLES_ROOT.rglob("main_*.py")
    )

    print()
    print("Standardising MonitAudit example paths")
    print("=" * 72)

    changed_files = 0

    for path in files:
        relative = path.relative_to(
            EXAMPLES_ROOT
        )

        if update_file(path):
            changed_files += 1
            print(f"UPDATED  {relative}")
        else:
            print(f"OK       {relative}")

    print()
    print("=" * 72)
    print(f"Files checked : {len(files)}")
    print(f"Files changed : {changed_files}")


if __name__ == "__main__":
    main()