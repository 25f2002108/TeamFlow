import os
import secrets
import threading
from flask import Blueprint, abort, current_app
from flask_login import current_user
from ..extensions import db
from ..models.planning import DevelopmentConfig, Execution
from ..services.project_service import project_access, record
from ..services.execution_service import authorize, permitted, command_args, fingerprint, processes, lock, run, stop_process
from .archives import full_project, safe_path
from ..utils import payload
from ..services.workspace_service import effective

bp=Blueprint('execution',__name__,url_prefix='/api')

def config(project):
    return project.development or DevelopmentConfig(project=project,run_command='',test_command='',working_directory='.',allow_edit_execution=False)

@bp.get('/projects/<int:project_id>/development')
@project_access()
def get_config(project,membership):
    value=project.development.to_dict() if project.development else dict(run_command='',test_command='',working_directory='.',allow_edit_execution=False)
    full=membership.role=='LEADER' or bool(project.nodes) and all(effective(n)=='FULL_ACCESS' for n in project.nodes)
    can=permitted(project,membership)
    latest=db.session.scalar(db.select(Execution).filter_by(project_id=project.id,kind='test').order_by(Execution.started_at.desc())) if can else None
    paths={n.path for n in project.nodes}
    suggestions=dict(run_command='python app.py' if 'app.py' in paths else 'python main.py' if 'main.py' in paths else '',test_command='python -m pytest' if any(p.startswith('tests/') or p.startswith('test_') for p in paths) else '')
    return dict(config=value,can_manage=full,can_execute=can,enabled=current_app.config.get('EXECUTION_MODE',os.getenv('EXECUTION_MODE','disabled'))=='trusted-local',suggestions=suggestions,latest_test=latest.to_dict() if latest else None,fingerprint=fingerprint(project))

@bp.put('/projects/<int:project_id>/development')
@project_access()
def update_config(project,membership):
    full_project(project,membership);data=payload();item=config(project)
    for key in ('run_command','test_command'):
        value=data.get(key,'')
        if value: command_args(value)
        setattr(item,key,value)
    item.working_directory=safe_path(data.get('working_directory','.'),True)
    if type(data.get('allow_edit_execution',False)) is not bool: abort(400)
    item.allow_edit_execution=data.get('allow_edit_execution',False)
    db.session.add(item);record(project,'DEVELOPMENT_CONFIGURED','project',project.id,title=project.name);db.session.commit()
    return dict(config=item.to_dict())

@bp.post('/projects/<int:project_id>/executions')
@project_access()
def start(project,membership):
    authorize(project,membership)
    if current_app.config.get('EXECUTION_MODE',os.getenv('EXECUTION_MODE','disabled'))!='trusted-local': abort(503,description='Local execution is disabled. The server operator must enable EXECUTION_MODE=trusted-local for trusted demo code only.')
    data=payload();kind=data.get('kind')
    if kind not in ('run','test','terminal'): abort(400,description='Choose run, test, or terminal.')
    cfg=project.development
    command=data.get('command') if kind=='terminal' else getattr(cfg,kind+'_command','')
    args=command_args(command);cwd=cfg.working_directory if cfg else '.'
    if cwd!='.' and not any(n.path==cwd and n.kind=='folder' for n in project.nodes): abort(400,description='Working directory does not exist in the saved workspace.')
    if args[0]!='-m' and not any(n.path==('/'.join([cwd,args[0]]) if cwd!='.' else args[0]) and n.kind=='file' for n in project.nodes): abort(400,description='The script does not exist in the saved working directory.')
    app=current_app._get_current_object()
    with lock:
        if len(processes)>=4 or any(e['project_id']==project.id for e in processes.values()): abort(409,description='An execution is already running, or server capacity is full. Stop it before starting another.')
        eid=secrets.token_hex(16)
        item=Execution(id=eid,project_id=project.id,user_id=current_user.id,kind=kind,command=command,working_directory=cwd,fingerprint=fingerprint(project),output='')
        db.session.add(item);record(project,'EXECUTION_STARTED','project',project.id,title=project.name,kind=kind);db.session.commit()
        processes[eid]=dict(project_id=project.id,stopped=False,output='',process=None)
    files=[(n.path,n.asset.data if n.asset else n.content,n.kind) for n in project.nodes]
    threading.Thread(target=run,args=(app,eid,files,args,cwd),daemon=True).start()
    return dict(execution=item.to_dict()),202

@bp.get('/projects/<int:project_id>/executions')
@project_access()
def history(project,membership):
    authorize(project,membership)
    items=db.session.scalars(db.select(Execution).filter_by(project_id=project.id).order_by(Execution.started_at.desc()).limit(10)).all()
    return dict(executions=[i.to_dict() for i in items])

@bp.get('/projects/<int:project_id>/executions/<eid>')
@project_access()
def detail(project,membership,eid):
    authorize(project,membership);item=db.session.get(Execution,eid)
    if not item or item.project_id!=project.id: abort(404)
    return dict(execution=item.to_dict(),stale=item.fingerprint!=fingerprint(project))

@bp.post('/projects/<int:project_id>/executions/<eid>/stop')
@project_access()
def stop(project,membership,eid):
    authorize(project,membership);item=db.session.get(Execution,eid)
    if not item or item.project_id!=project.id: abort(404)
    if membership.role!='LEADER' and item.user_id!=current_user.id: abort(403,description='Only the starter or leader can stop this process.')
    entry=processes.get(eid)
    if entry: stop_process(entry)
    return dict(message='Stop requested.' if entry else 'Process has already ended.')
