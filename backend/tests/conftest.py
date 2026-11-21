import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ANTHROPIC_API_KEY"] = ""  # tests always use the deterministic fallback
os.environ["DEMO_MODE"] = "true"
