from flask import Blueprint, abort, request
from flask_login import current_user, login_required
from ..extensions import db
from ..models import WorkspaceNode, FilePermission, TaskFile, Task, CodeComment, TeamMember
from ..utils import payload, field
from ..services.project_service import project_access, task_access, record
from ..services.workspace_service import effective, node_access, name, content, descendants, workspace_record, PERMISSIONS, notify

bp = Blueprint('workspace', __name__, url_prefix='/api')

@bp.get('/projects/<int:project_id>/workspace')
@project_access()
def tree(project, membership):
    nodes = sorted(project.nodes, key=lambda n: (n.kind != 'folder', n.name_key, n.id))
    return dict(nodes=[n.to_dict(effective(n)) for n in nodes if effective(n) != 'NO_ACCESS'], root_permission='FULL_ACCESS' if membership.role == 'LEADER' else 'VIEW')

@bp.post('/projects/<int:project_id>/workspace')
@project_access()
def create(project, membership):
    data = payload(); parent_id = data.get('parent_id')
    if parent_id is not None:
        if type(parent_id) is not int: abort(400, description='Invalid parent folder.')
        parent, _, _ = node_access(parent_id, 'manage')
        if parent.project_id != project.id or parent.kind != 'folder': abort(400, description='Choose a folder in this project.')
    elif membership.role != 'LEADER': abort(403, description='Only the leader can create nodes at the workspace root.')
    kind = data.get('kind')
    if kind not in ('file','folder'): abort(400, description='Choose file or folder.')
    title = name(data.get('name'))
    node = WorkspaceNode(project_id=project.id, parent_id=parent_id, parent_scope=parent_id or 0, name=title, name_key=title.casefold(), kind=kind, content=content(data.get('content','')) if kind == 'file' else '', created_by=current_user.id)
    db.session.add(node); db.session.flush()
    workspace_record(node, 'FILE_CREATED' if kind == 'file' else 'FOLDER_CREATED')
    db.session.commit()
    return dict(node=node.to_dict(effective(node), True)), 201

@bp.get('/workspace/nodes/<int:node_id>')
@login_required
def detail(node_id):
    node, _, permission = node_access(node_id)
    related = [link.task.to_dict() for link in node.links]
    return dict(node=node.to_dict(permission, True), comments=[c.to_dict() for c in node.comments], tasks=related)

@bp.get('/workspace/nodes/<int:node_id>/download')
@login_required
def download_node(node_id):
    import io
    from flask import send_file
    node,_,_=node_access(node_id)
    if node.kind!='file': abort(400)
    return send_file(io.BytesIO(node.asset.data if node.asset else node.content.encode('utf-8')),as_attachment=True,download_name=node.name,mimetype='application/octet-stream',max_age=0)

@bp.patch('/workspace/nodes/<int:node_id>')
@login_required
def update(node_id):
    data = payload()
    if set(data) - {'name','content','version'}: abort(400, description='Unknown workspace field.')
    node, _, permission = node_access(node_id, 'manage' if 'name' in data else 'edit')
    if type(data.get('version')) is not int: abort(400, description='Send the file version you opened.')
    if data['version'] != node.version:
        return dict(error='This file changed while you were working. Your draft has been preserved. Reload the server version or copy your draft before retrying.', current=node.to_dict(permission, True)), 409
    if 'content' in data and node.kind != 'file': abort(400, description='Folders do not have editable content.')
    if 'content' in data and node.asset: abort(415,description='Binary assets cannot be edited as text.')
    if 'name' in data:
        value = name(data['name'])
        if value != node.name:
            previous = node.path; node.name = value; node.name_key = value.casefold()
            workspace_record(node, 'FILE_RENAMED', before=previous)
    if 'content' in data:
        value = content(data['content'])
        if value != node.content:
            node.content = value
            workspace_record(node, 'FILE_EDITED')
            recipients = {node.created_by} | {link.task.assigned_to for link in node.links}
            for uid in recipients:
                if uid and effective(node, uid) != 'NO_ACCESS': notify(node.project, uid, 'FILE_EDITED', f'{current_user.name} saved {node.path}.', node_id=node.id)
    db.session.commit()
    return dict(node=node.to_dict(effective(node), True))

@bp.delete('/workspace/nodes/<int:node_id>')
@login_required
def delete(node_id):
    node, _, _ = node_access(node_id, 'manage')
    if any(effective(child) != 'FULL_ACCESS' for child in descendants(node)):
        abort(403, description='You need FULL_ACCESS to every descendant to delete this folder.')
    workspace_record(node, 'FILE_DELETED' if node.kind == 'file' else 'FOLDER_DELETED')
    for child in descendants(node):
        for notification in child.notifications: notification.node_id = None
    db.session.delete(node); db.session.commit()
    return dict(message='Workspace node deleted.')

@bp.get('/workspace/nodes/<int:node_id>/permissions')
@login_required
def permissions(node_id):
    node, membership, _ = node_access(node_id)
    if membership.role != 'LEADER': abort(403, description='Only the team leader manages access rules.')
    return dict(members=[dict(user=m.user.to_dict(), role=m.role, permission=next((p.permission for p in node.permissions if p.user_id == m.user_id), None), effective=effective(node, m.user_id)) for m in node.project.team.memberships], default='VIEW')

