"""
Base tools that work with any realtime conversation provider.
These are the custom Billy functions.
"""

from typing import Any

from .config import PERSONALITY
from .song_manager import song_manager


def get_base_tools() -> list[dict[str, Any]]:
    """Get the base tools that work with any provider"""
    return [
        {
            "name": "update_personality",
            "type": "function",
            "description": "Adjusts Billy's personality traits. Accepts numeric values (0-100) or level names (min/low/med/high/max). Call this function when users request personality changes.",
            "parameters": {
                "type": "object",
                "properties": {
                    **{
                        trait: {
                            "oneOf": [
                                {"type": "integer", "minimum": 0, "maximum": 100},
                                {
                                    "type": "string",
                                    "enum": ["min", "low", "med", "high", "max"],
                                },
                            ]
                        }
                        for trait in vars(PERSONALITY)
                    }
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "play_song",
            "type": "function",
            "description": song_manager.get_dynamic_tool_description(),
            "parameters": {
                "type": "object",
                "properties": {"song": {"type": "string"}},
                "required": ["song"],
            },
        },
        {
            "name": "smart_home_command",
            "type": "function",
            "description": "Send a DIRECT command to Home Assistant (e.g., 'Turn on lights', 'Set temperature to 72'). **CRITICAL: Only call this for DIRECT commands. If the user asks you to ASK/CHECK/CONFIRM first (e.g., 'ask if lights should be on'), do NOT call this function - just speak the question and wait for their answer.**",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The DIRECT command to send to Home Assistant (not a question)",
                    }
                },
                "required": ["prompt"],
            },
        },
        {
            "name": "conversation_state",
            "type": "function",
            "description": "MANDATORY: MUST CALL AFTER EVERY RESPONSE. Call this INTERNAL FUNCTION (do not speak it) at the end of your turn to indicate conversation state. Set expects_follow_up=true if you asked a question or need user input, false for complete statements. CRITICAL: NEVER call this as your ONLY response - you MUST generate spoken audio first, then call this function. If audio is unclear, say 'I didn't catch that' before calling this.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expects_follow_up": {"type": "boolean"},
                    "suggested_prompt": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["expects_follow_up"],
            },
        },
        {
            "name": "identify_user",
            "type": "function",
            "description": "Call this ONLY when someone explicitly introduces themselves by stating their own name (e.g., 'I am Tom', 'My name is Sarah', 'Hey billy it is tom'). Do NOT call this when someone greets you by name (like 'Hello Billy' or 'Hey Billy'). Only call when they are telling you their own name to switch from guest mode to user mode. IMPORTANT: If you're uncertain about the spelling of a name (e.g., 'Thom' vs 'Tom', 'Sarah' vs 'Sara'), set confidence to 'low' to trigger spelling confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name the user provided",
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "How confident you are about the name spelling",
                    },
                    "context": {
                        "type": "string",
                        "description": "Any additional context about how they introduced themselves",
                    },
                },
                "required": ["name", "confidence"],
            },
        },
        #New tools
        {
        "name": "music_command",
        "type": "function",
        "description": "Control music playback on Billy via Home Assistant (through MQTT).",
        "parameters": {
            "type": "object",
            "properties": {
            "action": {"type": "string", "enum": ["play","stop","pause","resume","next","prev","vol_up","vol_down","volume_set"]},
            "query": {"type": "string"},
            "step": {"type": "number"},
            "level": {"type": "number"}
            },
            "required": ["action"]
        }
        },
        {
        "name": "web_lookup",
        "type": "function",
        "description": "Fetch up-to-date info from the internet for questions that need current data.",
        "parameters": {
          "type": "object",
          "properties": {
            "query": {"type": "string"}
          },
          "required": ["query"]
        }
        },
    ]


def get_user_tools() -> list[dict[str, Any]]:
    """Get user-specific tools (only available when not in guest mode)"""
    return [
        {
            "name": "store_memory",
            "type": "function",
            "description": "Store lasting preferences, facts, and interests that users VOLUNTARILY share. **CRITICAL: DO NOT STORE answers to YOUR OWN questions!** If you just asked a question, the answer is NOT a memory. Store ONLY when: (1) User volunteers info unprompted, OR (2) Info is NOT answering your question. Examples: WRONG: You: 'What cheese?' User: 'Gruyère' -> DO NOT STORE (answering your question). CORRECT: User: 'I love Gruyère cheese' -> DO STORE (volunteered). Call BEFORE responding with speech when appropriate.",
            "parameters": {
                "type": "object",
                "properties": {
                    "memory": {
                        "type": "string",
                        "description": "The memory or fact to store about the user",
                    },
                    "importance": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "How important this memory is",
                    },
                    "category": {
                        "type": "string",
                        "enum": [
                            "preference",
                            "fact",
                            "event",
                            "relationship",
                            "interest",
                        ],
                        "description": "Category of the memory",
                    },
                },
                "required": ["memory", "importance", "category"],
            },
        },
        {
            "name": "manage_profile",
            "type": "function",
            "description": "Manage user profile settings and preferences",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["create", "update", "switch_persona", "get_info"],
                        "description": "Action to perform on the profile",
                    },
                    "preferred_persona": {
                        "type": "string",
                        "description": "User's preferred Billy personality",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Additional notes about the user",
                    },
                },
                "required": ["action"],
            },
        },
        {
            "name": "switch_persona",
            "type": "function",
            "description": "Switch Billy's persona mid-session and acknowledge the change",
            "parameters": {
                "type": "object",
                "properties": {
                    "persona": {
                        "type": "string",
                        "description": "The persona to switch to",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Optional reason for the persona switch",
                    },
                },
                "required": ["persona"],
            },
        },
    ]
