"""
Profile management routes for Billy Bass Assistant.
Handles user profile CRUD operations and persona management.
"""

import json
import os
from pathlib import Path

from flask import Blueprint, jsonify, request


profiles_bp = Blueprint('profiles', __name__)


@profiles_bp.route('/profiles', methods=['GET'])
def list_profiles():
    """List all available user profiles."""
    try:
        profiles_dir = Path("profiles")
        if not profiles_dir.exists():
            return jsonify({"profiles": []})

        profiles = []
        for profile_file in profiles_dir.glob("*.ini"):
            profile_name = profile_file.stem.title()  # Convert to title case

            # Read display name from profile
            display_name = profile_name  # Default to profile name
            try:
                import configparser

                config = configparser.ConfigParser()
                config.read(profile_file)
                if config.has_section("USER_INFO") and config.has_option(
                    "USER_INFO", "display_name"
                ):
                    display_name = config.get("USER_INFO", "display_name")
            except Exception:
                pass  # Use default display name if reading fails

            profiles.append({
                "name": profile_name,
                "display_name": display_name,
                "file": str(profile_file),
                "size": profile_file.stat().st_size,
                "modified": profile_file.stat().st_mtime,
            })

        return jsonify({"profiles": profiles})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@profiles_bp.route('/profiles/<profile_name>', methods=['GET'])
