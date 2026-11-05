"""Settings read from environment variables or an optional .env file (never from code).

The *_URL values default to the real services. They can be overridden only to make a source fail
on purpose (e.g. CRTSH_URL=http://127.0.0.1:9/ gives "connection refused"); the running portal never mocks a source.
"""

import os

from dotenv import load_dotenv

load_dotenv()

BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8010"))

SOURCE_TIMEOUT_SECONDS = float(os.getenv("SOURCE_TIMEOUT_SECONDS", "10"))
# crt.sh is slow (a good answer took ~16 s on 2026-11-05), so it gets its own, longer timeout.
CRTSH_TIMEOUT_SECONDS = float(os.getenv("CRTSH_TIMEOUT_SECONDS", "25"))

USER_AGENT = "ioc-enrichment-portal-dns/0.1 (training project)"
DOH_URL = os.getenv("DOH_URL", "https://dns.google/resolve")
RDAP_URL = os.getenv("RDAP_URL", "https://rdap.org").rstrip("/")
CRTSH_URL = os.getenv("CRTSH_URL", "https://crt.sh").rstrip("/")
