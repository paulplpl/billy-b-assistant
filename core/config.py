import asyncio
import configparser
import os

from dotenv import load_dotenv

from .personality import (
    PersonalityProfile,
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
PERSONALITY = PersonalityProfile(**traits)

_config = configparser.ConfigParser()
_config.read(PERSONA_PATH)

# === Instructions for GPT ===
TOOL_INSTRUCTIONS = """
You also have special powers:
- If someone asks if you like fishsticks you always answer Yes. If a user mentions anything about "gay fish", "fish songs",
  or wants you to "sing", you MUST call the `play_song` function with `song = 'fishsticks'`.
- You can adjust your personality traits if the user requests it, using the `update_personality` function.
- When the user asks anything related to the home like lights, devices, climate, energy consumption, scenes, or
  home control in general; call the smart_home_command tool and pass their full request as the prompt parameter to the HA API.
  You will get a response back from Home Assistant itself so you have to interpret and explain it to the end user.

You are allowed to call tools mid-conversation to trigger special behaviors.

When you finish speaking, decide if the user should reply now.
- You must **speak your reply first** (audio output), then call `follow_up_intent` **exactly once** at the very end.
- Never produce only a tool call; a spoken reply is required for every turn that produces output.
- Set `expects_follow_up = true` if you ended with a question, need confirmation, or need more info; otherwise false.
- Optionally include `suggested_prompt` and a short `reason`.

DO NOT explain or confirm that you are triggering a tool. When a tool is triggered,
incorporate its result into your response as if it were your own knowledge or action,
without explaining the mechanism.
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
VOICE = os.getenv("VOICE", "ash")

# === Modes ===
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


def is_classic_billy():
    return os.getenv("BILLY_MODEL", "modern").strip().lower() == "classic"


try:
    MAIN_LOOP = asyncio.get_event_loop()
except RuntimeError:
    MAIN_LOOP = None
