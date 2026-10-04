import atexit
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from flask import abort, current_app
from flask_login import current_user
from ..extensions import db, socketio
from ..models import Project, TeamMember, Activity, now
from ..models.planning import Execution
from .workspace_service import effective

processes={}; lock=threading.Lock()

def fingerprint(project):
    return hashlib.sha256(json.dumps([(n.id,n.path,n.version) for n in sorted(project.nodes,key=lambda n:n.id)]).encode()).hexdigest()

def permitted(project,membership,uid=None):
    uid=uid or current_user.id
    if membership.role=='LEADER': return True
    permissions=[effective(n,uid) for n in project.nodes]
    if not permissions or any(p in ('NO_ACCESS','VIEW') for p in permissions): return False
    return all(p=='FULL_ACCESS' for p in permissions) or bool(project.development and project.development.allow_edit_execution)

def authorize(project,membership):
    if not permitted(project,membership): abort(403,description='Execution requires full workspace access, or EDIT on every file with leader approval.')

def command_args(command):
    if not isinstance(command,str) or not command.strip() or len(command)>500: abort(400,description='Configure a Run or Test command first.')
    if any(c in command for c in ('\n','\r','|','&',';','>','<','`','$')): abort(400,description='Shell expressions and command chaining are not supported.')
    try: args=shlex.split(command,posix=True)
    except ValueError: abort(400,description='Invalid command quoting.')
    if not args or args[0] not in ('python','python3'): abort(400,description='Guarded local execution supports Python scripts, python -m pytest, and python -m unittest. npm/Node and shell commands require a separate sandbox and are not supported.')
    args=args[1:]
    if not args: abort(400,description='Choose a Python script or test module; interactive shells are not supported.')
    if args[0]=='-m':
        if len(args)<2 or args[1] not in ('pytest','unittest'): abort(400,description='Only pytest and unittest modules are supported.')
    elif args[0].startswith('-') or not args[0].endswith('.py'): abort(400,description='Choose a project .py script.')
    for arg in args:
        if '\\' in arg or ':' in arg or arg.startswith('/') or '..' in arg.split('/'):
            abort(400,description='Command arguments must stay inside the project.')
    return args

def stop_process(entry):
    entry['stopped']=True
    process=entry.get('process')
    if process and process.poll() is None:
        process.terminate()
        try: process.wait(timeout=3)
        except subprocess.TimeoutExpired: process.kill()

def cleanup_all():
    for entry in list(processes.values()): stop_process(entry)
atexit.register(cleanup_all)

def emit_current(app,item):
    # Send only to currently authorized project viewers, never a global output room.
    from ..realtime import membership
    for sid,peer in list(app.extensions['teamflow_presence'].items()):
        if peer.get('project_id')!=item.project_id: continue
        member=membership(peer['uid'],item.project.team_id)
        if member and permitted(item.project,member,peer['uid']): socketio.emit('execution_update',item.to_dict(),to=sid)

def run(app,eid,files,args,cwd_text):
    entry=processes[eid]
    try:
        with tempfile.TemporaryDirectory(prefix='teamflow-execution-') as directory:
            root=Path(directory).resolve();project_root=root/'project';project_root.mkdir()
            for path,value,kind in files:
                target=(project_root/path).resolve()
                if project_root not in target.parents: raise ValueError('Invalid materialized path.')
                if kind=='folder': target.mkdir(parents=True,exist_ok=True)
                else: target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(value if isinstance(value,bytes) else value.encode('utf-8'))
            cwd=(project_root/cwd_text).resolve()
            if cwd!=project_root and project_root not in cwd.parents: raise ValueError('Invalid working directory.')
            if not cwd.is_dir(): raise ValueError('Working directory does not exist in saved files.')
            runner=root/'runner.py';shutil.copyfile(Path(__file__).with_name('execution_runner.py'),runner)
            env={k:os.environ[k] for k in ('SystemRoot','WINDIR') if k in os.environ}
            env.update(TEMP=directory,TMP=directory,HOME=directory,USERPROFILE=directory,PYTHONIOENCODING='utf-8',PYTHONUNBUFFERED='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
            if entry['stopped']: return
            process=subprocess.Popen([sys.executable,'-I','-u',str(runner),str(root),str(cwd),json.dumps(args)],cwd=cwd,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            entry['process']=process
            if entry['stopped']: stop_process(entry)
            timer=threading.Timer(app.config.get('EXECUTION_TIMEOUT',120),lambda:stop_process(entry));timer.daemon=True;timer.start()
            try:
                while True:
                    data=process.stdout.read1(4096)
                    if not data: break
                    entry['output']+=data.decode('utf-8',errors='replace')
                    if len(entry['output'])>200000:
                        entry['output']=entry['output'][:200000]+'\n[Output limit reached]\n';stop_process(entry)
                    with app.app_context():
                        item=db.session.get(Execution,eid);item.output=entry['output'];db.session.commit();emit_current(app,item)
                entry['exit_code']=process.wait()
            finally: timer.cancel()
    except Exception as error:
        entry['output']+=f'\nExecution failed: {error}\n';entry['exit_code']=-1
    finally:
        with app.app_context():
            item=db.session.get(Execution,eid)
            item.output=entry['output'];item.exit_code=entry.get('exit_code');item.status='stopped' if entry['stopped'] else 'passed' if item.exit_code==0 else 'failed';item.finished_at=now()
            db.session.add(Activity(team_id=item.project.team_id,project_id=item.project_id,user_id=item.user_id,action_type='TESTS_'+item.status.upper() if item.kind=='test' else 'EXECUTION_FINISHED',entity_type='project',entity_id=item.project_id,details=dict(title=item.project.name,status=item.status)))
            db.session.commit();emit_current(app,item)
            socketio.emit('project_changed',dict(project_id=item.project_id),to=f'project:{item.project_id}')
        processes.pop(eid,None)
