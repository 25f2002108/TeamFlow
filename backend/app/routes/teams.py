from flask import Blueprint, abort
from flask_login import current_user, login_required
from ..extensions import db
from ..models import Team, TeamMember
from ..utils import payload, field, team_access
from ..services.team_service import generate_code
from ..services.project_service import unassign_departing_member

bp = Blueprint('teams', __name__, url_prefix='/api/teams')

@bp.post('')
@login_required
def create():
    team = Team(name=field(payload(), 'name', 2), team_code=generate_code(), created_by=current_user.id)
    db.session.add(team)
    db.session.flush()
    db.session.add(TeamMember(user_id=current_user.id, team_id=team.id, role='LEADER'))
    db.session.commit()
    return dict(team=team.to_dict('LEADER')), 201

@bp.post('/join')
@login_required
def join():
    code = field(payload(), 'team_code', 4, 20).upper().replace(' ', '')
    team = db.session.scalar(db.select(Team).filter_by(team_code=code))
    if not team:
        abort(404, description='Team code not found. Check the code with your team leader.')
    if db.session.scalar(db.select(TeamMember).filter_by(team_id=team.id, user_id=current_user.id)):
        abort(409, description='You already belong to this team. Select it in the team switcher.')
    db.session.add(TeamMember(user_id=current_user.id, team_id=team.id, role='MEMBER'))
    db.session.commit()
    return dict(team=team.to_dict('MEMBER')), 201

@bp.get('/<int:team_id>')
@team_access()
def detail(team_id, membership):
    return dict(team=membership.team.to_dict(membership.role), members=[dict(**m.user.to_dict(), role=m.role, joined_at=m.joined_at.isoformat()+'Z') for m in membership.team.memberships])

@bp.patch('/<int:team_id>')
@team_access(leader=True)
def update(team_id, membership):
    membership.team.name = field(payload(), 'name', 2)
    db.session.commit()
    return dict(team=membership.team.to_dict(membership.role))

@bp.delete('/<int:team_id>/members/<int:user_id>')
@team_access(leader=True)
def remove(team_id, membership, user_id):
    target = db.session.scalar(db.select(TeamMember).filter_by(team_id=team_id, user_id=user_id))
    if not target:
        abort(404, description='Member not found.')
    if target.role == 'LEADER':
        abort(400, description='Team leaders cannot be removed. Leadership transfer is not available yet.')
    unassign_departing_member(team_id, user_id)
    db.session.delete(target)
    db.session.commit()
    return dict(message='Member removed.')

@bp.post('/<int:team_id>/leave')
@team_access()
def leave(team_id, membership):
    if membership.role == 'LEADER':
        abort(400, description='A leader cannot leave their team until leadership transfer is available.')
    unassign_departing_member(team_id, current_user.id)
    db.session.delete(membership)
    db.session.commit()
    return dict(message='You left the team.')
