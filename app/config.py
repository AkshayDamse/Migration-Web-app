"""
Configuration for Flask app.

Put secrets in environment variables for production.
"""
import os


class Config:
    # Use an environment variable for SECRET_KEY in production
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-me")
    # Add other configuration (DB URI, Celery broker, etc.) as you scale
