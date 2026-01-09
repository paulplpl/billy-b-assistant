import os
import sys


# Ensure project root for `core` package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Import core config after path setup
from core import config as core_config
from core.realtime_ai_provider import voice_provider_registry

# Import providers to register them
import core.providers


# Export core_config for use in server.py
__all__ = ['core_config', 'voice_provider_registry']
