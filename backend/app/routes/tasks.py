import mimetypes
import secrets
from pathlib import Path
from flask import Blueprint, abort, current_app, request, send_file
from flask_login import current_user
from werkzeug.utils import secure_filename
from ..extensions import db
from ..models import Task, Comment, Attachment, Activity, now
from ..utils import payload, field
from ..services.project_service import project_access, task_access, text, deadline, assignee, workflow, PRIORITIES, record
from ..services.planning import snapshot, set_duration, FIELDS, fields
from ..models.planning import TaskRevision

bp = Blueprint('tasks', __name__, url_prefix='/api')
ALLOWED_EXTENSIONS = {'txt','md','csv','json','pdf','png','jpg','jpeg','webp','docx','xlsx','pptx','zip'}
MAX_FILE_SIZE = 10 * 1024 * 1024

@bp.get('/projects/<int:project_id>/tasks')
@project_access()
def list_tasks(project, membership):
    return dict(tasks=[t.to_dict() for t in sorted(project.tasks, key=lambda t: t.id)])

@bp.post('/projects/<int:project_id>/tasks')
@project_access(leader=True)
def create(project, membership):
    data = payload()
    priority = data.get('priority', 'MEDIUM')
    if priority not in PRIORITIES:
        abort(400, description='Invalid task priority.')
    status, progress = workflow(data.get('status', 'TODO'), data.get('progress', 0))
    task = Task(project_id=project.id, title=field(data, 'title', 2, 180), description=text(data, 'description'), assigned_to=assignee(data.get('assigned_to'), project.team_id), priority=priority, deadline=deadline(data.get('deadline')), status=status, progress=progress, created_by=current_user.id)
    db.session.add(task)
    db.session.flush()
    if 'estimated_duration' in data: set_duration(task,data['estimated_duration'])
    snapshot(task)
    record(project, 'TASK_CREATED', 'task', task.id, title=task.title)
    if task.assigned_to:
        record(project, 'TASK_ASSIGNED', 'task', task.id, title=task.title, to=task.assignee.name)
    db.session.commit()
    return dict(task=task.to_dict()), 201

@bp.get('/tasks/<int:task_id>')
@task_access
def detail(task, membership):
    activities = db.session.scalars(db.select(Activity).filter_by(project_id=task.project_id, entity_type='task', entity_id=task.id).order_by(Activity.created_at.desc(), Activity.id.desc()).limit(50)).all()
    return dict(task=task.to_dict(), comments=[c.to_dict() for c in task.comments], attachments=[a.to_dict() for a in task.attachments], activity=[a.to_dict() for a in activities])

@bp.patch('/tasks/<int:task_id>')
@task_access
def update(task, membership):
    data = payload()
    if membership.role != 'LEADER':
        if task.assigned_to != current_user.id:
            abort(403, description='Only the assigned member or a leader can update this task.')
        if set(data) - {'status', 'progress', 'version', 'merge'}:
            abort(403, description='Members can update only status and progress on their assigned tasks.')
    elif set(data) - {'title','description','assigned_to','priority','deadline','status','progress','version','merge','estimated_duration'}:
        abort(400, description='Unknown task field.')
    if type(data.get('version')) is not int: abort(400,description='Expected task version is required.')
    if data['version'] != task.version:
        revision=db.session.scalar(db.select(TaskRevision).filter_by(task_id=task.id,version=data['version']))
        current=fields(task); base=revision.fields if revision else None
        changed=[k for k in FIELDS if k in data and (not base or data[k]!=base.get(k))]
        conflicts=[k for k in changed if not base or current[k]!=base.get(k) and current[k]!=data[k]]
        # Status and progress are a single workflow unit.
        if base and any(k in changed for k in ('status','progress')) and any(current[k]!=base.get(k) for k in ('status','progress')):
            conflicts=list(set(conflicts+['status','progress']))
        if not data.get('merge') or conflicts or not base:
            return dict(error='This task changed. Review your changes against the current version.',current=task.to_dict(),base=base,conflicts=conflicts,safe_fields=[k for k in changed if k not in conflicts]),409
        data={k:v for k,v in data.items() if k in changed or k in ('version','merge')}
    snapshot(task)
    updates = {}
    if 'estimated_duration' in data:
        from ..services.planning import duration
        value=duration(data['estimated_duration'])
        if value!=(task.plan.duration if task.plan else 1):
            set_duration(task,value);task.version+=1
            record(task.project,'TASK_EDITED','task',task.id,title=task.title,fields=['estimated_duration'])
    if 'title' in data: updates['title'] = field(data, 'title', 2, 180)
    if 'description' in data: updates['description'] = text(data, 'description')
    if 'priority' in data:
        if data['priority'] not in PRIORITIES: abort(400, description='Invalid task priority.')
        updates['priority'] = data['priority']
    if 'assigned_to' in data: updates['assigned_to'] = assignee(data['assigned_to'], task.project.team_id)
    if 'deadline' in data: updates['deadline'] = deadline(data['deadline'])
    if 'status' in data or 'progress' in data:
        value = data.get('progress', task.progress)
        next_status = data.get('status', task.status)
        if task.status == 'DONE' and next_status != 'DONE' and 'progress' not in data:
            value = 0
        if task.status == 'DONE' and 'status' not in data and type(value) is int and value < 100:
            next_status = 'IN_PROGRESS'
        if task.status == 'DONE' and next_status != 'DONE' and value == 100:
            value = 0
        updates['status'], updates['progress'] = workflow(next_status, value)
    old = {key: getattr(task, key) for key in updates}
    changes = [key for key, value in updates.items() if old[key] != value]
    for key in changes: setattr(task, key, updates[key])
    if 'assigned_to' in changes:
        from ..models import User
        target = db.session.get(User, task.assigned_to) if task.assigned_to else None
        record(task.project, 'TASK_REASSIGNED', 'task', task.id, title=task.title, to=target.name if target else 'Unassigned')
    if 'status' in changes: record(task.project, 'TASK_STATUS_CHANGED', 'task', task.id, title=task.title, before=old['status'], after=task.status)
    if 'progress' in changes: record(task.project, 'TASK_PROGRESS_CHANGED', 'task', task.id, title=task.title, before=old['progress'], after=task.progress)
    management = [key for key in changes if key not in ('assigned_to','status','progress')]
    if management: record(task.project, 'TASK_EDITED', 'task', task.id, title=task.title, fields=management)
    db.session.commit()
    return dict(task=task.to_dict())

