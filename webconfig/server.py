from app import create_app
from app.core_imports import core_config


app = create_app()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(core_config.FLASK_PORT),
        debug=False,
        use_reloader=False,
    )
