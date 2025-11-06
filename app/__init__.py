"""
Application factory for the Flask app.

This file creates the Flask app, loads configuration, and registers blueprints.
Keeping an app factory makes the project easier to test and scale.
"""
from flask import Flask
from .config import Config


def create_app(config_object: object = None):
    """Create and configure the Flask application.

    Args:
        config_object: Optional config object (defaults to Config class)

    Returns:
        Flask app instance
    """
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # Load configuration
    if config_object is None:
        app.config.from_object(Config)
    else:
        app.config.from_object(config_object)

    # Register blueprints
    from .main import bp as main_bp

    app.register_blueprint(main_bp)

    # Initialize other extensions here (db, login, celery, etc.)

    return app
