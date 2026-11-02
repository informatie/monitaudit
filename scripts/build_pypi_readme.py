# scripts/build_pypi_readme.py

from __future__ import annotations

from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]

README_PATH = PROJECT_DIR / "PYPI_README.md"
USAGE_PATH = PROJECT_DIR / "PYPI_USAGE.md"

CONFIG_DIR = PROJECT_DIR / "config" / "monitaudit"
PROPERTIES_PATH = CONFIG_DIR / "example_monitaudit.properties"
RUNTIME_PATH = CONFIG_DIR / "example_monitaudit.runtime"

OUTPUT_PATH = PROJECT_DIR / "README.md"

CODE_FENCE = "````"


def read_required_file(path: Path) -> str:
    """Read a required UTF-8 text file."""
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")

    return path.read_text(encoding="utf-8").strip()


def fenced_code(language: str, content: str) -> str:
    """Wrap content in a Markdown code fence."""
    return f"{CODE_FENCE}{language}\n{content}\n{CODE_FENCE}"



def build_pypi_readme() -> str:
    """Build the complete PyPI README."""
    readme = read_required_file(README_PATH)
    usage = read_required_file(USAGE_PATH)
    properties = read_required_file(PROPERTIES_PATH)
    runtime = read_required_file(RUNTIME_PATH)

    sections = [
        readme,
        "---",
        usage,
        "---",
        "# Complete Configuration Examples",
        (
            "The following examples show the complete Monitaudit "
            "configuration files."
        ),
        "## `config/monitaudit.properties`",
        fenced_code("properties", properties),
        "## `config/monitaudit.runtime`",
        fenced_code("yaml", runtime),
    ]

    return "\n\n".join(sections) + "\n"


def main() -> None:
    """Generate PYPI_README.md."""
    content = build_pypi_readme()

    OUTPUT_PATH.write_text(
        content,
        encoding="utf-8",
    )

    print(f"Generated: {OUTPUT_PATH}")
    print(f"Size     : {len(content):,} characters")


if __name__ == "__main__":
    main()