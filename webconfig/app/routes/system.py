import os
import subprocess
import threading
import time

from dotenv import find_dotenv, set_key
from flask import Blueprint, jsonify, render_template, request
from packaging.version import parse as parse_version

from ..core_imports import core_config, voice_provider_registry
from ..state import PROJECT_ROOT, RELEASE_NOTE, load_versions, save_versions


bp = Blueprint("system", __name__)

# Find .env file in project root (not webconfig directory)
ENV_PATH = find_dotenv(usecwd=True)
if not ENV_PATH or not os.path.exists(ENV_PATH):
    # Fallback: look for .env in project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    ENV_PATH = os.path.join(project_root, ".env")
CONFIG_KEYS = [
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "BILLY_MODEL",
    "BILLY_PINS",
    "MIC_TIMEOUT_SECONDS",
    "SILENCE_THRESHOLD",
    "MQTT_HOST",
    "MQTT_PORT",
    "MQTT_USERNAME",
    "MQTT_PASSWORD",
    "HA_HOST",
    "HA_TOKEN",
    "HA_LANG",
    "MIC_PREFERENCE",
    "SPEAKER_PREFERENCE",
    "FLASK_PORT",
    "RUN_MODE",
    "SHOW_SUPPORT",
    "TURN_EAGERNESS",
    "FORCE_PASS_CHANGE",
    "MOUTH_ARTICULATION",
    "LOG_LEVEL",
    "DEFAULT_USER",
    "CURRENT_USER",
    "SHOW_RC_VERSIONS",
]


def delayed_restart():
    time.sleep(1.5)
    subprocess.run(["sudo", "systemctl", "restart", "billy-webconfig.service"])
    subprocess.run(["sudo", "systemctl", "restart", "billy.service"])


@bp.route("/")
def index():
    return render_template(
        "index.html",
        config={k: str(getattr(core_config, k, "")) for k in CONFIG_KEYS}
        | {
            "VOICE_OPTIONS": [
                "alloy",
                "ash",
                "ballad",
                "coral",
                "echo",
                "sage",
                "shimmer",
                "verse",
                "marin",
                "cedar",
            ],
        },
    )


@bp.route("/version")
def version_info():
    versions = load_versions()
    current = versions["version"].get("current", "unknown")
    latest = versions["version"].get("latest", "unknown")
    try:
        update_available = (
            current != "unknown"
            and latest != "unknown"
            and parse_version(latest.lstrip("v")) > parse_version(current.lstrip("v"))
        )
    except Exception:
        update_available = False
    return jsonify({
        "current": current,
        "latest": latest,
        "update_available": update_available,
    })


@bp.route("/update", methods=["POST"])
def perform_update():
    versions = load_versions()
    current = versions["version"].get("current", "unknown")
    latest = versions["version"].get("latest", "unknown")
    if current == latest or latest == "unknown":
        return jsonify({"status": "up-to-date", "version": current})
    try:
        subprocess.check_output(["git", "remote", "-v"], cwd=PROJECT_ROOT, text=True)
        subprocess.check_call(["git", "fetch", "--tags"], cwd=PROJECT_ROOT)
        subprocess.check_call(
            ["git", "checkout", "--force", f"tags/{latest}"], cwd=PROJECT_ROOT
        )
        venv_pip = os.path.join(PROJECT_ROOT, "venv", "bin", "pip")
        output = subprocess.check_output(
            [venv_pip, "install", "--upgrade", "-r", "requirements.txt"],
            cwd=PROJECT_ROOT,
            stderr=subprocess.STDOUT,
            text=True,
        )
        print("📦 Pip install output:\n", output)
        save_versions(latest, latest)
        threading.Thread(
            target=lambda: (
                time.sleep(2),
                subprocess.run([
                    "sudo",
                    "systemctl",
                    "restart",
                    "billy-webconfig.service",
                ]),
            )
        ).start()
        threading.Thread(
            target=lambda: (
                time.sleep(2),
                subprocess.run(["sudo", "systemctl", "restart", "billy.service"]),
            )
        ).start()
        return jsonify({"status": "updated", "version": latest})
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@bp.route("/release-note")
def release_note():
    return jsonify(RELEASE_NOTE)


@bp.route("/save", methods=["POST"])
def save():
    data = request.json
    old_port = os.getenv("FLASK_PORT", "80")
    changed_port = False
    for key, value in data.items():
        if key in CONFIG_KEYS:
            set_key(ENV_PATH, key, value, quote_mode='never')
            if key == "FLASK_PORT" and str(value) != str(old_port):
                changed_port = True
    response = {"status": "ok"}
    if changed_port:
        response["port_changed"] = True
        threading.Thread(target=delayed_restart).start()
    return jsonify(response)


