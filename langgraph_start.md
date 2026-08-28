$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:UV_CACHE_DIR = "$PWD\.uv-cache"
uv run langgraph dev
Branch yxh