@bp.post('/tasks/<int:task_id>/comments')
@task_access
def comment(task, membership):
    item = Comment(task_id=task.id, user_id=current_user.id, content=field(payload(), 'content', 1, 5000))
    db.session.add(item)
    task.version += 1
    record(task.project, 'COMMENT_ADDED', 'task', task.id, title=task.title)
    db.session.commit()
    return dict(comment=item.to_dict()), 201

@bp.post('/tasks/<int:task_id>/attachments')
@task_access
def upload(task, membership):
    file = request.files.get('file')
    if not file or not file.filename:
        abort(400, description='Choose a file to upload.')
    filename = secure_filename(file.filename)
    if not filename or len(filename) > 200 or '.' not in filename or filename.rsplit('.', 1)[1].lower() not in ALLOWED_EXTENSIONS:
        abort(400, description='Upload PDF, images (PNG/JPG/WebP), text, CSV, JSON, Office documents, or ZIP files. Maximum filename length: 200.')
    content = file.stream.read(MAX_FILE_SIZE + 1)
    if not content: abort(400, description='Empty files cannot be uploaded.')
    if len(content) > MAX_FILE_SIZE: abort(413, description='Files must be 10 MB or smaller.')
    stored = secrets.token_hex(24)
    path = Path(current_app.config['UPLOAD_FOLDER']) / stored
    path.write_bytes(content)
    try:
        item = Attachment(task_id=task.id, uploaded_by=current_user.id, original_filename=filename, stored_filename=stored, mime_type=mimetypes.guess_type(filename)[0] or 'application/octet-stream', size=len(content))
        db.session.add(item)
        task.version += 1
        record(task.project, 'ATTACHMENT_UPLOADED', 'task', task.id, title=task.title, filename=filename)
        db.session.commit()
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return dict(attachment=item.to_dict()), 201

@bp.get('/tasks/<int:task_id>/attachments/<int:attachment_id>')
@task_access
def download(task, membership, attachment_id):
    item = db.session.get(Attachment, attachment_id)
    if not item or item.task_id != task.id: abort(404, description='Attachment not found.')
    path = Path(current_app.config['UPLOAD_FOLDER']) / item.stored_filename
    if not path.is_file(): abort(404, description='The attachment file is missing. Ask its uploader to upload it again.')
    response = send_file(path, as_attachment=True, download_name=item.original_filename, mimetype='application/octet-stream')
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Cache-Control'] = 'private, no-store'
    return response

@bp.delete('/tasks/<int:task_id>/attachments/<int:attachment_id>')
@task_access
def delete_attachment(task, membership, attachment_id):
    item = db.session.get(Attachment, attachment_id)
    if not item or item.task_id != task.id: abort(404, description='Attachment not found.')
    if membership.role != 'LEADER' and item.uploaded_by != current_user.id:
        abort(403, description='Only the uploader or a team leader can delete an attachment.')
    path = Path(current_app.config['UPLOAD_FOLDER']) / item.stored_filename
    record(task.project, 'ATTACHMENT_DELETED', 'task', task.id, title=task.title, filename=item.original_filename)
    task.version += 1
    db.session.delete(item)
    db.session.commit()
    path.unlink(missing_ok=True)
    return dict(message='Attachment deleted.')
