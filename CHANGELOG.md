# Changelog

All notable changes to this project will be documented in this file.

---

## [2.0.0] — 2025-10-26

### 🎉 Major New Features

- **User Profiles**: Billy now recognizes individual users with their own profiles, display names, interaction history, and preferred personas
- **Memory System**: Billy remembers facts, preferences, and relationships for each user. Memories can be viewed, edited, and organized by importance
- **Multiple Personas**: Create and switch between different Billy personalities, each with unique voices, traits, and mouth articulation settings
- **Smart Greetings**: Context-aware greetings based on time of day and interaction history

### Added

- **User Management**: Create/switch profiles, set display names, guest mode, import/export profiles, profile statistics
- **Persona System**: Create custom personalities, per-persona voices and mouth articulation, import/export personas, mid-conversation switching with graceful voice changes
- **Memory Management**: Store and recall user-specific memories, categorize by type, set importance levels, edit/delete through UI
- **UI Improvements**: 4-level configurable logging (ERROR/WARNING/INFO/VERBOSE), tooltips, loading states, optimized polling

### Changed
- **Custom Wake-up Sounds**: wake-up sounds are now saved on Persona level.
- **Logging System**: Replaced DEBUG_MODE with configurable LOG_LEVEL system
- **Mouth Articulation**: Now on persona level instead of global
- **Storage**: User profiles and personas stored as INI files

### Fixed

- **Self-Triggering**: Billy no longer hears his own wake-up sounds
- **Head Movement**: Prevented head from getting stuck during routines
- **Session Hanging**: Added timeouts to prevent stuck sessions
- **Audio**: Standardized RMS calculations for consistent silence detection
- 
---

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

## [1.3.1] — 2025-08-19

### Added

- **Shutdown and restart**: Added raspberry pi shutdown and restart buttons in the UI (contribution by @cprasmu )

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
