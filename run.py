"""Run script for the Flask application."""
from app import create_app

app = create_app()

if __name__ == "__main__":
    # Development server. For production use a WSGI server (gunicorn / waitress)
    app.run(host="0.0.0.0", port=5000, debug=True)
  