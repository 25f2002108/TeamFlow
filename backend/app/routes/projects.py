from flask import Blueprint
from flask_login import current_user
from ..extensions import db
from ..models import Project, Activity
from ..utils import team_access, payload, field
from ..services.project_service import project_access, deadline, text, record, dashboard, today

bp = Blueprint('projects', __name__, url_prefix='/api')

@bp.get('/teams/<int:team_id>/projects')
@team_access()
def list_projects(team_id, membership):
    projects = db.session.scalars(db.select(Project).filter_by(team_id=team_id).order_by(Project.created_at, Project.id)).all()
    return dict(projects=[p.to_dict() for p in projects])

@bp.post('/teams/<int:team_id>/projects')
@team_access(leader=True)
def create(team_id, membership):
    data = payload()
    project = Project(team_id=team_id, name=field(data, 'name', 2, 120), description=text(data, 'description'), deadline=deadline(data.get('deadline')), created_by=current_user.id)
    db.session.add(project)
    db.session.flush()
    record(project, 'PROJECT_CREATED', 'project', project.id, title=project.name)
    db.session.commit()
    return dict(project=project.to_dict()), 201

@bp.get('/projects/<int:project_id>')
@project_access()
def detail(project, membership):
    return dict(project=project.to_dict())

@bp.patch('/projects/<int:project_id>')
@project_access(leader=True)
def update(project, membership):
    data = payload()
    changes = []
    for key, value in [('name', field(data, 'name', 2, 120) if 'name' in data else project.name), ('description', text(data, 'description') if 'description' in data else project.description), ('deadline', deadline(data.get('deadline')) if 'deadline' in data else project.deadline)]:
        if getattr(project, key) != value:
            setattr(project, key, value); changes.append(key)
    if changes:
        record(project, 'PROJECT_EDITED', 'project', project.id, title=project.name, fields=changes)
    db.session.commit()
    return dict(project=project.to_dict())

@bp.get('/projects/<int:project_id>/dashboard')
@project_access()
def metrics(project, membership):
    result = dashboard(project, today())
    if membership.role != 'LEADER':
        result.pop('members')
    return dict(dashboard=result)

@bp.get('/projects/<int:project_id>/activity')
@project_access()
def activity(project, membership):
    from flask import request, abort
    try:
        offset = int(request.args.get('offset', '0'))
        if offset < 0: raise ValueError
    except ValueError:
        abort(400, description='Invalid activity offset.')
    from ..services.workspace_service import visible_activity
    rows = db.session.scalars(db.select(Activity).filter_by(project_id=project.id).order_by(Activity.created_at.desc(), Activity.id.desc())).all()
    rows = [row for row in rows if visible_activity(row,current_user.id)][offset:offset+51]
    return dict(activity=[row.to_dict() for row in rows[:50]], has_more=len(rows) > 50)
