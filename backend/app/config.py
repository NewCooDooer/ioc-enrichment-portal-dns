"""Settings read from environment variables or an optional .env file (never from code)."""

import os

from dotenv import load_dotenv

load_dotenv()

BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8010"))

SOURCE_TIMEOUT_SECONDS = 10.0
USER_AGENT = "ioc-enrichment-portal-dns/0.1 (training project)"
DOH_URL = "https://dns.google/resolve"
