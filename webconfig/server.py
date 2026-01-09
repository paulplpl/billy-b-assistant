import os

from dotenv import load_dotenv


# Ensure .env is loaded before any imports that depend on it
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
env_path = os.path.join(project_root, ".env")
load_dotenv(dotenv_path=env_path, override=True)

from app import create_app
from app.core_imports import core_config

# Initialize user manager to load default user and persona
from core.profile_manager import user_manager


user_manager.load_default_user()

app = create_app()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(core_config.FLASK_PORT),
        debug=False,
        use_reloader=False,
    )
