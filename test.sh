find . -type d -name '__pycache__' -prune -exec rm -rf {} 
rm -rf .mypy_cache .pytest_cache

uv run pytest

uv run mypy --no-incremental \
    src/monitaudit \
    tests

uv run pyright
