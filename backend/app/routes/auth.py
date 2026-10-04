import secrets
from flask import Blueprint, abort, session
from flask_login import login_user, logout_user, login_required, current_user
from ..extensions import db
from ..models import User
from ..utils import payload, field, email_field

bp = Blueprint('auth', __name__, url_prefix='/api/auth')

def identity():
    return dict(user=current_user.to_dict(), teams=[m.team.to_dict(m.role) for m in current_user.memberships])

@bp.get('/csrf')
def csrf():
    if 'csrf' not in session:
        session['csrf'] = secrets.token_hex(32)
    return dict(csrf_token=session['csrf'])

@bp.post('/register')
def register():
    data = payload()
    name, email = field(data, 'name', 2), email_field(data)
    password = data.get('password')
    if not isinstance(password, str) or not 8 <= len(password) <= 128 or not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        abort(400, description='Use 8–128 characters with at least one letter and one number.')
    if password != data.get('confirm_password'):
        abort(400, description='Passwords do not match.')
    if db.session.scalar(db.select(User).filter_by(email=email)):
        abort(409, description='An account with this email already exists.')
    user = User(name=name, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    session.clear()
    login_user(user)
    return identity(), 201

@bp.post('/login')
def login():
    data = payload()
    email = email_field(data)
    password = data.get('password')
    user = db.session.scalar(db.select(User).filter_by(email=email))
    if not isinstance(password, str) or len(password) > 128 or not user or not user.check_password(password):
        abort(401, description='Email or password is incorrect.')
    session.clear()
    login_user(user, remember=data.get('remember') is True)
    return identity()

@bp.post('/supabase-login')
def supabase_login():
    data = payload()
    email = email_field(data)
    name = data.get('name')
    if not isinstance(name, str) or len(name.strip()) < 2:
        name = email.split('@')[0]
    else:
        name = name.strip()

    user = db.session.scalar(db.select(User).filter_by(email=email))
    if not user:
        user = User(name=name, email=email)
        user.set_password(secrets.token_urlsafe(32))
        db.session.add(user)
        db.session.commit()

    session.clear()
    login_user(user, remember=True)
    return identity()

@bp.get('/me')
@login_required
def me():
    return identity()

@bp.post('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return dict(message='Signed out.')
