import asyncio
import base64
import json
import os
import socket
import time
from typing import Any

import numpy as np
import websockets.asyncio.client
import websockets.exceptions

from . import audio
from .config import (
    CHUNK_MS,
    DEBUG_MODE,
    DEBUG_MODE_INCLUDE_DELTA,
    INSTRUCTIONS,
    MIC_TIMEOUT_SECONDS,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    PERSONALITY,
    RUN_MODE,
    SILENCE_THRESHOLD,
    TEXT_ONLY_MODE,
    TURN_EAGERNESS,
    VOICE,
)
from .ha import send_conversation_prompt
from .mic import MicManager
from .movements import move_tail_async, stop_all_motors
from .mqtt import mqtt_publish
from .personality import update_persona_ini


TOOLS = [
    {
        "name": "update_personality",
        "type": "function",
        "description": "Adjusts Billy's personality traits",
        "parameters": {
            "type": "object",
            "properties": {
                trait: {"type": "integer", "minimum": 0, "maximum": 100}
                for trait in vars(PERSONALITY)
            },
        },
    },
    {
        "name": "play_song",
        "type": "function",
        "description": "Plays a special Billy song based on a given name.",
        "parameters": {
            "type": "object",
            "properties": {"song": {"type": "string"}},
            "required": ["song"],
        },
    },
    {
        "name": "smart_home_command",
        "type": "function",
        "description": "Send a natural language prompt to the Home Assistant conversation API and read back the response.",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The command to send to Home Assistant",
                }
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "follow_up_intent",
        "type": "function",
        "description": "Call at the end of your turn to indicate if you expect a user reply now.",
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
]


