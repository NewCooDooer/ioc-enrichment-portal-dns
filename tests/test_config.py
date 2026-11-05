"""The web page must only listen on this computer (Streamlit's default is every network interface)."""

import tomllib
from pathlib import Path

CONFIG = Path(__file__).resolve().parent.parent / ".streamlit" / "config.toml"


def test_frontend_listens_on_localhost_only():
    config = tomllib.loads(CONFIG.read_text())
    assert config["server"]["address"] == "127.0.0.1"


def test_backend_default_is_also_localhost_only():
    from backend.app import config

    assert config.BACKEND_HOST == "127.0.0.1"
