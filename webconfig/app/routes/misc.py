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
        output = subprocess.check_output(
            ["systemctl", "is-active", "billy.service"], stderr=subprocess.STDOUT
        )
        return jsonify({"status": output.decode("utf-8").strip()})
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
