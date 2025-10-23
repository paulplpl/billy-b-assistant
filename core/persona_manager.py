"""
Persona management system for Billy Bass Assistant.
Handles loading and switching between different personality configurations.
"""

import configparser
from pathlib import Path
from typing import Any, Optional

from .logger import logger


class PersonaManager:
    """Manages different Billy personas and personality configurations."""

    def __init__(self):
        self.personas_dir = Path("personas")
        self.personas_dir.mkdir(exist_ok=True)
        self.current_persona = "default"  # Default persona
        self._persona_cache: dict[str, dict[str, Any]] = {}

    def get_available_personas(self) -> list[dict]:
        """Get list of available persona files with their metadata."""
        personas = []

        # Add default persona.ini if it exists
        default_persona_file = Path("persona.ini")
        if default_persona_file.exists():
            try:
                config = configparser.ConfigParser()
                config.read(default_persona_file)
                personas.append({
                    "name": "default",
                    "description": "Default",
                })
            except Exception as e:
                logger.warning(f"Failed to load default persona: {e}")

        # Add custom personas from personas directory (both old format and new folder format)
        if self.personas_dir.exists():
            # Check for old format: personas/*.ini
            for file_path in self.personas_dir.glob("*.ini"):
                persona_name = file_path.stem
                persona_data = self.load_persona(persona_name)
                if persona_data:
                    personas.append({
                        "name": persona_name,
                        "description": persona_data.get("meta", {}).get(
                            "description", persona_name
                        ),
                    })

            # Check for new format: personas/*/persona.ini
            for folder_path in self.personas_dir.iterdir():
                if folder_path.is_dir():
                    persona_file = folder_path / "persona.ini"
                    if persona_file.exists():
                        persona_name = folder_path.name
                        persona_data = self.load_persona(persona_name)
                        if persona_data:
                            personas.append({
                                "name": persona_name,
                                "description": persona_data.get("meta", {}).get(
                                    "description", persona_name
                                ),
                            })

        return (
            sorted(personas, key=lambda x: x["name"])
            if personas
            else [{"name": "default", "description": "Default"}]
        )

    def load_persona(self, persona_name: str) -> Optional[dict[str, Any]]:
        """Load a persona configuration from file."""
        if persona_name in self._persona_cache:
            return self._persona_cache[persona_name]

        # Handle default persona
        if persona_name == "default":
            persona_file = Path("persona.ini")
        else:
            # Check new folder structure first: personas/persona_name/persona.ini
            persona_file = self.personas_dir / persona_name / "persona.ini"
            if not persona_file.exists():
                # Fall back to old structure: personas/persona_name.ini
                persona_file = self.personas_dir / f"{persona_name}.ini"

        if not persona_file.exists():
            logger.warning(f"Persona file not found: {persona_file}")
            return None

        try:
            config = configparser.ConfigParser()
            config.read(persona_file)

            persona_data = {
                "name": persona_name,
                "personality": dict(config.items("PERSONALITY"))
                if config.has_section("PERSONALITY")
                else {},
                "backstory": dict(config.items("BACKSTORY"))
                if config.has_section("BACKSTORY")
                else {},
                "meta": dict(config.items("META"))
                if config.has_section("META")
                else {},
            }

            # Migrate and convert personality values to integers
            from .persona import migrate_traits

            persona_data["personality"] = migrate_traits(persona_data["personality"])

            self._persona_cache[persona_name] = persona_data
            logger.info(f"Loaded persona: {persona_name}", "🎭")
            return persona_data

        except Exception as e:
            logger.error(f"Failed to load persona {persona_name}: {e}")
            return None

    def get_persona_instructions(self, persona_name: str) -> str:
        """Get formatted instructions for a specific persona."""
        persona_data = self.load_persona(persona_name)
        if not persona_data:
            return ""

        # Get persona-specific instructions from META section
        persona_specific_instructions = persona_data['meta'].get('instructions', '')

        # If this persona has specific instructions, use them instead of the default format
        if persona_specific_instructions and persona_name != 'default':
            return persona_specific_instructions

        # For default persona or personas without specific instructions, use compact format
        instructions = f"[PERSONA: {persona_data['meta'].get('description', persona_name)} | MOOD: {persona_data['meta'].get('mood', 'neutral')} | ENERGY: {persona_data['meta'].get('energy', 'medium')}]\n"

        # Format backstory as key-value pairs
        if persona_data['backstory']:
            backstory_parts = []
            for key, value in persona_data['backstory'].items():
                backstory_parts.append(f"{key}: {value}")
            instructions += f"Backstory: {'; '.join(backstory_parts)}\n"

        # Compact personality traits
        if persona_data["personality"]:
            traits = [
                f"{trait}:{value}"
                for trait, value in persona_data["personality"].items()
            ]
            instructions += f"Traits: {', '.join(traits)}\n"

        return instructions

    def switch_persona(self, persona_name: str) -> bool:
        """Switch to a different persona."""
        available_personas = [p["name"] for p in self.get_available_personas()]
        if persona_name not in available_personas:
            logger.warning(f"Persona not available: {persona_name}")
            return False

        self.current_persona = persona_name
        logger.info(f"Switched to persona: {persona_name}", "🎭")
        return True

    def get_current_persona_data(self) -> Optional[dict[str, Any]]:
        """Get data for the current persona."""
        return self.load_persona(self.current_persona)

    def get_current_persona_instructions(self) -> str:
        """Get instructions for the current persona."""
        return self.get_persona_instructions(self.current_persona)

    def get_persona_voice(self, persona_name: str) -> str:
        """Get the voice setting for a specific persona."""
        persona_data = self.load_persona(persona_name)
        if not persona_data:
            return "ballad"  # Default voice

        return persona_data['meta'].get('voice', 'ballad')

    def get_current_persona_voice(self) -> str:
        """Get the voice setting for the current persona."""
        return self.get_persona_voice(self.current_persona)

    def clear_persona_cache(self, persona_name: str = None) -> None:
        """Clear the cache for a specific persona or all personas."""
        if persona_name:
            self._persona_cache.pop(persona_name, None)
            logger.info(f"Cleared cache for persona: {persona_name}", "🎭")
        else:
            self._persona_cache.clear()
            logger.info("Cleared all persona cache", "🎭")


# Global persona manager instance
persona_manager = PersonaManager()
