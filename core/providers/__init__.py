from ..logger import logger

logger.verbose("Importing core.providers")
# Register realtime AI providers
from .openai_provider import OpenAIProvider
from .xai_provider import XAIProvider
from ..realtime_ai_provider import voice_provider_registry
from ..config import OPENAI_API_KEY, OPENAI_MODEL, REALTIME_AI_PROVIDER, XAI_API_KEY

logger.verbose(f"OPENAI_API_KEY set: {bool(OPENAI_API_KEY)}")
logger.verbose(f"XAI_API_KEY set: {bool(XAI_API_KEY)}")
logger.verbose(f"REALTIME_AI_PROVIDER: {REALTIME_AI_PROVIDER}")

if OPENAI_API_KEY:
    openai_provider = OpenAIProvider(api_key=OPENAI_API_KEY, model=OPENAI_MODEL)
    voice_provider_registry.register_provider(openai_provider)

if XAI_API_KEY:
    xai_provider = XAIProvider(api_key=XAI_API_KEY)
    voice_provider_registry.register_provider(xai_provider)

# Set the default provider based on configuration
if REALTIME_AI_PROVIDER:
    voice_provider_registry.set_default_provider(REALTIME_AI_PROVIDER)
elif OPENAI_API_KEY and not XAI_API_KEY:
    voice_provider_registry.set_default_provider("openai")
elif XAI_API_KEY and not OPENAI_API_KEY:
    voice_provider_registry.set_default_provider("xai")
else:
    raise ValueError("At least one provider API key must be set!")
