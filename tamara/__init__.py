"""Application factory. Importing this package does not open the real database."""

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException
from .config import settings
from .database import configure_database
from .security import guard, security, http_error
from .validation import validate


def create_app(data_dir=None, testing=False):
    app = Flask(__name__, static_folder=None)
    app.config.update(settings(data_dir), TESTING=testing)
    from .proxy import TrustedProxy

    app.wsgi_app = TrustedProxy(app.wsgi_app, app.config["TRUSTED_PROXY_CIDRS"])
    configure_database(app)
    from .services.reference_panel import initialize

    initialize(app)
    from .services.bootstrap import initialize_admin

    initialize_admin(app)

    def validate_content(data):
        with app.app_context():
            return validate(data)

    app.validate_content = validate_content
    app.before_request(guard)
    app.after_request(security)
    app.register_error_handler(HTTPException, http_error)
    from .routes import public, auth, admin, media, reference_panel, bookings

    for routes in (public, auth, admin, media, reference_panel, bookings):
        app.register_blueprint(routes.bp)

    @app.errorhandler(Exception)
    def unexpected(error):
        if app.testing:
            raise error
        app.logger.exception("Solicitud fallida")
        return jsonify(
            error="No se pudo completar la operación. Intenta de nuevo o contacta al administrador."
        ), 500

    return app
