import re
from flask import abort
from flask_login import current_user
from ..extensions import db
from ..models import WorkspaceNode, FilePermission, TeamMember, Notification
from .project_service import access, record

PERMISSIONS = ('VIEW','EDIT','NO_ACCESS','FULL_ACCESS')
MAX_CONTENT = 512 * 1024

def effective(node, user_id=None):
    uid = user_id if user_id is not None else current_user.id
    member = db.session.scalar(db.select(TeamMember).filter_by(team_id=node.project.team_id, user_id=uid))
    if not member: return 'NO_ACCESS'
    if member.role == 'LEADER': return 'FULL_ACCESS'
    chosen = None
    cursor = node
    while cursor:
        rule = next((p.permission for p in cursor.permissions if p.user_id == uid), None)
        if rule == 'NO_ACCESS': return 'NO_ACCESS'
        if chosen is None and rule: chosen = rule
        cursor = cursor.parent
    return chosen or 'VIEW'

def node_access(node_id, require=None):
    node = db.session.get(WorkspaceNode, node_id)
    if not node: abort(404, description='Workspace node not found.')
    membership = access(node.project)
    permission = effective(node)
    if permission == 'NO_ACCESS': abort(403, description='You do not have access to this workspace node.')
    if require == 'edit' and permission not in ('EDIT','FULL_ACCESS'): abort(403, description='This file is read only. EDIT access is required.')
    if require == 'manage' and permission != 'FULL_ACCESS': abort(403, description='FULL_ACCESS is required to manage this node.')
    return node, membership, permission

def name(value):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 120:
        abort(400, description='Use a file or folder name of 1–120 characters.')
    value = value.strip()
    if value in ('.','..') or re.search(r'[\\/:*?"<>|\x00-\x1f]', value) or value.endswith('.') or value.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}:
        abort(400, description='Names cannot contain path separators, control characters, or reserved filename characters.')
    return value

def content(value):
    if not isinstance(value, str) or '\x00' in value or len(value.encode('utf-8')) > MAX_CONTENT:
        abort(400, description='Workspace files must be UTF-8 text, without null bytes, up to 512 KB.')
    return value

def descendants(node):
    return [node] + [child for n in node.children for child in descendants(n)]

def workspace_record(node, action, **details):
    audience = [m.user_id for m in node.project.team.memberships if effective(node, m.user_id) != 'NO_ACCESS']
    record(node.project, action, 'node', node.id, title=node.name, path=node.path, _audience=audience, **details)

def visible_activity(activity, uid):
    audience = activity.details.get('_audience')
    if audience is not None and uid not in audience: return False
    if activity.entity_type == 'node':
        node = db.session.get(WorkspaceNode, activity.entity_id)
        if node and effective(node, uid) == 'NO_ACCESS': return False
    return True

def notify(project, uid, kind, message, task_id=None, node_id=None):
    if uid and uid != current_user.id and db.session.scalar(db.select(TeamMember).filter_by(team_id=project.team_id, user_id=uid)):
        db.session.add(Notification(user_id=uid, project_id=project.id, kind=kind, message=message[:500], task_id=task_id, node_id=node_id))
        db.session.info.setdefault('notification_users',set()).add(uid)

def task_notifications(task, kind, message):
    notify(task.project, task.assigned_to, kind, message, task_id=task.id)
