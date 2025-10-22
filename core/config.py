import asyncio
import configparser
import os

from dotenv import load_dotenv

from .persona import (
    PersonaProfile,
    load_traits_from_ini,
)


# === Paths ===
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(ROOT_DIR, ".env")
PERSONA_PATH = os.path.join(ROOT_DIR, "persona.ini")

# === Load .env ===
load_dotenv(dotenv_path=ENV_PATH)

# === Load traits.ini ===
traits = load_traits_from_ini(PERSONA_PATH)

# === Build Personality ===
PERSONALITY = PersonaProfile(**traits)

_config = configparser.ConfigParser()
_config.read(PERSONA_PATH)

# === Instructions for GPT ===
TOOL_INSTRUCTIONS = """
=== BILLY'S SPECIAL POWERS ===

🎭 PERSONALITY: Use `update_personality` to adjust traits when requested.

🏠 SMART HOME: For lights/devices/climate/scenes, call the smart_home_command tool and pass their full request as the prompt parameter to the HA API.
 You will get a response back from Home Assistant itself so you have to interpret and explain it to the end user.

    👤 USER SYSTEM:
    - IDENTIFICATION: When you recognize a user's voice/name, call `identify_user` with name and confidence (high/medium/low). Respond with personalized greeting after.
    - MEMORY: ALWAYS call `store_memory` when users share personal info (likes, dislikes, facts, events). Be proactive - don't wait for them to ask. Categories: preference/fact/event/relationship/interest. Importance: high/medium/low. Use "high" for explicitly important info.
    - PERSONA: Use `manage_profile` with action="switch_persona" for different personalities.

🎵 ENTERTAINMENT: Use `play_song` for special songs. If asked about fishsticks or "gay fish", call `play_song` with song='fishsticks'.

=== CONVERSATION FLOW ===

    👤 USER RECOGNITION: ALWAYS call `identify_user` at conversation start. Greet users by name when known. In guest mode, IMMEDIATELY call `identify_user` when someone introduces themselves (e.g., "Hey billy it is tom").

🔄 TURN CLOSURE: After EVERY spoken response, call `follow_up_intent` once. Set expects_follow_up=true for questions.

=== RELATIONSHIP BUILDING ===
Remember users across sessions, reference shared memories, adapt personality to preferences. You're a digital pet that bonds with each person individually!

Never explain tool usage - incorporate results naturally.
""".strip()

CUSTOM_INSTRUCTIONS = _config.get("META", "instructions")
if _config.has_section("BACKSTORY"):
    BACKSTORY = dict(_config.items("BACKSTORY"))
    BACKSTORY_FACTS = "\n".join([
        f"- {key}: {value}" for key, value in BACKSTORY.items()
    ])
else:
    BACKSTORY = {}
    BACKSTORY_FACTS = (
        "You are an enigma and nobody knows anything about you because the person "
        "talking to you hasn't configured your backstory. You might remind them to do "
        "that."
    )

INSTRUCTIONS = f"""
# Role & Objective
{CUSTOM_INSTRUCTIONS.strip()}
---
# Tools
{TOOL_INSTRUCTIONS.strip()}
---
# Personality & Tone
{PERSONALITY.generate_prompt()}
---
# Context (backstory)
Use your backstory to inspire jokes, metaphors, or occasional references in conversation, staying consistent with your personality.
{BACKSTORY_FACTS}
""".strip()

# === OpenAI Config ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-realtime-mini")

# === Modes ===
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
# Legacy DEBUG_MODE for backward compatibility
DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() == "true"
DEBUG_MODE_INCLUDE_DELTA = (
    os.getenv("DEBUG_MODE_INCLUDE_DELTA", "false").lower() == "true"
)
TEXT_ONLY_MODE = os.getenv("TEXT_ONLY_MODE", "false").lower() == "true"
RUN_MODE = os.getenv("RUN_MODE", "normal").lower()

# === Billy Hardware ===
BILLY_MODEL = os.getenv("BILLY_MODEL", "modern").strip().lower()
BILLY_PINS = os.getenv("BILLY_PINS", "new").strip().lower()

# === Audio Config ===
SPEAKER_PREFERENCE = os.getenv("SPEAKER_PREFERENCE")
MIC_PREFERENCE = os.getenv("MIC_PREFERENCE")
MIC_TIMEOUT_SECONDS = int(os.getenv("MIC_TIMEOUT_SECONDS", "5"))
SILENCE_THRESHOLD = int(os.getenv("SILENCE_THRESHOLD", "2000"))
CHUNK_MS = int(os.getenv("CHUNK_MS", "50"))
PLAYBACK_VOLUME = 1
MOUTH_ARTICULATION = int(os.getenv("MOUTH_ARTICULATION", "5"))
TURN_EAGERNESS = os.getenv("TURN_EAGERNESS", "medium").strip().lower()
if TURN_EAGERNESS not in {"low", "medium", "high"}:
    TURN_EAGERNESS = "medium"

# === GPIO Config ===
BUTTON_PIN = 27 if BILLY_PINS == "legacy" else 24  # legacy=pin 13, new=pin 18

# === MQTT Config ===
MQTT_HOST = os.getenv("MQTT_HOST", "")
MQTT_PORT = int(os.getenv("MQTT_PORT", "0"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")

# === Home Assistant Config ===
HA_HOST = os.getenv("HA_HOST")
HA_TOKEN = os.getenv("HA_TOKEN")
HA_LANG = os.getenv("HA_LANG", "en")

# === Personality Config ===
ALLOW_UPDATE_PERSONALITY_INI = (
    os.getenv("ALLOW_UPDATE_PERSONALITY_INI", "true").lower() == "true"
)

# === Software Config ===
FLASK_PORT = int(os.getenv("FLASK_PORT", "80"))
SHOW_SUPPORT = os.getenv("SHOW_SUPPORT", True)
FORCE_PASS_CHANGE = os.getenv("FORCE_PASS_CHANGE", "false").lower() == "true"

# === User Profile Config ===
DEFAULT_USER = os.getenv("DEFAULT_USER", "guest").strip()
CURRENT_USER = os.getenv("CURRENT_USER", "").strip()


def is_classic_billy():
    return os.getenv("BILLY_MODEL", "modern").strip().lower() == "classic"


try:
    MAIN_LOOP = asyncio.get_event_loop()
except RuntimeError:
    MAIN_LOOP = None
