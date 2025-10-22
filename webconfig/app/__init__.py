import os
import sys

from flask import Flask


def create_app() -> Flask:
    # Ensure project root on path for core imports
    sys.path.append(
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    )

    base_dir = os.path.dirname(__file__)
    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, "..", "templates"),
        static_folder=os.path.join(base_dir, "..", "static"),
    )

    # Late imports to avoid circulars
    from .routes.audio import bp as audio_bp
    from .routes.misc import bp as misc_bp
    from .routes.persona import bp as persona_bp
    from .routes.profiles import profiles_bp
    from .routes.system import bp as system_bp
    from .state import bootstrap_versions_and_release_note

    # Bootstrap cached data
    bootstrap_versions_and_release_note()

    # Register blueprints
    app.register_blueprint(system_bp)
    app.register_blueprint(persona_bp)
    app.register_blueprint(profiles_bp)
    app.register_blueprint(audio_bp)
    app.register_blueprint(misc_bp)

    return app
