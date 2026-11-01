# examples/fix_config.py

from __future__ import annotations

import re
from pathlib import Path


EXAMPLES_DIR = Path(__file__).resolve().parent


BUILD_CONFIG_PATTERN = re.compile(
    r"""
    build_monitaudit
    \(
        \s*
        CONFIG_PATH
        \s*
    \)
    """,
    re.VERBOSE,
)


def update_file(
    path: Path,
) -> int:
    source = path.read_text(
        encoding="utf-8"
    )

    updated, count = BUILD_CONFIG_PATTERN.subn(
        "build_monitaudit()",
        source,
    )

    if count:
        path.write_text(
            updated,
            encoding="utf-8",
        )

    return count


def main() -> None:
    files = sorted(
        EXAMPLES_DIR.rglob("main_*.py")
    )

    total_changes = 0

    print()
    print("MonitAudit example configuration migration")
    print("=" * 70)

    for path in files:
        count = update_file(path)

        relative = path.relative_to(
            EXAMPLES_DIR
        )

        if count:
            total_changes += count

            print(
                f"UPDATED  {relative} "
                f"({count} call(s))"
            )
        else:
            print(
                f"OK       {relative}"
            )

    print()
    print("=" * 70)
    print(
        f"Changed {total_changes} "
        "build_monitaudit call(s)."
    )


if __name__ == "__main__":
    main()