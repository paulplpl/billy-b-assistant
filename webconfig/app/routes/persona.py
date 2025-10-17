import configparser

from flask import Blueprint, jsonify, request, send_file

from ..state import PERSONA_PATH


bp = Blueprint("persona", __name__)


@bp.route("/persona", methods=["GET"])
def get_persona():
    config = configparser.ConfigParser()
    config.read(PERSONA_PATH)
    return jsonify({
        "PERSONALITY": dict(config["PERSONALITY"]) if "PERSONALITY" in config else {},
        "BACKSTORY": dict(config["BACKSTORY"]) if "BACKSTORY" in config else {},
        "META": config["META"].get("instructions", "") if "META" in config else "",
        "WAKEUP": dict(config["WAKEUP"]) if "WAKEUP" in config else {},
    })


@bp.route("/persona", methods=["POST"])
def save_persona():
    data = request.json
    config = configparser.ConfigParser()
    config["PERSONALITY"] = {k: str(v) for k, v in data.get("PERSONALITY", {}).items()}
    config["BACKSTORY"] = data.get("BACKSTORY", {})
    config["META"] = {"instructions": data.get("META", "")}
    wakeup = data.get("WAKEUP", {})
    config["WAKEUP"] = {
        str(k): v["text"] if isinstance(v, dict) and "text" in v else str(v)
        for k, v in wakeup.items()
    }
    with open(PERSONA_PATH, "w") as f:
        config.write(f)
    return jsonify({"status": "ok"})


@bp.route("/persona/wakeup", methods=["POST"])
def save_single_wakeup_phrase():
    data = request.get_json()
    index = str(data.get("index"))
    phrase = data.get("phrase", "").strip()
    if not index or not phrase:
        return jsonify({"error": "Missing index or phrase"}), 400
    config = configparser.ConfigParser()
    config.read(PERSONA_PATH)
    if "WAKEUP" not in config:
        config["WAKEUP"] = {}
    config["WAKEUP"][index] = phrase
    with open(PERSONA_PATH, "w") as f:
        config.write(f)
    return jsonify({"status": "ok"})


@bp.route('/persona/import', methods=['POST'])
def import_persona():
    if request.is_json:
        ini = request.json.get('ini', '')
    elif 'file' in request.files:
        ini = request.files['file'].read().decode('utf-8')
    else:
        return jsonify({'error': 'No file provided'}), 400
    if not ini or '[PERSONALITY]' not in ini:
        return jsonify({'error': 'Invalid INI file'}), 400
    try:
        with open(PERSONA_PATH, 'w') as f:
            f.write(ini)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/persona/export')
def export_persona():
    return send_file(
        PERSONA_PATH,
        as_attachment=True,
        download_name="persona.ini",
        mimetype="text/plain",
    )
