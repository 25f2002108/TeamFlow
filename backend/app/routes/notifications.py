from flask import Blueprint, abort
from flask_login import current_user, login_required
from ..extensions import db
from ..models import Notification, TeamMember

bp=Blueprint('notifications', __name__, url_prefix='/api/notifications')

@bp.get('')
@login_required
def list_notifications():
    rows=db.session.scalars(db.select(Notification).filter_by(user_id=current_user.id).order_by(Notification.id.desc())).all()
    rows=[n for n in rows if db.session.scalar(db.select(TeamMember).filter_by(team_id=n.project.team_id,user_id=current_user.id))]
    return dict(notifications=[n.to_dict() for n in rows[:100]], unread=sum(not n.read for n in rows))

@bp.patch('/<int:notification_id>/read')
@login_required
def read(notification_id):
    item=db.session.get(Notification,notification_id)
    if not item or item.user_id != current_user.id: abort(404,description='Notification not found.')
    item.read=True; db.session.commit(); return dict(message='Notification read.')

@bp.post('/read-all')
@login_required
def read_all():
    db.session.execute(db.update(Notification).where(Notification.user_id==current_user.id).values(read=True))
    db.session.commit(); return dict(message='Notifications read.')
