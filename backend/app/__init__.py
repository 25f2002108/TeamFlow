import os
import secrets
from pathlib import Path
from flask import Flask, request, session, abort, g
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError
from dotenv import load_dotenv
from .extensions import db, login_manager, socketio

def create_app(config=None):
    load_dotenv()
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    secret = os.getenv('SECRET_KEY')
    if not secret:
        secret_path = Path(app.instance_path) / 'session-secret'
        if not secret_path.exists():
            secret_path.write_text(secrets.token_hex(32))
        secret = secret_path.read_text().strip()
    app.config.update(SECRET_KEY=secret, SQLALCHEMY_DATABASE_URI='sqlite:///teamflow.db', SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=os.getenv('COOKIE_SECURE', 'false').lower() == 'true', REMEMBER_COOKIE_HTTPONLY=True, REMEMBER_COOKIE_SAMESITE='Lax', REMEMBER_COOKIE_SECURE=os.getenv('COOKIE_SECURE', 'false').lower() == 'true', FRONTEND_ORIGIN=os.getenv('FRONTEND_ORIGIN', 'http://localhost:5173'))
    if config:
        app.config.update(config)
    app.config.setdefault('UPLOAD_FOLDER', str(Path(app.instance_path) / 'uploads'))
    app.config['MAX_CONTENT_LENGTH'] = app.config.get('MAX_CONTENT_LENGTH') or 12 * 1024 * 1024
    Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app, cors_allowed_origins=[app.config['FRONTEND_ORIGIN']], max_http_buffer_size=1024*1024)
    app.extensions['teamflow_presence'] = {}
    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id)) if user_id.isdigit() else None
    @login_manager.unauthorized_handler
    def unauthorized():
        return dict(error='Please sign in to continue.'), 401
    @app.before_request
    def protect_mutations():
        from flask_login import current_user
        g.socket_uid = current_user.id if current_user.is_authenticated else None
        g.socket_csrf = session.get('csrf')
        if request.method in ('POST', 'PATCH', 'PUT', 'DELETE') and request.path.startswith('/api/'):
            origin = request.headers.get('Origin')
            if origin and origin != app.config['FRONTEND_ORIGIN']:
                abort(403, description='Request origin is not allowed.')
            expected = session.get('csrf')
            if not expected or not secrets.compare_digest(expected, request.headers.get('X-CSRF-Token', '')):
                abort(403, description='Session verification expired. Please retry.')
    @app.errorhandler(HTTPException)
    def http_error(error):
        return dict(error=error.description), error.code
    @app.errorhandler(IntegrityError)
    def conflict(error):
        db.session.rollback()
        return dict(error='This record already exists. Please refresh and try again.'), 409
    @app.errorhandler(StaleDataError)
    def stale(error):
        db.session.rollback()
        return dict(error='This task changed during your update. Refresh and retry.'), 409
    @app.errorhandler(Exception)
    def unexpected(error):
        db.session.rollback()
        app.logger.exception('Unexpected request error')
        return dict(error='Something went wrong. Please try again.'), 500
    from .routes import auth, teams, users, projects, tasks, workspace, notifications, planning, archives, execution
    for module in (auth, teams, users, projects, tasks, workspace, notifications, planning, archives, execution):
        app.register_blueprint(module.bp)
    from .realtime import publish_response, register_handlers
    register_handlers()
    app.after_request(publish_response)
    with app.app_context():
        db.create_all()
        from .models import Task
        from .services.planning import snapshot
        for task in db.session.scalars(db.select(Task)).all(): snapshot(task)
        db.session.commit()
    return app
