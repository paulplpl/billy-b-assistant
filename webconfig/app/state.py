import configparser
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from packaging.version import InvalidVersion
from packaging.version import parse as parse_version


WEBCONFIG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROJECT_ROOT = Path(os.path.abspath(os.path.join(WEBCONFIG_DIR, "..")))
PERSONA_PATH = PROJECT_ROOT / "persona.ini"
VERSIONS_PATH = PROJECT_ROOT / "versions.ini"
WAKE_UP_DIR = PROJECT_ROOT / "sounds" / "wake-up" / "custom"
WAKE_UP_DIR_DEFAULT = PROJECT_ROOT / "sounds" / "wake-up" / "default"

RELEASE_NOTE = {"tag": None, "body": "", "url": "", "fetched_at": 0}


def load_versions():
    config = configparser.ConfigParser()
    if not os.path.exists(VERSIONS_PATH):
        example_path = os.path.join(PROJECT_ROOT, "versions.ini.example")
        if os.path.exists(example_path):
            shutil.copy(example_path, VERSIONS_PATH)
        else:
            config["version"] = {"current": "unknown", "latest": "unknown"}
            with open(VERSIONS_PATH, "w") as f:
                config.write(f)
    config.read(VERSIONS_PATH)
    return config


def save_versions(current: str, latest: str):
    if not current or not latest:
        print("[save_versions] Refusing to save empty version")
        return
    try:
        parsed_current = parse_version(current.lstrip("v"))
        parsed_latest = parse_version(latest.lstrip("v"))
    except InvalidVersion as e:
        print("[save_versions] Invalid version: ", e)
        return
    if parsed_latest < parsed_current:
        print(
            f"[save_versions] Skipping downgrade from {parsed_current} to {parsed_latest}"
        )
        latest = current
    config = configparser.ConfigParser()
    config["version"] = {"current": current, "latest": latest}
    with open(VERSIONS_PATH, "w") as f:
        config.write(f)


def get_current_version():
    try:
        return subprocess.check_output(
            ["git", "describe", "--tags", "--exact-match"],
            cwd=PROJECT_ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        try:
            commit = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=PROJECT_ROOT,
                text=True,
            ).strip()
            return f"(commit {commit})"
        except Exception as e:
            print("[get_current_version] Failed:", e)
            return "unknown"


def fetch_latest_tag():
    try:
        output = subprocess.check_output(
            [
                "curl",
                "-s",
                "https://api.github.com/repos/Thokoop/Billy-B-assistant/tags",
            ],
            text=True,
        )
        data = json.loads(output)
        if isinstance(data, dict) and data.get("message"):
            print(f"[fetch_latest_tag] GitHub error: {data['message']}")
            return None
        if not isinstance(data, list):
            print("[fetch_latest_tag] Unexpected response format")
            return None
        filtered = [tag["name"] for tag in data if "name" in tag]
        if filtered:
            return max(filtered, key=lambda v: parse_version(v.lstrip("v")))
        print("[fetch_latest_tag] No tags found")
        return None
    except Exception as e:
        print("[fetch_latest_tag] Exception:", e)
        return None


def fetch_release_note_for_tag(tag: str):
    try:
        output = subprocess.check_output(
            [
                "curl",
                "-s",
                f"https://api.github.com/repos/Thokoop/billy-b-assistant/releases/tags/{tag}",
            ],
            text=True,
        )
        data = json.loads(output)
        if isinstance(data, dict) and data.get("body"):
            return {
                "tag": data.get("tag_name") or tag,
                "body": data.get("body") or "",
                "url": data.get("html_url") or "",
            }
        return None
    except Exception as e:
        print("[fetch_release_note_for_tag] Exception:", e)
        return None


def bootstrap_versions_and_release_note():
    latest = fetch_latest_tag()
    current = get_current_version()
    save_versions(current, latest)
    try:
        versions_cfg = load_versions()
        tag_for_notes = versions_cfg["version"].get("latest") or versions_cfg[
            "version"
        ].get("current")
        if tag_for_notes:
            note = fetch_release_note_for_tag(tag_for_notes)
            if note:
                RELEASE_NOTE.update(note)
                RELEASE_NOTE["fetched_at"] = int(time.time())
                print(f"[release-note] Cached notes for {RELEASE_NOTE['tag']}")
            else:
                print("[release-note] No notes found for tag:", tag_for_notes)
        else:
            print("[release-note] No tag available to fetch notes.")
    except Exception as e:
        print("[release-note] Bootstrap failed:", e)