@bp.route("/config")
def get_config():
    # Reload .env file and core config to get latest values
    from dotenv import load_dotenv

    load_dotenv(ENV_PATH, override=True)

    # Reload core config module to pick up new .env values
    import importlib
    import sys

    if 'core.config' in sys.modules:
        importlib.reload(sys.modules['core.config'])

    # Re-import core_config to get fresh values
    from ..core_imports import core_config

    # Get basic configuration
    config_data = {k: str(getattr(core_config, k, "")) for k in CONFIG_KEYS}

    # Add voice options from the current provider
    current_provider = voice_provider_registry.get_provider()
    voices = current_provider.get_supported_voices()
    config_data["VOICE_OPTIONS"] = voices

    # Add user profile information
    try:
        from core.config import DEFAULT_USER
        from core.profile_manager import user_manager

        # Get current user from .env file (already reloaded above)
        current_user_name = (
            os.getenv("CURRENT_USER", "").strip().strip("'\"").lower()
        )  # Remove quotes, whitespace, and normalize to lowercase
        current_user = None

        # Update config_data with fresh CURRENT_USER value
        config_data["CURRENT_USER"] = current_user_name

        # If we have a current user in .env, try to load it
        if current_user_name and current_user_name.lower() != "guest":
            try:
                current_user = user_manager.identify_user(current_user_name, "high")
            except Exception as e:
                print(f"Failed to load current user {current_user_name}: {e}")

        # Only fall back to DEFAULT_USER if CURRENT_USER is completely empty (not set)
        # If CURRENT_USER is explicitly set to "guest", respect that choice
        if (
            not current_user
            and not current_user_name
            and DEFAULT_USER
            and DEFAULT_USER.lower() != "guest"
        ):
            try:
                current_user = user_manager.identify_user(DEFAULT_USER, "high")
                # Only update CURRENT_USER in .env if it was completely empty
                config_data["CURRENT_USER"] = DEFAULT_USER
            except Exception as e:
                print(f"Failed to load default user {DEFAULT_USER}: {e}")

        # Add user profile data
        if current_user:
            config_data["CURRENT_USER"] = {
                "name": current_user.name,
                "data": current_user.data,
                "memories": current_user.get_memories(10),
                "context": current_user.get_context_string(),
            }
        else:
            # If no user is loaded, preserve the CURRENT_USER value from .env
            # This could be "guest" or a user name that couldn't be loaded
            config_data["CURRENT_USER"] = (
                current_user_name if current_user_name else None
            )

        # Add available profiles with full data including preferred personas
        try:
            from core.profile_manager import UserProfile

            available_profiles = []
            for user_name in user_manager.list_all_users():
                try:
                    profile = UserProfile(user_name)
                    available_profiles.append({
                        "name": profile.name,
                        "data": profile.data,
                    })
                except Exception as e:
                    print(f"Failed to load profile {user_name}: {e}")
                    # Add basic info even if full profile can't be loaded
                    available_profiles.append({
                        "name": user_name,
                        "data": {"USER_INFO": {"preferred_persona": "default"}},
                    })
            config_data["AVAILABLE_PROFILES"] = available_profiles
        except Exception as e:
            print(f"Failed to load profile data: {e}")
            config_data["AVAILABLE_PROFILES"] = []

        # Add available personas and current persona
        try:
            from core.persona_manager import persona_manager

            config_data["AVAILABLE_PERSONAS"] = persona_manager.get_available_personas()
            config_data["CURRENT_PERSONA"] = persona_manager.current_persona
        except Exception as e:
            print(f"Failed to load personas: {e}")
            config_data["AVAILABLE_PERSONAS"] = []
            config_data["CURRENT_PERSONA"] = "default"

    except Exception as e:
        print(f"Failed to load user profile data: {e}")
        config_data["CURRENT_USER"] = None
        config_data["AVAILABLE_PROFILES"] = []
        config_data["AVAILABLE_PERSONAS"] = []

    return jsonify(config_data)


