from datetime import date, datetime, timezone
from functools import wraps
from flask import abort, request
from flask_login import current_user, login_required
from ..extensions import db
from ..models import Project, Task, TeamMember, Activity, now

STATUSES = ('TODO', 'IN_PROGRESS', 'REVIEW', 'DONE')
PRIORITIES = ('LOW', 'MEDIUM', 'HIGH', 'URGENT')

def access(project, leader=False):
    if not project:
        abort(404, description='Project not found.')
    member = db.session.scalar(db.select(TeamMember).filter_by(team_id=project.team_id, user_id=current_user.id))
    if not member:
        abort(403, description='You do not have access to this project.')
    if leader and member.role != 'LEADER':
        abort(403, description='Only a team leader can manage projects and tasks.')
    return member

def project_access(leader=False):
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapped(project_id, *args, **kwargs):
            project = db.session.get(Project, project_id)
            membership = access(project, leader)
            return fn(project, membership, *args, **kwargs)
        return wrapped
    return decorator

def task_access(fn):
    @wraps(fn)
    @login_required
    def wrapped(task_id, *args, **kwargs):
        task = db.session.get(Task, task_id)
        if not task:
            abort(404, description='Task not found.')
        membership = access(task.project)
        return fn(task, membership, *args, **kwargs)
    return wrapped

def deadline(value):
    if value is None or value == '':
        return None
    if not isinstance(value, str) or len(value) != 10:
        abort(400, description='Use a calendar date in YYYY-MM-DD format.')
    try:
        return date.fromisoformat(value)
    except ValueError:
        abort(400, description='Enter a valid calendar date.')

def today():
    return deadline(request.args.get('today')) or datetime.now(timezone.utc).date()

def text(data, key, maximum=10000):
    value = data.get(key, '')
    if not isinstance(value, str) or len(value) > maximum:
        abort(400, description=f'{key.capitalize()} must be text of at most {maximum} characters.')
    return value.strip()

def assignee(value, team_id):
    if value is None:
        return None
    if type(value) is not int or not db.session.scalar(db.select(TeamMember).filter_by(user_id=value, team_id=team_id)):
        abort(400, description='Assign tasks only to a current member of this team.')
    return value

def workflow(status, progress):
    if status not in STATUSES:
        abort(400, description='Invalid task status.')
    if type(progress) is not int or not 0 <= progress <= 100:
        abort(400, description='Progress must be a whole number from 0 to 100.')
    if status == 'DONE' or progress == 100:
        return 'DONE', 100
    return status, progress

def record(project, action, entity, entity_id, **details):
    db.session.add(Activity(team_id=project.team_id, project_id=project.id, user_id=current_user.id, action_type=action, entity_type=entity, entity_id=entity_id, details=details))
    db.session.info.setdefault('changed_projects', set()).add(project.id)
    if entity == 'task' and action in ('TASK_ASSIGNED','TASK_REASSIGNED','COMMENT_ADDED'):
        from .workspace_service import notify
        task = db.session.get(Task,entity_id)
        if task:
            recipients = {task.assigned_to, task.created_by} if action == 'COMMENT_ADDED' else {task.assigned_to}
            for uid in recipients: notify(project,uid,action,f'{current_user.name} '+('commented on ' if action == 'COMMENT_ADDED' else 'assigned you to ')+task.title+'.',task_id=task.id)

def unassign_departing_member(team_id, user_id):
    tasks = db.session.scalars(db.select(Task).join(Project).where(Project.team_id == team_id, Task.assigned_to == user_id)).all()
    for task in tasks:
        task.assigned_to = None
        record(task.project, 'TASK_REASSIGNED', 'task', task.id, title=task.title, to='Unassigned', reason='Member left or was removed')

def dashboard(project, current_day):
    tasks = project.tasks
    counts = {status: sum(t.status == status for t in tasks) for status in STATUSES}
    def overdue(task):
        return task.status != 'DONE' and task.deadline and task.deadline < current_day
    def progress(items):
        return round(sum(t.progress for t in items) / len(items), 1) if items else 0
    members = []
    for membership in project.team.memberships:
        assigned = [t for t in tasks if t.assigned_to == membership.user_id]
        active = [t for t in assigned if t.status != 'DONE']
        score = sum({'LOW': 1, 'MEDIUM': 2, 'HIGH': 3, 'URGENT': 4}[t.priority] + (1 if t.deadline and (t.deadline-current_day).days <= 3 else 0) + min(3,max(0,__import__('math').ceil(t.plan.duration if t.plan else 1)-1)) for t in active)
        members.append(dict(user=membership.user.to_dict(), assigned=len(assigned), completed=sum(t.status == 'DONE' for t in assigned), active=len(active), overdue=sum(bool(overdue(t)) for t in assigned), progress=progress(assigned), workload_score=score, workload='Light' if score <= 3 else 'Balanced' if score <= 7 else 'High' if score <= 11 else 'Overloaded'))
    upcoming = sorted([t for t in tasks if t.deadline and t.status != 'DONE'], key=lambda t: (t.deadline, t.id))[:6]
    from .planning import insights
    return dict(total=len(tasks), statuses=counts, overdue=sum(bool(overdue(t)) for t in tasks), progress=progress(tasks), members=members, deadlines=[t.to_dict() for t in upcoming], unassigned=sum(t.assigned_to is None for t in tasks), today=current_day.isoformat(), **insights(project,current_day,members))
