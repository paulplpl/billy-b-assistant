import getpass
import os
import subprocess

from flask import Blueprint, jsonify, request


bp = Blueprint("misc", __name__)


@bp.route("/logs")
def logs():
    try:
        output = subprocess.check_output([
            "journalctl",
            "-u",
            "billy.service",
            "-n",
            "100",
            "--no-pager",
            "--output=short",
        ])
        return jsonify({"logs": output.decode("utf-8")})
    except subprocess.CalledProcessError as e:
        return jsonify({"logs": "Failed to retrieve logs", "error": str(e)}), 500


@bp.route("/service/<action>")
def control_service(action):
    if action not in ["start", "stop", "restart"]:
        return jsonify({"error": "Invalid action"}), 400
    try:
        if action in ["start", "restart"]:
            subprocess.check_call(["sudo", "systemctl", action, "billy.service"])
        else:
            subprocess.check_call(["sudo", "systemctl", action, "billy.service"])
        return jsonify({"status": "success", "action": action})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/restart', methods=['POST'])
def restart_billy_services():
    try:
        subprocess.Popen(["sudo", "systemctl", "restart", "billy-webconfig.service"])
        subprocess.Popen(["sudo", "systemctl", "restart", "billy.service"])
        return jsonify({"status": "ok", "message": "Restarting..."})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@bp.route("/service/status")
def service_status():
    try:
        # Get service status
        output = subprocess.check_output(
            ["systemctl", "is-active", "billy.service"], stderr=subprocess.STDOUT
        )
        service_status = output.decode("utf-8").strip()

        # Get comprehensive status including profiles and configuration
        try:
            import time

            from dotenv import load_dotenv

            from core.persona_manager import persona_manager
            from core.profile_manager import user_manager

            # Get project root and .env path
            project_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            )
            env_path = os.path.join(project_root, ".env")

            # Reload .env to get latest values
            load_dotenv(env_path)
            current_user_name = (
                os.getenv("CURRENT_USER", "").strip().strip("'\"")
            )  # Remove quotes and whitespace
            current_user = user_manager.get_current_user()

            # Get .env file status
            env_exists = os.path.exists(env_path)
            env_modified = os.path.getmtime(env_path) if env_exists else 0

            # Get memory count for current user
            memory_count = 0
            if current_user:
                try:
                    memories = current_user.get_memories(
                        100
                    )  # Get up to 100 memories to count
                    memory_count = len(memories)
                except Exception as e:
                    print(f"Failed to get memory count: {e}")

            # Get config hash to detect config changes
            config_hash = None
            try:
                import hashlib

                from ..core_imports import core_config

                # Create a hash of key config values to detect changes
                config_values = [
                    str(getattr(core_config, k, ""))
                    for k in [
                        "SILENCE_THRESHOLD",
                        "MIC_TIMEOUT_SECONDS",
                        "DEFAULT_USER",
                        "CURRENT_USER",
                        "MOUTH_ARTICULATION",
                    ]
                ]
                config_string = "|".join(config_values)
                config_hash = hashlib.md5(config_string.encode()).hexdigest()
            except Exception as e:
                print(f"Failed to get config hash: {e}")

            # Get current personality traits
            current_personality = None
            try:
                # Reload personality from disk to get latest changes from Billy
                from core.persona import load_traits_from_ini

                # Get current persona file path
                current_persona = persona_manager.current_persona
                if current_persona == "default":
                    persona_ini_path = os.path.join(project_root, "persona.ini")
                else:
                    persona_ini_path = os.path.join(
                        project_root, "personas", current_persona, "persona.ini"
                    )
                    if not os.path.exists(persona_ini_path):
                        # Fall back to old structure
                        persona_ini_path = os.path.join(
                            project_root, "personas", f"{current_persona}.ini"
                        )

                # Load fresh traits from the file
                traits = load_traits_from_ini(persona_ini_path)

                current_personality = {
                    "humor": traits.get("humor", 50),
                    "sarcasm": traits.get("sarcasm", 50),
                    "honesty": traits.get("honesty", 50),
                    "respectfulness": traits.get("respectfulness", 50),
                    "optimism": traits.get("optimism", 50),
                    "confidence": traits.get("confidence", 50),
                    "warmth": traits.get("warmth", 50),
                    "curiosity": traits.get("curiosity", 50),
                    "verbosity": traits.get("verbosity", 50),
                    "formality": traits.get("formality", 50),
                }
            except Exception as e:
                print(f"Failed to get current personality: {e}")

            return jsonify({
                "status": service_status,
                "current_user": current_user_name,
                "current_user_loaded": current_user.name if current_user else None,
                "current_persona": persona_manager.current_persona,
                "current_personality": current_personality,
                "available_profiles": user_manager.list_all_users(),
                "available_personas": persona_manager.get_available_personas(),
                "memory_count": memory_count,
                "config_hash": config_hash,
                "env_file": {"exists": env_exists, "modified": env_modified},
                "timestamp": time.time(),
            })
        except Exception as e:
            # Fallback to basic service status if profile loading fails
            return jsonify({
                "status": service_status,
                "error": f"Failed to load profile status: {str(e)}",
            })

    except subprocess.CalledProcessError as e:
        return jsonify({"status": e.output.decode("utf-8").strip()})


