#!/usr/bin/env bash

set -e
PKG_NAME="monitaudit"
echo "Creating Python package structure for: ${PKG_NAME}..."

# 1. Create directory structure

mkdir -p src/${PKG_NAME}
mkdir -p tests

# 2. Initialize minimal source files

touch src/${PKG_NAME}/init.py
touch src/${PKG_NAME}/core.py
touch tests/init.py
touch tests/test_core.py
touch README.md
touch .gitignore

# 3. Populate pyproject.toml cleanly (no hidden spaces)

cat << 'EOF' > pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
[project]
name = "monitaudit"
version = "0.1.0"
description = "A lightweight, low-overhead Python framework for real-time log monitoring and structured system auditing."
readme = "README.md"
requires-python = ">=3.14"
license = { text = "MIT" }
keywords = ["logging", "monitoring", "audit-trail", "telemetry", "observability"]
authors = [
{ name = "Informatie", email = "informatie@nednazit.nl" }
]
classifiers = [
"Development Status :: 3 - Alpha",
"Intended Audience :: Developers",
"License :: OSI Approved :: MIT License",
"Programming Language :: Python :: 3",
"Topic :: System :: Monitoring",
"Topic :: System :: Logging",
]
dependencies = []
[project.urls]
Homepage = "https://github.com/informatie/monitaudit"
Issues = "https://github.com/informatie/monitaudit/issues"
EOF

# 4. Populate a standard Python .gitignore layout

cat << 'EOF' > .gitignore
pycache/
*.py[cod]
*$py.class
.venv/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST
.pytest_cache/
.uv/
EOF
echo "Done! Run 'uv sync' to initialize your workspace environment."

