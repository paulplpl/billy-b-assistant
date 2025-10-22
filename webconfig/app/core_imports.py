import os
import sys


# Ensure project root for `core` package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Import core config after path setup
from core import config as core_config


# Export core_config for use in server.py
__all__ = ['core_config']