class BillySession:
    def __init__(
        self,
        interrupt_event=None,
        *,
        kickoff_text: str | None = None,
        kickoff_kind: str = "literal",  # "literal" | "prompt" | "raw"
        kickoff_to_interactive: bool = False,  # immediately open-mic after kickoff
        autofollowup: str = "auto",  # "auto" | "never" | "always"
    ):
        self.ws = None
        self.ws_lock: asyncio.Lock = asyncio.Lock()
        self.loop = None
        self.audio_buffer = bytearray()
        self.committed = False
        self.first_text = True
        self.full_response_text = ""
        self.last_rms = 0.0
        self.last_activity = [time.time()]
        self.session_active = asyncio.Event()
        self.user_spoke_after_assistant = False
        self.allow_mic_input = True
        self.interrupt_event = interrupt_event or asyncio.Event()
        self.mic = MicManager()
        self.mic_running = False
        self.mic_timeout_task: asyncio.Task | None = None

        # Track whenever a session is updated after creation, and OpenAI is ready to receive voice.
        self.session_initialized = False
        self.run_mode = RUN_MODE

        # Kickoff (MQTT say)
        self.kickoff_text = (kickoff_text or "").strip() or None
        self.kickoff_kind = kickoff_kind
        self.kickoff_to_interactive = kickoff_to_interactive
        self.kickoff_first_turn_done = False

        # Follow-up
        self.autofollowup = autofollowup  # "auto" | "never" | "always"
        self.follow_up_expected = False
        self.follow_up_prompt: str | None = None

        # Tool args buffer (for streamed args)
        self._tool_args_buffer: dict[str, str] = {}

        # Turn-level flags for follow-up detection
        self._saw_transcript_delta = False
        self._turn_had_speech = False
        self._active_transcript_stream: str | None = None  # "audio" | "text"
        self._added_done_text = False

    # ---- Websocket helpers ---------------------------------------------
    async def _ws_send_json(self, payload: dict[str, Any]):
        """Send a JSON payload over the session websocket with locking.

        This method is a small convenience to avoid repeating the lock and
        json.dumps boilerplate across the codebase.
        """
        async with self.ws_lock:
            if self.ws is not None:
                await self.ws.send(json.dumps(payload))

    # ---- Message type constants ----------------------------------------
    AUDIO_OUT_TYPES = {
        "response.output_audio",
        "response.output_audio.delta",
    }
    TRANSCRIPT_DELTA_TYPES = {
        "response.output_audio_transcript.delta",
        "response.audio_transcript.delta",
        "response.text.delta",
    }
    TRANSCRIPT_DONE_TYPES = {
        "response.output_audio_transcript.done",
        "response.audio_transcript.done",
        "response.text.done",
    }

    # ---- Private handlers -----------------------------------------------
    def _on_response_created(self):
        self._saw_transcript_delta = False
        self._turn_had_speech = False
        self.follow_up_expected = False
        self.follow_up_prompt = None
        self._active_transcript_stream = None
        self._added_done_text = False
        self._saw_follow_up_call = False

    def _on_input_speech_started(self):
        self.committed = False

    def _on_transcript_done(self, data: dict[str, Any]):
        transcript = data.get("transcript") or data.get("text") or ""
        if transcript and not self._saw_transcript_delta and not self._added_done_text:
            self.full_response_text += transcript
            self._added_done_text = True
        self.full_response_text += "\n\n"
        if DEBUG_MODE:
            print(f"\n📝 transcript(done): {transcript!r}")

    def _on_audio_out(self, data: dict[str, Any]):
        if TEXT_ONLY_MODE:
            return
        self._turn_had_speech = True
        audio_b64 = data.get("audio") or data.get("delta")
        if audio_b64:
            audio_chunk = base64.b64decode(audio_b64)
            self.audio_buffer.extend(audio_chunk)
            self.last_activity[0] = time.time()
            audio.playback_queue.put(audio_chunk)

            if self.interrupt_event.is_set():
                print("⛔ Assistant turn interrupted. Stopping response playback.")
                while not audio.playback_queue.empty():
                    try:
                        audio.playback_queue.get_nowait()
                        audio.playback_queue.task_done()
                    except Exception:
                        break
                self.session_active.clear()
                self.interrupt_event.clear()

    def _on_transcript_delta(self, t: str, data: dict[str, Any]):
        # Choose a single transcript stream per turn to avoid duplicates
        if t.startswith("response.output_audio_transcript") or t.startswith(
            "response.audio_transcript"
        ):
            stream = "audio"
        else:
            stream = "text"
        if self._active_transcript_stream is None:
            self._active_transcript_stream = stream
        elif stream != self._active_transcript_stream:
            return
        self._turn_had_speech = True
        self._saw_transcript_delta = True
        self.allow_mic_input = False
        if self.first_text:
            mqtt_publish("billy/state", "speaking")
            print("\n🐟 Billy: ", end="", flush=True)
            self.first_text = False
            self.user_spoke_after_assistant = False
        print(data.get("delta", ""), end="", flush=True)
        self.full_response_text += data.get("delta", "")

    def _on_tool_args_delta(self, data: dict[str, Any]):
        name = data.get("name")
        if name:
            self._tool_args_buffer.setdefault(name, "")
            self._tool_args_buffer[name] += data.get("arguments", "")

    async def _handle_follow_up_intent(self, raw_args: str | None):
        raw_args = raw_args or "{}"
        try:
            args = json.loads(raw_args)
        except Exception as e:
            print(
                f"\n⚠️ follow_up_intent: failed to parse arguments: {e} | raw={raw_args!r}"
            )
            args = {}

        self.follow_up_expected = bool(args.get("expects_follow_up", False))
        self.follow_up_prompt = args.get("suggested_prompt") or None
        reason = args.get("reason")
        self._saw_follow_up_call = True

        if DEBUG_MODE:
            print(
                "\n🧭 follow_up_intent"
                f" | expects_follow_up={self.follow_up_expected}"
                f" | suggested_prompt={self.follow_up_prompt!r}"
                f" | reason={reason!r}"
            )

    async def _handle_update_personality(self, raw_args: str | None):
        args = json.loads(raw_args or "{}")
        changes = []
        for trait, val in args.items():
            if hasattr(PERSONALITY, trait) and isinstance(val, int):
                setattr(PERSONALITY, trait, val)
                update_persona_ini(trait, val)
                changes.append((trait, val))
        if changes:
            print("\n🎛️ Personality updated via function_call:")
            for trait, val in changes:
                print(f"  - {trait.capitalize()}: {val}%")
            print("\n🧠 New Instructions:\n")
            print(PERSONALITY.generate_prompt())

            self.user_spoke_after_assistant = True
            self.full_response_text = ""
            self.last_activity[0] = time.time()

            confirmation_text = " ".join([
                f"Okay, {trait} is now set to {val}%." for trait, val in changes
            ])
            await self._ws_send_json({
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": confirmation_text}],
                },
            })
            await self._ws_send_json({"type": "response.create"})

    async def _handle_play_song(self, raw_args: str | None):
        args = json.loads(raw_args or "{}")
        song_name = args.get("song")
        if song_name:
            print(f"\n🎵 Assistant requested to play song: {song_name} ")
            await self.stop_session()
            await asyncio.sleep(1.0)
            await audio.play_song(song_name)

    async def _handle_smart_home_command(self, raw_args: str | None):
        args = json.loads(raw_args or "{}")
        prompt = args.get("prompt")
        if not prompt:
            return
        print(f"\n🏠 Sending to Home Assistant Conversation API: {prompt} ")
        ha_response = await send_conversation_prompt(prompt)
        speech_text = None
        if isinstance(ha_response, dict):
            speech_text = ha_response.get("speech", {}).get("plain", {}).get("speech")

        if speech_text:
            print(f"🔍 HA debug: {ha_response.get('data')}")
            ha_message = f"Home Assistant says: {speech_text}"
            print(f"\n📣 {ha_message}")
            await self._ws_send_json({
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": ha_message}],
                },
            })
            await self._ws_send_json({"type": "response.create"})
        else:
            print(f"⚠️ Failed to parse HA response: {ha_response}")
            await self._ws_send_json({
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "Home Assistant didn't understand the request.",
                        }
                    ],
                },
            })
            await self._ws_send_json({"type": "response.create"})

    async def _on_tool_args_done(self, data: dict[str, Any]):
        name = data.get("name")
        raw_args = data.get("arguments")
        if not raw_args:
            raw_args = self._tool_args_buffer.pop(name, "{}")

        if name == "follow_up_intent":
            await self._handle_follow_up_intent(raw_args)
            return
        if name == "update_personality":
            await self._handle_update_personality(raw_args)
            return
        if name == "play_song":
            await self._handle_play_song(raw_args)
            return
        if name == "smart_home_command":
            await self._handle_smart_home_command(raw_args)
            return

    async def _on_response_done(self, data: dict[str, Any]):
        error = data.get("status_details", {}).get("error")
        if error:
            error_type = error.get("type")
            error_message = error.get("message", "Unknown error")
            print(f"\n❌ OpenAI API Error [{error_type}]: {error_message}")
        else:
            print("\n✿ Assistant response complete.")

        if not TEXT_ONLY_MODE:
            await asyncio.to_thread(audio.playback_queue.join)
            await asyncio.sleep(1)
            if len(self.audio_buffer) > 0:
                print(f"💾 Saving audio buffer ({len(self.audio_buffer)} bytes)")
                audio.rotate_and_save_response_audio(self.audio_buffer)
            else:
                print("⚠️ Audio buffer was empty, skipping save.")
            self.audio_buffer.clear()
            audio.playback_done_event.set()
            self.last_activity[0] = time.time()
            self.allow_mic_input = True

        # Kickoff follow-up switch
        if self.kickoff_text and not self.kickoff_first_turn_done:
            if self._turn_had_speech:
                self.kickoff_first_turn_done = True
                if self.kickoff_to_interactive:
                    print("🔁 Kickoff complete — switching to interactive mode.")
                    self._start_mic()
                    mqtt_publish("billy/state", "listening")
                elif self.autofollowup == "auto":
                    asked_question = self._wants_follow_up_heuristic()
                    wants_follow_up = self.follow_up_expected or asked_question
                    if wants_follow_up:
                        print("🔁 Auto follow-up detected — opening mic.")
                        await self._start_mic_after_playback()
                        mqtt_publish("billy/state", "listening")
                        self.user_spoke_after_assistant = False
                        self.last_activity[0] = time.time()
            else:
                if DEBUG_MODE:
                    print(
                        "ℹ️ Kickoff turn ended with no speech (tool-only). Waiting for next turn."
                    )

        if self.run_mode == "dory":
            print("🎣 Dory mode active. Ending session after single response.")
            await self.stop_session()

    # ---- Mic helpers -------------------------------------------------
    def _start_mic(self, *, retry=True):
        """
        Try to open the mic. If it fails (device busy/unavailable), optionally
        start a background retry loop with exponential backoff.
        """
        if self.mic_running or not self.session_active.is_set():
            return

        try:
            # Recreate the manager in case the previous stream left it in a bad state
            if self.mic is None:
                self.mic = MicManager()

            self.mic.start(self.mic_callback)
            self.mic_running = True
            if DEBUG_MODE:
                print("🎤 Mic started")
            if not self.mic_timeout_task or self.mic_timeout_task.done():
                self.mic_timeout_task = asyncio.create_task(self.mic_timeout_checker())

        except Exception as e:
            self.mic_running = False
            print(f"❌ Mic start failed: {e}")
            if retry and self.session_active.is_set():
                # Kick off a retry loop (non-blocking)
                asyncio.create_task(self._retry_mic_loop())

    def _stop_mic(self):
        if self.mic_running:
            try:
                self.mic.stop()
            except Exception as e:
                print(f"⚠️ Error while stopping mic: {e}")
            self.mic_running = False

    async def _retry_mic_loop(self):
        """
        Retry opening the mic a few times with backoff. Keeps the session alive
        while we wait for the input device to become available again.
        """
        if DEBUG_MODE:
            print("🔁 Mic retry loop started")

        # Small, bounded backoff: 0.5s → 1s → 2s → 2s → …
        delays = [0.5, 1.0, 2.0, 2.0, 2.0]
        for delay in delays:
            if not self.session_active.is_set():
                return

            await asyncio.sleep(delay)

            # Recreate MicManager to clear any stale PortAudio handles
            try:
                self.mic = MicManager()
            except Exception as e:
                if DEBUG_MODE:
                    print(f"⚠️ MicManager recreate failed: {e}")

            try:
                self.mic.start(self.mic_callback)
                self.mic_running = True
                if DEBUG_MODE:
                    print("✅ Mic started after retry")
                if not self.mic_timeout_task or self.mic_timeout_task.done():
                    self.mic_timeout_task = asyncio.create_task(
                        self.mic_timeout_checker()
                    )
                mqtt_publish("billy/state", "listening")
                return
            except Exception as e:
                self.mic_running = False
                print(f"❌ Mic retry failed: {e}")

        # All retries exhausted
        print("🛑 Mic unavailable after retries; keeping session but not listening.")

    # ------------------------------------------------------------------

    def _wants_follow_up_heuristic(self) -> bool:
        """
        Minimal, language-agnostic check: treat any question punctuation
        as an invitation to follow up.
        """
        txt = (self.full_response_text or "").strip()
        # Latin '?', Spanish '¿', CJK full-width '？', Arabic '؟', interrobang '‽'
        return any(ch in txt for ch in ("?", "¿", "？", "؟", "‽"))

    async def _start_mic_after_playback(
        self, delay: float = 0.6, retries: int = 3
    ) -> bool:
        """
        Open the mic a tad later (and retry) so ALSA has released devices.
        """
        for attempt in range(1, retries + 1):
            try:
                # Progressive delay: longer waits for later attempts
                if attempt > 1:
                    wait_time = delay * (attempt - 1) + 0.5
                    print(f"⏳ Waiting {wait_time:.1f}s before mic retry {attempt}...")
                    await asyncio.sleep(wait_time)

                # Ensure mic is fully stopped before retry
                if self.mic_running:
                    self.mic.stop()
                    self.mic_running = False
                    await asyncio.sleep(0.2)  # Brief pause after stop

                if not self.mic_running:
                    self.mic.start(self.mic_callback)  # may raise
                    self.mic_running = True
                    if not self.mic_timeout_task or self.mic_timeout_task.done():
                        self.mic_timeout_task = asyncio.create_task(
                            self.mic_timeout_checker()
                        )
                print(f"🎙️ Mic opened (attempt {attempt}).")
                return True
            except Exception as e:
                print(f"⚠️ Mic open failed (attempt {attempt}/{retries}): {e}")
                # For ALSA device unavailable errors, try to reset audio system
                if "Device unavailable" in str(e) and attempt < retries:
                    print("🔄 Attempting audio system reset...")
                    try:
                        import subprocess

                        subprocess.run(
                            ["sudo", "alsactl", "restore"],
                            capture_output=True,
                            timeout=5,
                        )
                        await asyncio.sleep(1.0)
                    except Exception as reset_error:
                        print(f"⚠️ Audio reset failed: {reset_error}")

        print("🛑 Mic failed to open after retries.")
        return False

    async def start(self):
        self.loop = asyncio.get_running_loop()
        print("\n⏱️ Session starting...")

        self.audio_buffer.clear()
        self.committed = False
        self.first_text = True
        self.full_response_text = ""
        self.last_activity[0] = time.time()
        self.session_active.set()
        self.user_spoke_after_assistant = False
        self.allow_mic_input = True

        async with self.ws_lock:
            if self.ws is None:
                uri = f"wss://api.openai.com/v1/realtime?model={OPENAI_MODEL}"
                headers = {
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                }

                try:
                    self.ws = await websockets.asyncio.client.connect(
                        uri, additional_headers=headers
                    )
                    await self.ws.send(
                        json.dumps({
                            "type": "session.update",
                            "session": {
                                "type": "realtime",
                                "instructions": INSTRUCTIONS,
                                "tools": TOOLS,
                                "audio": {
                                    "input": {
                                        "format": {"type": "audio/pcm", "rate": 24000},
                                        "turn_detection": {
                                            "type": "semantic_vad",
                                            "eagerness": TURN_EAGERNESS,
                                            "create_response": True,
                                            "interrupt_response": True,
                                        },
                                    },
                                    **(
                                        {
                                            "output": {
                                                "format": {
                                                    "type": "audio/pcm",
                                                    "rate": 24000,
                                                },
                                                "voice": VOICE,
                                            }
                                        }
                                        if not TEXT_ONLY_MODE
                                        else {}
                                    ),
                                },
                            },
                        })
                    )

                    # Kickoff message (from MQTT say)
                    if self.kickoff_text:
                        if self.kickoff_kind == "prompt":
                            kickoff_payload = self.kickoff_text
                        elif self.kickoff_kind == "literal":
                            kickoff_payload = (
                                "Say the user's message **verbatim**, word for word, with no additions or reinterpretation.\n"
                                "Maintain personality, but do NOT rephrase or expand.\n\n"
                                f"Repeat this literal message sent via MQTT: {self.kickoff_text}"
                                "\n\n"
                                "After you finish speaking, call `follow_up_intent` once. "
                                "If the line is not a question and needs no reply, set expects_follow_up=false."
                            )
                        else:
                            kickoff_payload = self.kickoff_text

                        await self.ws.send(
                            json.dumps({
                                "type": "conversation.item.create",
                                "item": {
                                    "type": "message",
                                    "role": "user",
                                    "content": [
                                        {"type": "input_text", "text": kickoff_payload}
                                    ],
                                },
                            })
                        )
                        await self.ws.send(json.dumps({"type": "response.create"}))

                except websockets.exceptions.ConnectionClosedError as e:
                    reason = getattr(e, "reason", str(e))
                    if "invalid_api_key" in reason:
                        await self._play_error_sound("noapikey", reason)
                    else:
                        await self._play_error_sound("error", reason)
                    return

                except socket.gaierror:
                    await self._play_error_sound(
                        "nowifi", "Network unreachable or DNS failed"
                    )
                    return

                except Exception as e:
                    await self._play_error_sound("error", str(e))
                    return

        if not TEXT_ONLY_MODE:
            audio.playback_done_event.clear()
            audio.ensure_playback_worker_started(CHUNK_MS)

        await self.run_stream()

    def mic_callback(self, indata, *_):
        if not self.allow_mic_input or not self.session_active.is_set():
            return

        # Don't send mic data until wake-up sound is finished
        if not TEXT_ONLY_MODE and not audio.playback_done_event.is_set():
            return

        # Log once when mic data starts being sent after wake-up sound
        if not hasattr(self, '_mic_data_started') and not TEXT_ONLY_MODE:
            print("🎤 Mic data now being sent (wake-up sound finished)")
            self._mic_data_started = True

        samples = indata[:, 0]
        rms = np.sqrt(np.mean(np.square(samples.astype(np.float32))))
        self.last_rms = rms

        if DEBUG_MODE:
            print(f"\r🎙 Mic Volume: {rms:.1f}     ", end='', flush=True)

        if rms > SILENCE_THRESHOLD:
            self.last_activity[0] = time.time()
            self.user_spoke_after_assistant = True

        audio.send_mic_audio(self.ws, samples, self.loop)

    async def run_stream(self):
        if not TEXT_ONLY_MODE and audio.playback_done_event.is_set():
            await asyncio.to_thread(audio.playback_done_event.wait)

        print(
            "🎙️ Mic stream active. Say something..."
            if not self.kickoff_text
            else "📣 Announcing kickoff..."
        )
        mqtt_publish(
            "billy/state", "listening" if not self.kickoff_text else "speaking"
        )

        try:
            # Start mic immediately only for non-kickoff sessions
            if not self.kickoff_text:
                self._start_mic()

            async for message in self.ws:
                if not self.session_active.is_set():
                    print("🚪 Session marked as inactive, stopping stream loop.")
                    break
                data = json.loads(message)
                if DEBUG_MODE and (
                    DEBUG_MODE_INCLUDE_DELTA
                    or not (data.get("type") or "").endswith("delta")
                ):
                    print(f"\n🔁 Raw message: {data} ")

                if data.get("type") in ("session.updated", "session_updated"):
                    self.session_initialized = True

                await self.handle_message(data)

        except Exception as e:
            print(f"❌ Error opening mic input: {e}")
            self.session_active.clear()

        finally:
            try:
                self._stop_mic()
                print("🎙️ Mic stream closed.")
            except Exception as e:
                print(f"⚠️ Error while stopping mic: {e}")

            try:
                await self.post_response_handling()
            except Exception as e:
                print(f"⚠️ Error in post_response_handling: {e}")

    async def handle_message(self, data):
        t = data.get("type") or ""

        if t == "response.created":
            self._on_response_created()
            return
        if t == "input_audio_buffer.speech_started":
            self._on_input_speech_started()
            return
        if t == "input_audio_buffer.speech_stopped":
            return
        if t in self.TRANSCRIPT_DONE_TYPES:
            self._on_transcript_done(data)
            return
        if t in self.AUDIO_OUT_TYPES:
            self._on_audio_out(data)
            return
        if t == "input_audio_buffer.committed":
            self.committed = True
            return
        if t in self.TRANSCRIPT_DELTA_TYPES and "delta" in data:
            self._on_transcript_delta(t, data)
            return
        if t == "response.function_call_arguments.delta":
            self._on_tool_args_delta(data)
            return
        if t == "response.function_call_arguments.done":
            await self._on_tool_args_done(data)
            return
        if t == "response.done":
            await self._on_response_done(data)
            return
        if t == "error":
            error: dict[str, Any] = data.get("error") or {}
            code = error.get("code", "error").lower()
            message = error.get("message", "Unknown error")
            code = "noapikey" if "invalid_api_key" in code else "error"
            print(f"\n🛑 API Error ({code}): {message}")
            await self._play_error_sound(code, message)
            return
        # else: ignore unrecognized messages silently

    async def mic_timeout_checker(self):
        print("🛡️ Mic timeout checker active")
        last_tail_move = 0

        while self.session_active.is_set():
            if not self.mic_running:
                await asyncio.sleep(0.2)
                continue

            now = time.time()
            idle_seconds = now - max(self.last_activity[0], audio.last_played_time)
            timeout_offset = 2

            if idle_seconds - timeout_offset > 0.5:
                elapsed = idle_seconds - timeout_offset
                progress = min(elapsed / MIC_TIMEOUT_SECONDS, 1.0)
                bar_len = 20
                filled = int(bar_len * progress)
                bar = "█" * filled + "-" * (bar_len - filled)
                print(
                    f"\r👂 {MIC_TIMEOUT_SECONDS}s timeout: [{bar}] {elapsed:.1f}s "
                    f"| Mic Volume:: {self.last_rms:.4f} / Threshold: {SILENCE_THRESHOLD:.4f}",
                    end="",
                    flush=True,
                )

                if now - last_tail_move > 1.0:
                    move_tail_async(duration=0.2)
                    last_tail_move = now

                if elapsed > MIC_TIMEOUT_SECONDS:
                    print(
                        f"\n⏱️ No mic activity for {MIC_TIMEOUT_SECONDS}s. Ending input..."
                    )
                    await self.stop_session()
                    break

            await asyncio.sleep(0.5)

    async def post_response_handling(self):
        print(f"\n🧠 Full response: {self.full_response_text.strip()} ")

        if not self.session_active.is_set():
            print("🚪 Session inactive after timeout or interruption. Not restarting.")
            mqtt_publish("billy/state", "idle")
            stop_all_motors()
            async with self.ws_lock:
                if self.ws:
                    await self.ws.close()
                    await self.ws.wait_closed()
                    self.ws = None
            return

        # Heuristic fallback (punctuation only)
        asked_question = self._wants_follow_up_heuristic()
        if DEBUG_MODE:
            print(
                "🧪 follow-up decision"
                f" | mode={self.autofollowup}"
                f" | tool_expects={self.follow_up_expected}"
                f" | qmark={asked_question}"
                f" | had_speech={self._turn_had_speech}"
            )

        if self.autofollowup == "always":
            wants_follow_up = True
        elif self.autofollowup == "never":
            wants_follow_up = False
        else:
            wants_follow_up = self.follow_up_expected or asked_question

        if DEBUG_MODE and not self._saw_follow_up_call:
            print("⚠️ follow_up_intent not called this turn; using heuristic instead.")

        if wants_follow_up:
            print("🔁 Follow-up expected. Keeping session open.")
            mqtt_publish("billy/state", "listening")
            await self._start_mic_after_playback()  # <-- changed
            self.user_spoke_after_assistant = False
            self.full_response_text = ""
            self.last_activity[0] = time.time()
            return

        print("🛑 No follow-up. Ending session.")
        mqtt_publish("billy/state", "idle")
        stop_all_motors()
        async with self.ws_lock:
            if self.ws:
                await self.ws.close()
                await self.ws.wait_closed()
                self.ws = None

    async def stop_session(self):
        print("🛑 Stopping session...")
        self.session_active.clear()
        self._stop_mic()

        async with self.ws_lock:
            if self.ws:
                try:
                    await self.ws.close()
                    # Add timeout to prevent hanging
                    try:
                        await asyncio.wait_for(self.ws.wait_closed(), timeout=2.0)
                    except asyncio.TimeoutError:
                        print("⚠️ Websocket close timeout, forcing cleanup")
                except Exception as e:
                    print(f"⚠️ Error closing websocket: {e}")
                finally:
                    self.ws = None

    async def request_stop(self):
        print("🛑 Stop requested via external signal.")
        self.session_active.clear()

    async def _play_error_sound(self, code: str = "error", message: str | None = None):
        """
        Play an error sound based on the provided code.
        Example:
          - "error"     → sounds/error.wav
          - "nowifi"    → sounds/nowifi.wav
          - "noapikey"  → sounds/noapikey.wav
        """
        stop_all_motors()

        filename = f"{code}.wav"
        sound_path = os.path.join("sounds", filename)

        print(f"🛑 Error ({code}): {message or 'No message'}")
        print(f"🔊 Attempting to play {filename}...")

        if os.path.exists(sound_path):
            await asyncio.to_thread(audio.enqueue_wav_to_playback, sound_path)
            await asyncio.to_thread(audio.playback_queue.join)
        else:
            print(f"⚠️ {sound_path} not found, skipping audio playback.")

        await self.stop_session()