@bp.route("/profiles/current-user", methods=["PATCH"])
def update_current_user_profile():
    """Update the current user's profile settings."""
    try:
        from core.persona_manager import persona_manager
        from core.profile_manager import user_manager

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        current_user = user_manager.get_current_user()
        if not current_user:
            return jsonify({"error": "No current user"}), 400

        # Handle persona switching
        if data.get("action") == "switch_persona":
            new_persona = data.get("preferred_persona")
            if new_persona:
                # Update user's preferred persona
                current_user.data['USER_INFO']['preferred_persona'] = new_persona
                current_user._save_profile()

                # Switch persona manager to new persona
                persona_manager.switch_persona(new_persona)

                return jsonify({
                    "success": True,
                    "message": f"Switched to {new_persona} persona",
                })

        return jsonify({"error": "Invalid action"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/config/refresh", methods=["POST"])
def refresh_config():
    """Refresh core configuration modules to pick up new settings."""
    try:
        # Reload .env file first
        from dotenv import load_dotenv

        load_dotenv(ENV_PATH, override=True)

        # Import and reload core modules that might have cached configuration
        import importlib
        import sys

        # Reload core modules that contain configuration
        modules_to_reload = [
            'core.config',
            'core.personality',
            'core.wakeup',
            'core.say',
            'core.audio',
        ]

        for module_name in modules_to_reload:
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])

        # Also reload the core_imports to get fresh references
        if 'app.core_imports' in sys.modules:
            importlib.reload(sys.modules['app.core_imports'])

        return jsonify({"status": "ok", "message": "Configuration refreshed"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/config/auto-refresh", methods=["POST"])
def auto_refresh_config():
    """Automatically refresh configuration when .env changes are detected."""
    try:
        # Reload .env file
        from dotenv import load_dotenv

        load_dotenv(ENV_PATH, override=True)

        # Reload core config module
        import importlib
        import sys

        if 'core.config' in sys.modules:
            importlib.reload(sys.modules['core.config'])

        # Get updated configuration
        from ..core_imports import core_config

        # Return updated config data
        config_data = {k: str(getattr(core_config, k, "")) for k in CONFIG_KEYS}

        # Add user profile information
        try:
            from core.config import DEFAULT_USER
            from core.profile_manager import user_manager

            # Get current user from .env file (fresh read)
            current_user_name = os.getenv("CURRENT_USER", "").strip().strip("'\"")
            current_user = None

            # Update config_data with fresh CURRENT_USER value
            config_data["CURRENT_USER"] = current_user_name

            # If we have a current user in .env, try to load it
            if current_user_name and current_user_name.lower() != "guest":
                try:
                    current_user = user_manager.identify_user(current_user_name, "high")
                except Exception as e:
                    print(f"Failed to load current user {current_user_name}: {e}")

            # Only fall back to DEFAULT_USER if CURRENT_USER is completely empty
            if (
                not current_user
                and not current_user_name
                and DEFAULT_USER
                and DEFAULT_USER.lower() != "guest"
            ):
                try:
                    current_user = user_manager.identify_user(DEFAULT_USER, "high")
                    config_data["CURRENT_USER"] = DEFAULT_USER
                except Exception as e:
                    print(f"Failed to load default user {DEFAULT_USER}: {e}")

            # Add user profile data
            if current_user:
                config_data["CURRENT_USER"] = {
                    "name": current_user.name,
                    "data": current_user.data,
                    "memories": current_user.get_memories(10),
                    "context": current_user.get_context_string(),
                }
            else:
                config_data["CURRENT_USER"] = (
                    current_user_name if current_user_name else None
                )

            # Add available profiles with full data including preferred personas
            try:
                from core.profile_manager import UserProfile

                available_profiles = []
                for user_name in user_manager.list_all_users():
                    try:
                        profile = UserProfile(user_name)
                        available_profiles.append({
                            "name": profile.name,
                            "data": profile.data,
                        })
                    except Exception as e:
                        print(f"Failed to load profile {user_name}: {e}")
                        # Add basic info even if full profile can't be loaded
                        available_profiles.append({
                            "name": user_name,
                            "data": {"USER_INFO": {"preferred_persona": "default"}},
                        })
                config_data["AVAILABLE_PROFILES"] = available_profiles
            except Exception as e:
                print(f"Failed to load profile data: {e}")
                config_data["AVAILABLE_PROFILES"] = []

            # Add available personas
            try:
                from core.persona_manager import persona_manager

                config_data["AVAILABLE_PERSONAS"] = (
                    persona_manager.get_available_personas()
                )
            except Exception as e:
                print(f"Failed to load personas: {e}")
                config_data["AVAILABLE_PERSONAS"] = []

        except Exception as e:
            print(f"Failed to load user profile data: {e}")
            config_data["CURRENT_USER"] = None
            config_data["AVAILABLE_PROFILES"] = []
            config_data["AVAILABLE_PERSONAS"] = []

        return jsonify({
            "status": "ok",
            "message": "Configuration auto-refreshed",
            "config": config_data,
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@bp.route('/get-env')
def get_env():
    try:
        with open('.env') as f:
            return f.read(), 200
    except Exception as e:
        return str(e), 500


@bp.route('/save-env', methods=['POST'])
def save_env():
    content = request.json.get('content', '')
    try:
        with open('.env', 'w') as f:
            f.write(content)
        return jsonify({"status": "ok", "message": ".env saved"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/hostname", methods=["GET", "POST"])
def hostname():
    if request.method == "GET":
        return jsonify({"hostname": os.uname().nodename})
    if request.method == "POST":
        data = request.get_json()
        new_hostname = data.get("hostname", "").strip()
        if not new_hostname:
            return jsonify({"error": "Invalid hostname"}), 400
        try:
            subprocess.check_call(["sudo", "hostnamectl", "set-hostname", new_hostname])
            subprocess.run(["sudo", "systemctl", "restart", "avahi-daemon"])
            return jsonify({"status": "ok", "hostname": new_hostname})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "Unsupported method"}), 405
