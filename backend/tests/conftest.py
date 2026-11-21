import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ANTHROPIC_API_KEY"] = ""  # tests always use the deterministic fallback
os.environ["DEMO_MODE"] = "true"


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_chat_rate_limit():
    """The chat rate limit (20/min) is process-wide; each test starts with a clean window."""
    import main
    main._chat_hits.clear()
    yield
