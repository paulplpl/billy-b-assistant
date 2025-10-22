import asyncio
import base64
import json
import os
import re
import wave
from typing import Optional

import websockets.asyncio.client

from .config import CUSTOM_INSTRUCTIONS, OPENAI_API_KEY, OPENAI_MODEL


WAKEUP_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../sounds/wake-up/custom")
)
os.makedirs(WAKEUP_DIR, exist_ok=True)


def get_persona_wakeup_dir(persona_name: str) -> str:
    """Get the wake-up directory for a specific persona."""
    persona_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../personas", persona_name)
    )
    wakeup_dir = os.path.join(persona_dir, "wakeup")
    os.makedirs(wakeup_dir, exist_ok=True)
    return wakeup_dir


def slugify(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", text).strip("_").lower()


def get_wakeup_path(phrase: str) -> str:
    return os.path.join(WAKEUP_DIR, f"{slugify(phrase)}.wav")


class WakeupClipGenerator:
    def __init__(self, *, voice: Optional[str] = None, persona_name: str = "default"):
        self.persona_name = persona_name
        self.ws = None

        # Get voice from persona if not specified
        if voice:
            self.voice = voice
        else:
            try:
                from .persona_manager import persona_manager

                self.voice = persona_manager.get_persona_voice(persona_name)
            except Exception:
                self.voice = "ballad"  # Default voice

    async def _send_json(self, payload: dict):
        await self.ws.send(json.dumps(payload))

    async def generate(self, prompt: str, index: int) -> str:
        # Use appropriate directory based on persona
        if self.persona_name == "default":
            # For default persona, use the custom directory
            path = os.path.join(WAKEUP_DIR, f"{index}.wav")
        else:
            # For other personas, use persona-specific directory
            persona_wakeup_dir = get_persona_wakeup_dir(self.persona_name)
            path = os.path.join(persona_wakeup_dir, f"{index}.wav")

        uri = f"wss://api.openai.com/v1/realtime?model={OPENAI_MODEL}"
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        }

        print(f"🔊 Connecting to OpenAI realtime for: {prompt} → {index}")

        try:
            async with websockets.asyncio.client.connect(
                uri, additional_headers=headers
            ) as ws:
                self.ws = ws
                # Get current persona instructions
                try:
                    from .persona_manager import persona_manager

                    persona_instructions = persona_manager.get_persona_instructions(
                        self.persona_name
                    )
                except Exception:
                    persona_instructions = CUSTOM_INSTRUCTIONS

                await self._send_json({
                    "type": "session.update",
                    "session": {
                        "type": "realtime",
                        "instructions": (
                            "IMPORTANT: Always respond by speaking the exact user text out loud. Do not add, change or rephrase anything!\n\n"
                            + persona_instructions
                        ),
                        "audio": {
                            "input": {
                                "format": {"type": "audio/pcm", "rate": 24000},
                            },
                            "output": {
                                "format": {"type": "audio/pcm", "rate": 24000},
                                "voice": self.voice,
                            },
                        },
                    },
                })

                await self._send_json({
                    "type": "conversation.item.create",
                    "item": {
                        "type": "message",
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": "Repeat this literal message:" + prompt,
                            }
                        ],
                    },
                })

                await self._send_json({"type": "response.create"})

                audio_bytes = bytearray()
                async for message in ws:
                    data = json.loads(message)
                    t = data.get("type") or ""
                    if t in {"response.output_audio", "response.output_audio.delta"}:
                        b64 = data.get("audio") or data.get("delta")
                        if b64:
                            audio_bytes.extend(base64.b64decode(b64))
                    elif t == "response.done":
                        break

                if not audio_bytes:
                    raise RuntimeError("No audio data received from OpenAI.")

                with wave.open(path, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(24000)
                    wf.writeframes(audio_bytes)

                print(f"✅ Saved wakeup clip: {path}")
                return path

        finally:
            self.ws = None


def generate_wake_clip_async(prompt, index, persona_name="default"):
    async def _run():
        gen = WakeupClipGenerator(persona_name=persona_name)
        return await gen.generate(prompt, index)

    return asyncio.run(_run())
