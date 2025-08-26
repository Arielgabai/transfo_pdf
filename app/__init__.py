from flask import Flask
import os


def create_app() -> Flask:
    app = Flask(__name__)

    # Configuration
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
    app_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    app.config["UPLOAD_FOLDER"] = os.path.join(app_root, "uploads")
    app.config["OUTPUT_FOLDER"] = os.path.join(app_root, "output")
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["OUTPUT_FOLDER"], exist_ok=True)

    from .routes import bp as main_bp

    app.register_blueprint(main_bp)

    return app


