"""
User Profile Management System for Billy Bass Assistant.
Handles user identification, memory storage, and profile management.
"""

import configparser
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .logger import logger


class UserProfile:
    """Represents a user profile with memories and preferences."""

    def __init__(self, name: str):
        self.name = name
        self.profile_path = Path("profiles") / f"{name.lower()}.ini"
        self.data = self._load_or_create_profile()

    def _load_or_create_profile(self) -> dict[str, Any]:
        """Load existing profile or create new one."""
        if self.profile_path.exists():
            return self._load_profile()
        return self._create_new_profile()

    def _load_profile(self) -> dict[str, Any]:
        """Load profile from INI file."""
        config = configparser.ConfigParser()
        config.read(self.profile_path)

        # Convert INI to dict
        data = {}
        for section in config.sections():
            data[section] = dict(config[section])

        # Parse core memories from JSON
        if 'CORE_MEMORIES' in data:
            try:
                data['core_memories'] = json.loads(
                    data['CORE_MEMORIES'].get('memories', '[]')
                )
            except json.JSONDecodeError:
                data['core_memories'] = []
        else:
            data['core_memories'] = []

        # Parse display_name (migrate from aliases if needed)
        if 'USER_INFO' in data:
            # If aliases exist, use the first one as display_name, then remove aliases
            if 'aliases' in data['USER_INFO']:
                try:
                    aliases = json.loads(data['USER_INFO'].get('aliases', '[]'))
                    if aliases and len(aliases) > 0:
                        data['USER_INFO']['display_name'] = aliases[0]
                    else:
                        data['USER_INFO']['display_name'] = self.name
                    # Remove the old aliases field
                    del data['USER_INFO']['aliases']
                except json.JSONDecodeError:
                    data['USER_INFO']['display_name'] = self.name
            elif 'display_name' not in data['USER_INFO']:
                data['USER_INFO']['display_name'] = self.name
        else:
            # Ensure USER_INFO section exists with display_name
            if 'USER_INFO' not in data:
                data['USER_INFO'] = {}
            data['USER_INFO']['display_name'] = self.name

        return data

    def _create_new_profile(self) -> dict[str, Any]:
        """Create a new user profile."""
        data = {
            'USER_INFO': {
                'name': self.name,
                'display_name': self.name,
                'preferred_persona': 'default',
                'created_date': datetime.now().isoformat(),
                'last_seen': datetime.now().isoformat(),
                'interaction_count': '0',
                'bond_level': 'new',
            },
            'core_memories': [],
        }

        self._save_profile(data)
        logger.info(f"Created new profile for {self.name}", "👤")
        return data

    def _save_profile(self, data: Optional[dict[str, Any]] = None):
        """Save profile to INI file."""
        if data is None:
            data = self.data

        config = configparser.ConfigParser()

        # Convert dict to INI sections
        for section_name, section_data in data.items():
            if section_name == 'core_memories':
                continue  # Handle separately

            if not config.has_section(section_name):
                config.add_section(section_name)
            for key, value in section_data.items():
                # Handle JSON fields properly
                if key == 'aliases' and isinstance(value, list):
                    config.set(section_name, key, json.dumps(value))
                else:
                    config.set(section_name, key, str(value))

        # Save core memories as JSON
        if not config.has_section('CORE_MEMORIES'):
            config.add_section('CORE_MEMORIES')
        config.set(
            'CORE_MEMORIES', 'memories', json.dumps(data.get('core_memories', []))
        )

        # Ensure directory exists
        self.profile_path.parent.mkdir(exist_ok=True)

        with open(self.profile_path, 'w') as f:
            config.write(f)

    def add_memory(
        self, memory: str, importance: str = "medium", category: str = "fact"
    ):
        """Add a memory to the user's profile."""
        memory_entry = {
            "date": datetime.now().isoformat(),
            "memory": memory,
            "importance": importance,
            "category": category,
        }

        self.data['core_memories'].append(memory_entry)

        # Keep only most important memories (limit to 20)
        importance_order = {"high": 3, "medium": 2, "low": 1}
        self.data['core_memories'] = sorted(
            self.data['core_memories'],
            key=lambda x: importance_order.get(x.get("importance", "low"), 1),
        )[-20:]

        self._save_profile()
        logger.info(f"Added memory for {self.name}: {memory[:50]}...", "💭")

    def update_last_seen(self):
        """Update the last seen timestamp."""
        self.data['USER_INFO']['last_seen'] = datetime.now().isoformat()
        self._save_profile()

    def increment_interaction_count(self):
        """Increment the interaction count (called at end of session)."""
        interaction_count = int(self.data['USER_INFO'].get('interaction_count', '0'))
        self.data['USER_INFO']['interaction_count'] = str(interaction_count + 1)
        self._save_profile()
        logger.info(
            f"Incremented interaction count for {self.name}: {interaction_count + 1}",
            "👤",
        )

    def set_preferred_persona(self, persona: str):
        """Set the user's preferred Billy persona."""
        self.data['USER_INFO']['preferred_persona'] = persona
        self._save_profile()
        logger.info(f"Set {self.name}'s preferred persona to {persona}", "🎭")

    def get_memories(self, limit: int = 5) -> list[dict[str, Any]]:
        """Get recent memories for the user."""
        return self.data['core_memories'][-limit:]

    def get_context_string(self) -> str:
        """Get formatted context string for AI prompt."""
        context = f"\n[USER: {self.name} | PERSONA: {self.data['USER_INFO'].get('preferred_persona', 'default')} | BOND: {self.data['USER_INFO'].get('bond_level', 'new')}]\n"

        memories = self.get_memories(3)  # Reduced from 5 to 3
        if memories:
            context += f"Memories: {'; '.join([m['memory'] for m in memories])}\n"

        return context


