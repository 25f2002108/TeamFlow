from flask import Blueprint
from flask_login import current_user, login_required
from ..extensions import db
from ..utils import payload, field

bp = Blueprint('users', __name__, url_prefix='/api/users')

@bp.patch('/me')
@login_required
def update():
    current_user.name = field(payload(), 'name', 2)
    db.session.commit()
    return dict(user=current_user.to_dict())
