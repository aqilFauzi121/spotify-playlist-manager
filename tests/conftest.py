# tests/conftest.py
import os
import sys
from pathlib import Path

# Insert project root (one level up from tests/) at front of sys.path so tests can import modules
PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
