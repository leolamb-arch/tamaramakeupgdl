"""Application factory. Importing this package does not open the real database."""

from flask import Flask
from werkzeug.exceptions import HTTPException
from .config import settings
from .database import configure_database
from .security import guard, security, http_error
from .validation import validate


def create_app(data_dir=None, testing=False):
    app = Flask(__name__, static_folder=None)
    app.config.update(settings(data_dir), TESTING=testing)
    configure_database(app)
    from .services.reference_panel import initialize
    initialize(app)

    def validate_content(data):
        with app.app_context():
            return validate(data)

    app.validate_content = validate_content
    app.before_request(guard)
    app.after_request(security)
    app.register_error_handler(HTTPException, http_error)
    from .routes import public, auth, admin, media, reference_panel

    for routes in (public, auth, admin, media, reference_panel):
        app.register_blueprint(routes.bp)
    return app