class UserProfileManager:
    """Manages user profiles and current user state."""

    def __init__(self):
        self.current_user: Optional[UserProfile] = None
        self.profiles_dir = Path("profiles")
        self.profiles_dir.mkdir(exist_ok=True)

    def find_user_by_name_or_display_name(self, name: str) -> Optional[str]:
        """Find a user profile by name or display name. Returns the actual profile name if found."""
        name = name.strip().title()

        # First check if there's an exact match
        profile_path = Path("profiles") / f"{name.lower()}.ini"
        if profile_path.exists():
            return name

        # Check all profiles for display_name
        profiles_dir = Path("profiles")
        if not profiles_dir.exists():
            return None

        for profile_file in profiles_dir.glob("*.ini"):
            try:
                config = configparser.ConfigParser()
                config.read(profile_file)

                if config.has_section("USER_INFO"):
                    # Check if the name matches the display_name
                    display_name = config.get("USER_INFO", "display_name", fallback="")
                    if name.lower() == display_name.lower():
                        # Return the actual profile name (from filename)
                        return profile_file.stem.title()

            except Exception:
                continue

        return None

    def identify_user(
        self, name: str, confidence: str = "medium"
    ) -> Optional[UserProfile]:
        """Identify and load a user profile."""
        name = name.strip().title()

        if confidence == "low":
            logger.warning(f"Low confidence in name spelling: {name}")
            return None

        # First try to find existing user by name or display name
        actual_name = self.find_user_by_name_or_display_name(name)
        if actual_name:
            # Load existing profile
            profile = UserProfile(actual_name)
            self.current_user = profile
            profile.update_last_seen()
            logger.info(
                f"Identified existing user: {actual_name} (matched '{name}')", "👤"
            )
            return profile
        # Create new profile
        profile = UserProfile(name)
        self.current_user = profile
        profile.update_last_seen()
        logger.info(f"Created new user profile: {name}", "👤")
        return profile

    def get_current_user(self) -> Optional[UserProfile]:
        """Get the current user profile."""
        return self.current_user

    def clear_current_user(self):
        """Clear the current user (for guest mode)."""
        self.current_user = None
        logger.info("Cleared current user", "👤")

    def list_all_users(self) -> list[str]:
        """List all known users."""
        users = []
        for profile_file in self.profiles_dir.glob("*.ini"):
            name = profile_file.stem.title()
            users.append(name)
        return sorted(users)

    def get_user_context(self) -> str:
        """Get context string for current user."""
        if self.current_user:
            return self.current_user.get_context_string()
        return ""

    def increment_current_user_interaction_count(self):
        """Increment interaction count for current user (called at end of session)."""
        if self.current_user:
            self.current_user.increment_interaction_count()

    def load_default_user(self):
        """Load the default user on startup and always set current_user to default_user."""
        try:
            from .config import DEFAULT_USER

            # Always set current_user to default_user on startup to prevent stale user state
            if DEFAULT_USER and DEFAULT_USER.lower() != "guest":
                # Try to load the default user
                profile = self.identify_user(DEFAULT_USER, "high")
                if profile:
                    logger.info(f"Loaded default user: {DEFAULT_USER}", "👤")
                else:
                    logger.warning(
                        f"Default user '{DEFAULT_USER}' not found, staying in guest mode",
                        "⚠️",
                    )
                    self.clear_current_user()
            else:
                logger.info("Starting in guest mode", "👤")
                self.clear_current_user()
        except Exception as e:
            logger.warning(f"Failed to load default user: {e}", "⚠️")
            self.clear_current_user()


# Global instance
user_manager = UserProfileManager()
