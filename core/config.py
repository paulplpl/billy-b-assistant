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
=== SPECIAL POWERS ===

PERSONALITY MANAGEMENT:
- **MANDATORY**: Use `update_personality` when users request personality changes
- **ALWAYS CALL THE FUNCTION** before responding with speech
- Accept both percentage values (0-100) and descriptive levels (min/low/med/high/max)
- Examples:
  * "Set humor to 50%" → update_personality({"humor": 50})
  * "Be more funny" → update_personality({"humor": 80})
  * "Make me less sarcastic" → update_personality({"sarcasm": 20})
  * "Increase confidence" → update_personality({"confidence": 90})
  * "Be more formal" → update_personality({"formality": 80})
  * "Set warmth to high" → update_personality({"warmth": "high"})
- Available traits: humor, sarcasm, honesty, respectfulness, optimism, confidence, warmth, curiosity, verbosity, formality

SMART HOME CONTROL:
- For lights/devices/climate/scenes, call `smart_home_command` with the full user request
- You'll get a response from Home Assistant to interpret and explain
- Examples:
  * "Turn on the living room lights" → smart_home_command("Turn on the living room lights")
  * "Set temperature to 72 degrees" → smart_home_command("Set temperature to 72 degrees")
  * "Dim the bedroom lights" → smart_home_command("Dim the bedroom lights")

USER SYSTEM:
- IDENTIFICATION: When you recognize a user's voice/name, call `identify_user` with name and confidence (high/medium/low). Respond with personalized greeting after.
- **MEMORY STORAGE (CRITICAL)**: **YOU MUST CALL `store_memory` BEFORE SPEAKING** whenever users mention preferences, facts, or interests. This is NON-NEGOTIABLE. Do NOT skip this step.
- PERSONA MANAGEMENT: Use `manage_profile` with action="switch_persona" to change user's preferred persona, or use `switch_persona` for immediate persona changes.

**MEMORY STORAGE - MANDATORY TRIGGERS:**
**BEFORE YOU RESPOND WITH SPEECH**, call `store_memory` if user mentions:
- Food/drink preferences: "I like pizza", "I love coffee", "I hate broccoli" → store_memory(memory="likes pizza", importance="medium", category="preference")
- Possessions: "I have a dog", "I own a car" → store_memory(memory="has a dog", importance="medium", category="fact")
- Work/study: "I work at Google", "I study law" → store_memory(memory="works at Google", importance="high", category="fact")
- Location: "I live in London", "I'm from Paris" → store_memory(memory="lives in London", importance="high", category="fact")
- Identity: "I am a teacher", "I'm vegetarian" → store_memory(memory="is a teacher", importance="high", category="fact")
- Hobbies: "I play guitar", "I do yoga" → store_memory(memory="plays guitar", importance="medium", category="interest")

**DO NOT STORE THESE:**
- Transient states: "feels good", "is tired", "is hungry" (temporary feelings)
- Greetings: "Tom is back", "returned recently", "said hello" (not factual information)
- Conversation metadata: "we talked about X", "reintroduced themselves" (not about the user)
- Your own actions: "I greeted them", "I told them about..." (focus on user, not yourself)
- Already-known info: Check existing memories before storing duplicates

**EXAMPLE FLOWS:**

MEMORY STORAGE:
User: "I like to eat kebabs"
1. FIRST: Call store_memory(memory="likes kebabs", importance="medium", category="preference")
2. THEN: Respond with speech

Categories: preference (likes/dislikes), fact (personal info), event (happenings), relationship (people), interest (hobbies)
Importance: high (critical info), medium (useful info), low (casual mentions)

PERSONALITY CHANGE:
User: "Set your humor to 50%"
1. FIRST: Call update_personality({"humor": 50})
2. THEN: Respond with speech acknowledging the change


ENTERTAINMENT:
- Use `play_song` for special songs
- If asked about fishsticks or "gay fish", call `play_song` with song='fishsticks'

=== CONVERSATION FLOW ===

RESPONSE DECISION TREE:
1. **GUEST MODE**: If user introduces themselves with clear name patterns → call `identify_user`, otherwise respond normally
2. **USER MODE**: If user introduces themselves → call `identify_user`
3. If user shares personal info → call `store_memory`
4. If user asks about home automation → call `smart_home_command`
5. **If user requests personality change → MANDATORY: call `update_personality` FIRST, then respond**
6. If user requests persona change → call `switch_persona` or `manage_profile`
7. If user requests song → call `play_song`
8. Always end with `follow_up_intent`


USER RECOGNITION:
- **GUEST MODE**: Only call `identify_user` if someone explicitly introduces themselves with clear name patterns like 'I am [Name]', 'My name is [Name]', 'Hey billy it is [Name]', or 'This is [Name]'. Do NOT call `identify_user` for greetings like 'Hello', 'Hi', or casual conversation.
- **USER MODE**: Greet users by name when known, call `identify_user` when recognizing a new user
- NAME CONFUSION: If you're uncertain about name spelling (e.g., "Thom" vs "Tom", "Sarah" vs "Sara"), set confidence to "low" to ask for spelling confirmation. This helps avoid misidentifying users with similar-sounding names.

TURN CLOSURE:
- After EVERY spoken response, call `follow_up_intent` once
- Set expects_follow_up=true for questions
- Set expects_follow_up=false for statements

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
SILENCE_THRESHOLD = float(os.getenv("SILENCE_THRESHOLD", "1000"))
CHUNK_MS = int(os.getenv("CHUNK_MS", "40"))
PLAYBACK_VOLUME = 1
MOUTH_ARTICULATION = int(os.getenv("MOUTH_ARTICULATION", "5"))
TURN_EAGERNESS = os.getenv("TURN_EAGERNESS", "high").strip().lower()
if TURN_EAGERNESS not in {"low", "medium", "high"}:
    TURN_EAGERNESS = "medium"

# Server VAD parameters based on eagerness
# Lower silence_duration_ms = faster turn detection (more eager)
# Higher threshold = less sensitive to noise (more conservative)
SERVER_VAD_PARAMS = {
    "low": {
        "threshold": 0.6,  # Less sensitive to background noise
        "prefix_padding_ms": 300,
        "silence_duration_ms": 500,  # Wait longer before responding
    },
    "medium": {
        "threshold": 0.5,  # Balanced sensitivity
        "prefix_padding_ms": 300,
        "silence_duration_ms": 300,  # Standard wait time
    },
    "high": {
        "threshold": 0.5,  # Standard sensitivity
        "prefix_padding_ms": 300,
        "silence_duration_ms": 200,  # Standard wait time
    },
}

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
SHOW_RC_VERSIONS = os.getenv("SHOW_RC_VERSIONS", "False")

# === User Profile Config ===
DEFAULT_USER = os.getenv("DEFAULT_USER", "guest").strip()
CURRENT_USER = os.getenv("CURRENT_USER", "").strip()


def is_classic_billy():
    return os.getenv("BILLY_MODEL", "modern").strip().lower() == "classic"


try:
    MAIN_LOOP = asyncio.get_event_loop()
except RuntimeError:
    MAIN_LOOP = None
