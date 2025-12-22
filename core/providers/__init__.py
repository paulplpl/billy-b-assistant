# Register realtime AI providers
print("DEBUG: Importing core.providers")
from .openai_provider import OpenAIProvider
from ..realtime_ai_provider import voice_provider_registry
from ..config import OPENAI_API_KEY, OPENAI_MODEL, REALTIME_AI_PROVIDER

print(f"DEBUG: OPENAI_API_KEY set: {bool(OPENAI_API_KEY)}")
print(f"DEBUG: REALTIME_AI_PROVIDER: {REALTIME_AI_PROVIDER}")

# Register the OpenAI provider if API key is available
if OPENAI_API_KEY:
    openai_provider = OpenAIProvider(api_key=OPENAI_API_KEY, model=OPENAI_MODEL)
    voice_provider_registry.register_provider(openai_provider)

# Set the default provider based on configuration
try:
    voice_provider_registry.set_default_provider(REALTIME_AI_PROVIDER)
    print("DEBUG: Providers registered successfully")
except ValueError as e:
    print(f"Warning: Invalid REALTIME_AI_PROVIDER '{REALTIME_AI_PROVIDER}', using default provider. Error: {e}")
    # Keep the default provider that was set during registration (first registered provider)