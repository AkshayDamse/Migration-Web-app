"""Main blueprint package."""
from flask import Blueprint

bp = Blueprint("main", __name__)

from . import routes  # noqa: E402,F401 (import routes to register view functions)