@bp.put('/workspace/nodes/<int:node_id>/permissions')
@login_required
def set_permissions(node_id):
    node, membership, _ = node_access(node_id)
    if membership.role != 'LEADER': abort(403, description='Only the team leader manages access rules.')
    rules = payload().get('permissions')
    if not isinstance(rules, list) or len(rules) > len(node.project.team.memberships): abort(400, description='Send a list of member permission rules.')
    seen = set(); valid = []
    for rule in rules:
        if not isinstance(rule, dict) or type(rule.get('user_id')) is not int or rule['user_id'] in seen: abort(400, description='Invalid or duplicate member rule.')
        seen.add(rule['user_id'])
        member = db.session.scalar(db.select(TeamMember).filter_by(team_id=node.project.team_id, user_id=rule['user_id']))
        if not member or member.role == 'LEADER': abort(400, description='Choose a current non-leader team member.')
        permission = rule.get('permission')
        if permission is not None and permission not in PERMISSIONS: abort(400, description='Invalid permission.')
        valid.append((member.user_id, permission))
    for uid, permission in valid:
        existing = next((p for p in node.permissions if p.user_id == uid), None)
        if (existing.permission if existing else None) == permission: continue
        if permission is None:
            if existing: db.session.delete(existing)
        elif existing: existing.permission = permission
        else: db.session.add(FilePermission(project_id=node.project_id, node_id=node.id, user_id=uid, permission=permission))
        notify(node.project, uid, 'PERMISSION_CHANGED', 'Your workspace access was updated. Review the project workspace.', node_id=node.id if permission != 'NO_ACCESS' else None)
    workspace_record(node, 'PERMISSION_CHANGED')
    db.session.commit()
    return dict(message='Permissions saved.')

@bp.get('/tasks/<int:task_id>/files')
@task_access
def related_files(task, membership):
    return dict(files=[link.node.to_dict(effective(link.node)) for link in task.file_links if effective(link.node) != 'NO_ACCESS'])

@bp.post('/tasks/<int:task_id>/files')
@task_access
def link_file(task, membership):
    if membership.role != 'LEADER': abort(403, description='Only a leader can link or unlink task files.')
    nid = payload().get('node_id')
    if type(nid) is not int: abort(400, description='Choose a workspace file.')
    node, _, _ = node_access(nid)
    if node.project_id != task.project_id or node.kind != 'file': abort(400, description='Choose a file in this task’s project.')
    if any(l.node_id == nid for l in task.file_links): abort(409, description='This file is already linked.')
    db.session.add(TaskFile(task_id=task.id, node_id=nid, created_by=current_user.id)); task.version += 1
    record(task.project, 'TASK_FILE_LINKED', 'task', task.id, title=task.title)
    db.session.commit()
    return dict(message='File linked.'), 201

@bp.delete('/tasks/<int:task_id>/files/<int:node_id>')
@task_access
def unlink_file(task, membership, node_id):
    if membership.role != 'LEADER': abort(403, description='Only a leader can link or unlink task files.')
    link = next((l for l in task.file_links if l.node_id == node_id), None)
    if not link: abort(404, description='Related file not found.')
    db.session.delete(link); task.version += 1
    record(task.project, 'TASK_FILE_UNLINKED', 'task', task.id, title=task.title)
    db.session.commit(); return dict(message='File unlinked.')

@bp.post('/workspace/nodes/<int:node_id>/comments')
@login_required
def comment(node_id):
    node, _, _ = node_access(node_id)
    if node.kind != 'file' or node.asset: abort(400, description='Code comments belong to text files.')
    data=payload(); start=data.get('line_start'); end=data.get('line_end', start)
    if type(start) is not int or type(end) is not int or not 1 <= start <= end <= len(node.content.split('\n')): abort(400, description='Choose a valid line range in the saved file.')
    if type(data.get('version')) is not int or data['version'] != node.version: abort(409, description='Save or reload the file before commenting on its current lines.')
    tid=data.get('task_id')
    if tid is not None:
        task = db.session.get(Task, tid) if type(tid) is int else None
        if not task or task.project_id != node.project_id or not any(link.task_id == tid for link in node.links): abort(400, description='Choose a task linked to this file.')
    item=CodeComment(node_id=node.id, task_id=tid, user_id=current_user.id, line_start=start, line_end=end, file_version=node.version, content=field(data,'content',1,5000))
    db.session.add(item); workspace_record(node,'CODE_COMMENT_ADDED')
    for uid in {node.created_by} | {link.task.assigned_to for link in node.links}:
        if uid and effective(node, uid) != 'NO_ACCESS': notify(node.project, uid, 'CODE_COMMENT', f'{current_user.name} commented on {node.path}.', node_id=node.id, task_id=tid)
    db.session.commit(); return dict(comment=item.to_dict()), 201

@bp.patch('/workspace/comments/<int:comment_id>')
@login_required
def resolve(comment_id):
    item=db.session.get(CodeComment,comment_id)
    if not item: abort(404,description='Code comment not found.')
    node, membership, permission=node_access(item.node_id)
    if membership.role != 'LEADER' and item.user_id != current_user.id and permission not in ('EDIT','FULL_ACCESS'): abort(403,description='Only the author, an editor, or leader can resolve comments.')
    value=payload().get('resolved')
    if type(value) is not bool: abort(400,description='Send a resolved boolean.')
    if item.resolved != value: item.resolved=value; workspace_record(node,'CODE_COMMENT_RESOLVED' if value else 'CODE_COMMENT_REOPENED')
    db.session.commit(); return dict(comment=item.to_dict())
