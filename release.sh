#!/usr/bin/env bash
set -e

#### Ensure we are in the project root directory

if [ ! -f "pyproject.toml" ]; then
    echo "Error: Run this script from the project root directory."
    exit 1
fi

INIT_FILE="src/monitaudit/__init__.py"
BUMP_TYPE=${1:-patch}  # Defaults to 'patch' if no argument is given 

if [ ! -f "$INIT_FILE" ]; then
echo "Error: Initialization file not found at $INIT_FILE"
exit 1
fi

#### 1. Read current version from the **init**.py file

CURRENT_VERSION=$(grep -oP '__version__\s*=\s*"\K[^"]+' "$INIT_FILE")

echo "Current version is: $CURRENT_VERSION"

#### 2. Split version into parts (Major.Minor.Patch)

IFS='.' read -r major minor patch <<< "$CURRENT_VERSION"

#### 3. Determine the new version based on the bump type parameter

if [ "$BUMP_TYPE" == "major" ]; then
    NEW_MAJOR=$((major + 1))
    NEW_VERSION="$NEW_MAJOR.0.0"
elif [ "$BUMP_TYPE" == "minor" ]; then
    NEW_MINOR=$((minor + 1))
    NEW_VERSION="$major.$NEW_MINOR.0"
elif [ "$BUMP_TYPE" == "patch" ]; then
    NEW_PATCH=$((patch + 1))
    NEW_VERSION="$major.$minor.$NEW_PATCH"
else
    echo "Error: Invalid version type '$BUMP_TYPE'."
    exit 1
fi



echo "Bumping version (\(BUMP_TYPE) to:\)NEW_VERSION"

#### 4. Run test safety checks before making any changes

echo "Running project test suite..."
if ! uv run pytest; then
    echo "❌ ERROR: Test suite failed! Aborting release process to protect production."
    exit 1
fi

#### 5. Write the new version string back to the __init__.py file cleanly
sed -i "s/__version__ = .*/__version__ = \"$NEW_VERSION\"/g" "$INIT_FILE"


#### 6. Clear old distributions, build, and publish safely

set -euo pipefail

rm -rf dist/

echo "Generating PyPI README..."
uv run python scripts/build_pypi_readme.py

echo "Building Monitaudit..."
uv build --wheel

echo "Validating distribution..."
uvx twine check dist/*

if [ -f ".env" ]; then
    echo "Loading PyPI credentials..."
    set -a
    source .env
    set +a
fi

if [ -z "${PYPI_API_TOKEN:-}" ]; then
    echo "Error: PYPI_API_TOKEN is not set."
    exit 1
fi

echo "Publishing Monitaudit ${NEW_VERSION}..."
uv publish --token "$PYPI_API_TOKEN" dist/*.whl

echo "Success! Monitaudit ${NEW_VERSION} is published."