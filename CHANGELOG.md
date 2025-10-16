# Changelog

All notable changes to this project will be documented in this file.

---

## [1.0.0] — 2025-05-25
### Initial Version
**Core Functionality**
- Real-time, full-duplex voice assistant powered by OpenAI GPT-4o.
- Assistant input/output using `sounddevice` with a push-button session trigger.
- Streaming response handling with chunked playback and lip-syncing via RMS analysis.
- Motor control using Raspberry Pi GPIO:
    - PWM-based mouth movement synchronized to speech.
    - Head and tail motion via H-bridge motor drivers.

**Personality System**
- Configurable personality traits via `persona.ini` with real-time runtime updates using function calling.
- Trait categories include: `humor`, `sarcasm`, `honesty`, `confidence`, `verbosity`, `curiosity`, and more.
- Backstory and behavioral instructions stored in `persona.ini` with structured `[PERSONALITY]`, `[BACKSTORY]`, and `[META]` sections.

**Hardware & Setup**
- 3D-printable backplate to mount USB microphone and speaker in the Billy Bass enclosure.
- GPIO safe boot state configuration to prevent motor activation during Pi startup.
- Systemd integration (`billy.service`) for background operation and autostart at boot.

**Audio System**
- Configurable voice model (`VOICE`) via `.env` file.
- Adjustable silence threshold and mic timeout for voice session logic.

**MQTT Integration (Optional)**
- Basic MQTT connectivity for status reporting, safe shutdown Raspberry Pi command and future integration with Home Assistant.

**Song Mode**
- Folder-based song playback system supporting:
    - `full.wav` for audio
    - `vocals.wav` and `drums.wav` for animated flapping (mouth and tail)
    - `metadata.txt` to control animation timing and motion profiles
- Function-calling support to trigger songs via conversation with Billy.

## [1.1.0] — 2025-07-18
### Adds initial version of Home Assistant API integration and major stability improvements.

### Added

- Initial integration with Home Assistant's conversation API.
- Graceful fallback when Home Assistant is not configured.
- New environment variable `ALLOW_UPDATE_PERSONALITY_INI` to prevent users from permanently changing Billy's personality traits.
- Wake-up audio now blocks the assistant from listening until playback is complete.
- Retain reference to mic checker task to avoid premature destruction.
- Added Ruff linter with configuration and a pre-commit hook.
- Added `CHANGELOG.md`.

### Changed

- Audio session now ensures WebSocket session is created before sending audio.
- All audio sends are awaited to prevent race conditions.
- WebSocket connections now use additional mutex locking to avoid lifecycle errors.
- Improved full audio transcript logging with newlines.
- Error responses from the assistant API are now shown clearly in the output stream.
- Cleaned up import statements and used proper relative imports.
- MQTT logic now checks if MQTT is configured before sending or receiving.

### Fixed

- Fixed race condition where audio might be sent before the session is initialized.
- Prevented audio from being interpreted when `self.ws` is unexpectedly reset.
- Suppressed redundant session-end output.
- Addressed expected `CancelledError` when stopping sessions.
- Removed duplicate and unused imports and functions.
- Removed duplicate `aiohttp` dependency from `requirements.txt`.
- Fixed potential undefined variable.
- Fixed usage of legacy `websockets` API.
- Added missing dependencies: `aiohttp`, `lgpio`.

## [1.2.0] — 2025-07-24

### Web UI 

### Added
- Web-based user interface for easy configuration of Billy
  - Versioning check logic during boot & button to trigger OTA update
  - Speaker volume test and control in UI.
  - Tailwind CSS included locally for styling.
  - Password field visibility toggles in the UI.
  - Dropdown for selecting voice options in UI.
  - Mic input and speaker output level test utility.
- Option to change openAI Model
- Compatibilty for Classic Billy Model with 3 motors

### Improved
- Folder structure simplified and clarified.
- Automatic creation of `.env` and `persona.ini` from *.example files on first run.
- Committed `persona.ini`; now ignored by `.gitignore`.

### Added in beta
- MQTT "say" command integration for announcing messages
- Systemd service install process.
- Wi-Fi onboarding form (captive portal)

