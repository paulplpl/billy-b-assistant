import subprocess

from flask import Blueprint, jsonify


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
