from flask import Blueprint, abort, request
from flask_login import current_user
from ..extensions import db
from ..models import Task, Comment, CodeComment
from ..models.planning import Dependency
from ..services.project_service import task_access, project_access, record
from ..services.planning import graph, snapshot
from ..services.workspace_service import effective
from ..utils import payload

bp=Blueprint('planning',__name__,url_prefix='/api')

@bp.post('/tasks/<int:task_id>/dependencies')
@task_access
def add(task,membership):
    if membership.role!='LEADER': abort(403)
    target=payload().get('depends_on_id')
    other=db.session.get(Task,target) if type(target) is int else None
    if not other or other.project_id!=task.project_id: abort(400,description='Choose a task in this project.')
    if target==task.id: abort(400,description='A task cannot depend on itself.')
    if any(d.depends_on_id==target for d in task.dependencies): abort(409,description='Dependency already exists.')
    # An edge task -> prerequisite is invalid if prerequisite can already reach task.
    pending=[other]; seen=set()
    while pending:
        node=pending.pop()
        if node.id==task.id: abort(409,description='This dependency would create a cycle.')
        if node.id in seen: continue
        seen.add(node.id);pending.extend(d.prerequisite for d in node.dependencies)
    snapshot(task)
    db.session.add(Dependency(task_id=task.id,depends_on_id=target));task.version+=1
    record(task.project,'DEPENDENCY_ADDED','task',task.id,title=task.title)
    db.session.commit()
    return dict(task=task.to_dict()),201

@bp.delete('/tasks/<int:task_id>/dependencies/<int:target>')
@task_access
def remove(task,membership,target):
    if membership.role!='LEADER': abort(403)
    item=next((d for d in task.dependencies if d.depends_on_id==target),None)
    if not item: abort(404)
    snapshot(task);db.session.delete(item);task.version+=1
    record(task.project,'DEPENDENCY_REMOVED','task',task.id,title=task.title);db.session.commit()
    return dict(message='Dependency removed.')

@bp.get('/projects/<int:project_id>/search')
@project_access()
def search(project,membership):
    q=request.args.get('q','').strip().casefold()[:120]
    if len(q)<2: return dict(results=[])
    results=[]
    for t in project.tasks:
        for c in t.comments:
            if q in c.content.casefold(): results.append(dict(type='COMMENT',label=f'{t.title}: {c.content[:160]}',task_id=t.id))
    for node in project.nodes:
        if effective(node)=='NO_ACCESS': continue
        for c in node.comments:
            if q in c.content.casefold(): results.append(dict(type='CODE COMMENT',label=f'{node.path}: {c.content[:160]}',node_id=node.id,task_id=c.task_id))
    return dict(results=results[:30])