## [1.3.0] — 2025-07-28

### Added

- **'Dory' Mode**: Optional single-response mode where Billy answers only once before ending the session. (requested by @kenway33 )
- **Motor Test UI**: New motor test buttons in the Hardware tab allow triggering mouth and head/tail motion directly from the web interface. (requested by @henrym9)
- **Hostname + Port Configuration**: Added settings for customizing the device's hostname and Flask web port via UI. (requested by @cprasmu)
- **Import/Export**: Added ability to upload/download both `.env` and `persona.ini` files from the web UI.

### Changed

- Improved internal JS structure and modularization.
- Minor refinements to input label styling.
- Improved UX:
  - Added collapsible UI sections
  - **Reduced Motion Mode**: New UI toggle to disable animations and backdrop blur for accessibility or preference. Setting persists in local storage.
  - **Tooltips**: Informational tooltips added to multiple UI elements for better user guidance.

### Fixed

- **Motor Retract Fix**: Ensures Billy's head reliably returns to neutral after session ends.

## [1.3.1] — 2025-08-19

### Added

- **Shutdown and restart**: Added raspberry pi shutdown and restart buttons in the UI (contribution by @cprasmu )

## [1.4.0] — 2025-09-04

### Added

- **Say command**: Added a MQTT command to let billy announce messages, either as literal sentences or as prompts.
- **Custom Wake-up Sounds**: Custom Wake-up sounds can now be customised and generated via the UI
- **New gpt-realtime model**: Added Support for the new stable release of the openAI Realtime API model.
- **Favicon**: No more 404

### Changed

- Improved update process by re-installing python requirements on software update
- Updated personality traits prompt to be more descriptive and more distinct.
- Disabled Flask debug mode by default.

## [1.5.0] — 2025-10-13

>### ⚠️ For existing builds of Billy: ⚠️ 
> 
> **Please select the Legacy Pin Layout in the Hardware Settings tab of the Web UI if you can't switch to the new unified wiring layout (see [BUILDME.md](./docs/BUILDME.md#from-motor-driver-to-raspberry-pi-gpio-pinout))**

### Added
- **Configurable Pin Layouts:** Introduced `BILLY_PINS` Pin Layout setting (`new` / `legacy`) to switch between the new (default) pin layout and the legacy pin layout (for builds before october '25)
- **Mouth Articulation Control:** Added `MOUTH_ARTICULATION` (1–10) setting to fine-tune speech motion responsiveness.
- **Error Sound Handling:**  Centralized error playback — now plays `error.wav`, `noapikey.wav`, or `nowifi.wav` depending on the issue.
- **Release notes notification:** Notification in the UI with the release notes of the latest version.

### Changed
- **Unified GPIO Logic:** Refactored motor control for both Modern (2-motor) and Classic (3-motor) models into a single system. Default pin assignments moved to safer GPIOs. Unused H-bridge inputs are now grounded;
- **Movement Refinements:** Improved PWM handling and non-blocking motion timing for smoother, more natural flapping.
- **UI Enhancements:** Added Billy artwork to header and included reboot/power/restart-ui buttons. Improved feedback for mic and speaker device tests.

### Fixed
- Minor mouth sync inconsistencies under load.
- Occasional stalls caused by blocking PWM threads.
- Better recovery after OpenAI API or network errors.
- Motor watchdog will now disengage any motor that is on > 30 seconds

## [1.6.0] — 2025-10-13
### Added
- Support for gpt-realtime-mini API model
- Turn Detection Eagerness setting.
- Mandatory `follow_up_intent` each turn (moved into tool instructions).
- Heuristic follow-up detector (handles “let me know”, “should I…”, etc.).
- Delayed/retry mic open after playback to avoid ALSA `-9985`.
- Debug logs for follow-up intent + final transcripts.
- 
### Changed
- Kickoff (MQTT say): mic opens after first reply **only if** follow-up expected; `say(..., interactive)` still works (`False` = Dory).
- Stream parsing also reads `response.done` content.
- Cleaner event routing + state handling.

### Fixed
- ALSA mic-open race (“Device unavailable”).
- Missed follow-ups when no `?`.
