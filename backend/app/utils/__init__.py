import re
from functools import wraps
from flask import request, abort
from flask_login import current_user, login_required
from ..models import TeamMember
from ..extensions import db

def payload():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400, description='Send a JSON object.')
    return data

def field(data, key, minimum=1, maximum=80):
    value = data.get(key)
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
        abort(400, description=f'{key.replace("_", " ").capitalize()} must be {minimum}–{maximum} characters.')
    return value.strip()

def email_field(data):
    email = field(data, 'email', 3, 254).lower()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
        abort(400, description='Enter a valid email address.')
    return email

def team_access(leader=False):
    def decorate(fn):
        @wraps(fn)
        @login_required
        def wrapped(team_id, *args, **kwargs):
            membership = db.session.scalar(db.select(TeamMember).filter_by(team_id=team_id, user_id=current_user.id))
            if not membership:
                abort(403, description='You are not a member of this team.')
            if leader and membership.role != 'LEADER':
                abort(403, description='Only a team leader can perform this action.')
            return fn(team_id, membership, *args, **kwargs)
        return wrapped
    return decorate