def get_profile(profile_name):
    """Get details of a specific profile."""
    try:
        # Convert to lowercase to match file naming convention
        profile_file = Path("profiles") / f"{profile_name.lower()}.ini"
        if not profile_file.exists():
            return jsonify({"error": "Profile not found"}), 404

        # Read profile data
        import configparser

        config = configparser.ConfigParser()
        config.read(profile_file)

        profile_data = {}
        for section in config.sections():
            profile_data[section] = dict(config.items(section))

        return jsonify({"name": profile_name, "data": profile_data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@profiles_bp.route('/profiles/<profile_name>', methods=['DELETE'])
def delete_profile(profile_name):
    """Delete a user profile."""
    try:
        # Convert to lowercase to match file naming convention
        profile_file = Path("profiles") / f"{profile_name.lower()}.ini"
        if not profile_file.exists():
            return jsonify({"error": "Profile not found"}), 404

        profile_file.unlink()
        return jsonify({"message": f"Profile {profile_name} deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@profiles_bp.route('/personas', methods=['GET'])
def list_personas():
    """List all available personas."""
    try:
        personas_dir = Path("personas")
        if not personas_dir.exists():
            return jsonify({"personas": []})

        personas = []
        for persona_file in personas_dir.glob("*.ini"):
            persona_name = persona_file.stem

            # Read persona metadata
            import configparser

            config = configparser.ConfigParser()
            config.read(persona_file)

            meta = dict(config.items("META")) if config.has_section("META") else {}
            personality = (
                dict(config.items("PERSONALITY"))
                if config.has_section("PERSONALITY")
                else {}
            )

            personas.append({
                "name": persona_name,
                "description": meta.get("description", persona_name),
                "mood": meta.get("mood", "neutral"),
                "energy": meta.get("energy", "medium"),
                "personality_traits": personality,
            })

        return jsonify({"personas": personas})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@profiles_bp.route('/current-user', methods=['GET'])
def get_current_user():
    """Get the currently active user profile."""
    try:
        # Import here to avoid circular imports
        from core.config import DEFAULT_USER
        from core.profile_manager import user_manager

        current_user = user_manager.get_current_user()

        # If no current user but we have a default user, try to load it
        if not current_user and DEFAULT_USER and DEFAULT_USER.lower() != "guest":
            try:
                current_user = user_manager.identify_user(DEFAULT_USER, "high")
            except Exception as e:
                print(f"Failed to load default user {DEFAULT_USER}: {e}")

        if not current_user:
            return jsonify({"user": None})

        return jsonify({
            "user": {
                "name": current_user.name,
                "data": current_user.data,
                "memories": current_user.get_memories(10),  # Last 10 memories
                "context": current_user.get_context_string(),
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@profiles_bp.route('/current-user', methods=['POST'])
def set_current_user():
    """Set the current user profile."""
    try:
        data = request.get_json()
        user_name = data.get("name", "").strip()

        if not user_name:
            return jsonify({"error": "User name is required"}), 400

        # Import here to avoid circular imports
        from core.profile_manager import user_manager

        # Identify the user (this will load or create the profile)
        profile = user_manager.identify_user(user_name, "high")

        if profile:
            return jsonify({
                "message": f"Switched to user: {user_name}",
                "user": {"name": profile.name, "data": profile.data},
            })
        return jsonify({"error": "Failed to load user profile"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@profiles_bp.route('/current-user', methods=['DELETE'])
def clear_current_user():
    """Clear the current user profile (switch to guest mode)."""
    try:
        # Import here to avoid circular imports
        from core.profile_manager import user_manager

        user_manager.clear_current_user()
        return jsonify({"message": "Current user cleared, switched to guest mode"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@profiles_bp.route('/current-user', methods=['PATCH'])
def update_current_user():
    """Update current user settings (like preferred persona)."""
    try:
        data = request.get_json()
        action = data.get("action")

        # Import here to avoid circular imports
        from core.profile_manager import user_manager

        current_user = user_manager.get_current_user()
        if not current_user:
            return jsonify({"error": "No current user"}), 400

        if action == "switch_persona":
            preferred_persona = data.get("preferred_persona")
            if preferred_persona:
                current_user.set_preferred_persona(preferred_persona)
                return jsonify({
                    "message": f"Updated {current_user.name}'s preferred persona to {preferred_persona}"
                })
            return jsonify({"error": "preferred_persona is required"}), 400
        return jsonify({"error": "Unknown action"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@profiles_bp.route('/profiles/rename', methods=['POST'])
def rename_profile():
    """Rename a user profile."""
    try:
        data = request.get_json()
        old_name = data.get("oldName", "").strip()
        new_name = data.get("newName", "").strip()

        if not old_name or not new_name:
            return jsonify({"error": "Both oldName and newName are required"}), 400

        if old_name.lower() == new_name.lower():
            return jsonify({"error": "New name must be different from old name"}), 400

        # Convert to lowercase for file operations
        old_file = Path("profiles") / f"{old_name.lower()}.ini"
        new_file = Path("profiles") / f"{new_name.lower()}.ini"

        if not old_file.exists():
            return jsonify({"error": "Profile not found"}), 404

        if new_file.exists():
            return jsonify({"error": "A profile with this name already exists"}), 400

        # Rename the file
        old_file.rename(new_file)

        # Update the profile name inside the file
        import configparser

        config = configparser.ConfigParser()
        config.read(new_file)

        if config.has_section("USER_INFO"):
            config.set("USER_INFO", "name", new_name)

            with open(new_file, 'w') as f:
                config.write(f)

        return jsonify({"message": f"Profile renamed from {old_name} to {new_name}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@profiles_bp.route('/profiles/delete-memory', methods=['POST'])
def delete_memory():
    """Delete a specific memory from a user profile."""
    try:
        data = request.get_json()
        user_name = data.get("user", "").strip()
        memory_date = data.get("memoryDate", "").strip()

        if not user_name or not memory_date:
            return jsonify({"error": "Both user and memoryDate are required"}), 400

        # Convert to lowercase for file operations
        profile_file = Path("profiles") / f"{user_name.lower()}.ini"

        if not profile_file.exists():
            return jsonify({"error": "Profile not found"}), 404

        # Read the profile
        import configparser

        config = configparser.ConfigParser()
        config.read(profile_file)

        if not config.has_section("CORE_MEMORIES"):
            return jsonify({"error": "No memories found"}), 404

        # Parse existing memories
        memories_str = config.get("CORE_MEMORIES", "memories", fallback="[]")
        try:
            memories = json.loads(memories_str)
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid memories format"}), 500

        # Find and remove the memory with matching date
        original_count = len(memories)
        memories = [m for m in memories if m.get("date") != memory_date]

        if len(memories) == original_count:
            return jsonify({"error": "Memory not found"}), 404

        # Update the profile
        config.set("CORE_MEMORIES", "memories", json.dumps(memories))

        with open(profile_file, 'w') as f:
            config.write(f)

        return jsonify({"message": "Memory deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@profiles_bp.route('/config', methods=['GET'])
def get_config():
    """Get current configuration including DEFAULT_USER."""
    try:
        return jsonify({"DEFAULT_USER": os.getenv("DEFAULT_USER", "guest")})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@profiles_bp.route('/profiles/update-display-name', methods=['POST'])
def update_display_name():
    """Update display name for a user's profile."""
    try:
        data = request.json
        user = data.get('user')
        display_name = data.get('display_name', '')

        if not user:
            return jsonify({"error": "User is required"}), 400

        profile_file = Path("profiles") / f"{user.lower()}.ini"
        if not profile_file.exists():
            return jsonify({"error": "Profile not found"}), 404

        # Read current profile
        import configparser

        config = configparser.ConfigParser()
        config.read(profile_file)

        # Ensure USER_INFO section exists
        if not config.has_section('USER_INFO'):
            config.add_section('USER_INFO')

        # Update display name
        config.set('USER_INFO', 'display_name', display_name)

        # Write back to file
        with open(profile_file, 'w') as f:
            config.write(f)

        return jsonify({"message": f"Updated display name for {user}'s profile"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
