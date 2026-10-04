import os
import secrets
from pathlib import Path

from flask import Flask, request, session, abort, g
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError
from dotenv import load_dotenv

from .extensions import db, login_manager, socketio


from urllib.parse import urlparse


def is_allowed_origin(origin, frontend_origin_setting, request_host_url=None):
    if not origin:
        return True

    origin_clean = origin.rstrip('/')

    if request_host_url and origin_clean == request_host_url.rstrip('/'):
        return True

    allowed_list = [
        o.strip().rstrip('/')
        for o in (frontend_origin_setting or "").split(',')
        if o.strip()
    ]

    if "*" in allowed_list or origin_clean in allowed_list:
        return True

    parsed_origin = urlparse(origin_clean)
    if parsed_origin.hostname in ("localhost", "127.0.0.1"):
        for allowed in allowed_list:
            parsed_allowed = urlparse(allowed)
            if parsed_allowed.hostname in ("localhost", "127.0.0.1"):
                if parsed_origin.port == parsed_allowed.port:
                    return True
                if parsed_origin.port in (5173, 5174, 5000, 5001) or parsed_origin.port is None:
                    return True

    if os.getenv("VERCEL") or os.getenv("VERCEL_ENV"):
        if parsed_origin.hostname and parsed_origin.hostname.endswith(".vercel.app"):
            return True

    return False


def create_app(config=None):
    load_dotenv()

    # Vercel's application filesystem (/var/task) is read-only.
    # Use /tmp on Vercel, while keeping the normal instance folder locally.
    if os.getenv("VERCEL"):
        app = Flask(
            __name__,
            instance_path="/tmp/teamflow-instance"
        )
    else:
        app = Flask(
            __name__,
            instance_relative_config=True
        )

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    # Secret key
    secret = os.getenv("SECRET_KEY")

    if not secret:
        secret_path = Path(app.instance_path) / "session-secret"

        if not secret_path.exists():
            secret_path.write_text(secrets.token_hex(32))

        secret = secret_path.read_text().strip()

    # Database URI configuration (Supports Supabase PostgreSQL & SQLite fallback)
    db_uri = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DATABASE_URL")
    if db_uri:
        if db_uri.startswith("postgres://"):
            db_uri = db_uri.replace("postgres://", "postgresql://", 1)
    else:
        db_uri = "sqlite:///teamflow.db"

    # Application configuration
    app.config.update(
        SECRET_KEY=secret,

        SQLALCHEMY_DATABASE_URI=db_uri,

        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=(
            os.getenv("COOKIE_SECURE", "false").lower() == "true"
        ),

        REMEMBER_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_SAMESITE="Lax",
        REMEMBER_COOKIE_SECURE=(
            os.getenv("COOKIE_SECURE", "false").lower() == "true"
        ),

        FRONTEND_ORIGIN=os.getenv(
            "FRONTEND_ORIGIN",
            "http://localhost:5173"
        ),
    )

    if config:
        app.config.update(config)

    # Writable uploads directory
    app.config.setdefault(
        "UPLOAD_FOLDER",
        str(Path(app.instance_path) / "uploads")
    )

    app.config["MAX_CONTENT_LENGTH"] = (
        app.config.get("MAX_CONTENT_LENGTH")
        or 12 * 1024 * 1024
    )

    Path(app.config["UPLOAD_FOLDER"]).mkdir(
        parents=True,
        exist_ok=True
    )

    # Extensions
    db.init_app(app)
    login_manager.init_app(app)

    socketio.init_app(
        app,
        cors_allowed_origins="*",
        max_http_buffer_size=1024 * 1024,
    )

    app.extensions["teamflow_presence"] = {}

    # Models
    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return (
            db.session.get(User, int(user_id))
            if user_id.isdigit()
            else None
        )

    @login_manager.unauthorized_handler
    def unauthorized():
        return {"error": "Please sign in to continue."}, 401

    # CSRF / mutation protection
    @app.before_request
    def protect_mutations():
        from flask_login import current_user

        g.socket_uid = (
            current_user.id
            if current_user.is_authenticated
            else None
        )

        g.socket_csrf = session.get("csrf")

        if (
            request.method in ("POST", "PATCH", "PUT", "DELETE")
            and request.path.startswith("/api/")
        ):
            origin = request.headers.get("Origin")

            if origin and not is_allowed_origin(
                origin,
                app.config.get("FRONTEND_ORIGIN", ""),
                request.host_url
            ):
                abort(
                    403,
                    description="Request origin is not allowed."
                )

            expected = session.get("csrf")

            if (
                not expected
                or not secrets.compare_digest(
                    expected,
                    request.headers.get("X-CSRF-Token", "")
                )
            ):
                abort(
                    403,
                    description=(
                        "Session verification expired. Please retry."
                    ),
                )

    # Error handlers
    @app.errorhandler(HTTPException)
    def http_error(error):
        return {"error": error.description}, error.code

    @app.errorhandler(IntegrityError)
    def conflict(error):
        db.session.rollback()

        return {
            "error": (
                "This record already exists. "
                "Please refresh and try again."
            )
        }, 409

    @app.errorhandler(StaleDataError)
    def stale(error):
        db.session.rollback()

        return {
            "error": (
                "This task changed during your update. "
                "Refresh and retry."
            )
        }, 409

    @app.errorhandler(Exception)
    def unexpected(error):
        db.session.rollback()
        app.logger.exception("Unexpected request error")

        return {
            "error": "Something went wrong. Please try again."
        }, 500

    # Blueprints
    from .routes import (
        auth,
        teams,
        users,
        projects,
        tasks,
        workspace,
        notifications,
        planning,
        archives,
        execution,
    )

    for module in (
        auth,
        teams,
        users,
        projects,
        tasks,
        workspace,
        notifications,
        planning,
        archives,
        execution,
    ):
        app.register_blueprint(module.bp)

    # Realtime handlers
    from .realtime import publish_response, register_handlers

    register_handlers()

    app.after_request(publish_response)

    # Database initialization
    with app.app_context():
        db.create_all()

        from .models import Task
        from .services.planning import snapshot

        for task in db.session.scalars(
            db.select(Task)
        ).all():
            snapshot(task)

        db.session.commit()

    return app