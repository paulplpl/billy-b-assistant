import os
import sys


# Ensure project root for `core` package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Import core config after path setup
# Import providers to register them
from core import config as core_config
from core.realtime_ai_provider import voice_provider_registry


# Export core_config for use in server.py
__all__ = ['core_config', 'voice_provider_registry']