@bp.route("/reboot", methods=["POST"])
def reboot_billy():
    try:
        subprocess.call(["sudo", "shutdown", "-r", "now"])
        return jsonify({"status": "ok", "message": "Billy rebooting"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@bp.route("/shutdown", methods=["POST"])
def shutdown_billy():
    try:
        subprocess.call(["sudo", "shutdown", "-h", "now"])
        return jsonify({"status": "ok", "message": "Billy shutting down"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@bp.route("/change-password", methods=["POST"])
def change_password():
    """Change the password for the current user (typically 'billy' on Raspberry Pi)."""
    try:
        data = request.get_json()
        new_password = data.get("new_password")
        confirm_password = data.get("confirm_password")

        if not all([new_password, confirm_password]):
            return jsonify({"status": "error", "error": "All fields are required"}), 400

        if new_password != confirm_password:
            return jsonify({
                "status": "error",
                "error": "New passwords do not match",
            }), 400

        if len(new_password) < 8:
            return jsonify({
                "status": "error",
                "error": "New password must be at least 8 characters long",
            }), 400

        # Get current username
        current_user = getpass.getuser()

        # Change the password using chpasswd command (more reliable than passwd)
        try:
            # Use chpasswd which accepts username:password pairs via stdin
            process = subprocess.Popen(
                ["sudo", "chpasswd"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Send username:newpassword to chpasswd
            stdout, stderr = process.communicate(
                input=f"{current_user}:{new_password}\n"
            )

            if process.returncode == 0:
                # Set FORCE_PASS_CHANGE=false in .env file
                try:
                    # Get the project root directory (two levels up from webconfig/app/routes/)
                    project_root = os.path.dirname(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                    )
                    env_file_path = os.path.join(project_root, ".env")
                    env_content = ""
                    force_pass_change_set = False

                    # Read existing .env file
                    if os.path.exists(env_file_path):
                        with open(env_file_path) as f:
                            lines = f.readlines()

                        # Update or add FORCE_PASS_CHANGE
                        for line in lines:
                            if line.startswith("FORCE_PASS_CHANGE="):
                                env_content += "FORCE_PASS_CHANGE=False\n"
                                force_pass_change_set = True
                            else:
                                env_content += line

                    # Add FORCE_PASS_CHANGE if it wasn't found
                    if not force_pass_change_set:
                        env_content += "FORCE_PASS_CHANGE=False\n"

                    # Write back to .env file
                    with open(env_file_path, 'w') as f:
                        f.write(env_content)

                    # Reload the .env file to pick up the new setting
                    from dotenv import load_dotenv

                    load_dotenv(dotenv_path=env_file_path, override=True)

                    # Also reload the core config module to pick up the new setting
                    import importlib
                    import sys

                    if 'core.config' in sys.modules:
                        importlib.reload(sys.modules['core.config'])

                except Exception as e:
                    print(f"Warning: Could not update .env file: {e}")

                return jsonify({
                    "status": "ok",
                    "message": "Password changed successfully",
                })
            error_msg = stderr.strip() if stderr else "Password change failed"
            return jsonify({"status": "error", "error": error_msg}), 400

        except Exception as e:
            return jsonify({
                "status": "error",
                "error": f"Failed to change password: {str(e)}",
            }), 500

    except Exception as e:
        return jsonify({"status": "error", "error": f"Unexpected error: {str(e)}"}), 500


@bp.route("/test-motor", methods=["POST"])
def test_motor():
    """Test individual motors (mouth, head, or tail)."""
    try:
        import time

        # Stop Billy service if running (to release GPIO)
        was_active = False
        try:
            output = subprocess.check_output(
                ["systemctl", "is-active", "billy.service"], stderr=subprocess.STDOUT
            )
            was_active = output.decode().strip() == "active"
        except subprocess.CalledProcessError:
            was_active = False

        if was_active:
            subprocess.check_call(["sudo", "systemctl", "stop", "billy.service"])

        data = request.get_json()
        motor = data.get("motor")

        import core.movements as movements

        # Perform the requested test
        if motor == "mouth":
            movements.move_mouth(100, 1, brake=True)
        elif motor == "head":
            movements.move_head("on")
            time.sleep(1)
            movements.move_head("off")
        elif motor == "tail":
            movements.move_tail(duration=1)
        else:
            return jsonify({"error": "Invalid motor"}), 400

        return jsonify({"status": f"{motor} tested", "service_was_active": was_active})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
