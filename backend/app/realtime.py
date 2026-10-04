"""Authenticated rooms, permission-filtered presence, and small invalidation events.

Single-process development presence. Content always travels through authorized APIs.
"""
import secrets
import time
from flask import current_app, request, session, g
from flask_login import current_user
from flask_socketio import join_room, leave_room
from werkzeug.exceptions import HTTPException
from .extensions import socketio, db
from .models import Project, WorkspaceNode, TeamMember, User
from .services.workspace_service import effective

def connections(): return current_app.extensions['teamflow_presence']
def membership(uid, tid): return db.session.scalar(db.select(TeamMember).filter_by(user_id=uid,team_id=tid))

def snapshots():
    peers=list(connections().items())
    for sid, viewer in peers:
        if not viewer.get('team_id'): continue
        if not membership(viewer['uid'],viewer['team_id']): continue
        rows=[]; seen=set()
        for _, peer in peers:
            if peer.get('team_id') != viewer['team_id'] or not membership(peer['uid'],viewer['team_id']): continue
            key=(peer['uid'],peer.get('project_id'),peer.get('node_id'),peer.get('state'))
            if key in seen: continue
            seen.add(key); user=db.session.get(User,peer['uid'])
            row=dict(user=user.to_dict(), project_id=peer.get('project_id'), state='viewing', node_id=None, path=None, cursor=None)
            node=db.session.get(WorkspaceNode,peer.get('node_id')) if peer.get('node_id') else None
            if node and viewer.get('project_id') == peer.get('project_id') and effective(node,viewer['uid']) != 'NO_ACCESS':
                row.update(node_id=node.id,path=node.path,state=peer.get('state','viewing'),cursor=peer.get('cursor'))
            rows.append(row)
        socketio.emit('presence_snapshot',dict(users=rows),to=sid)

def reconcile():
    for sid, peer in list(connections().items()):
        tid=peer.get('team_id'); pid=peer.get('project_id'); nid=peer.get('node_id')
        if tid and not membership(peer['uid'],tid):
            if pid: socketio.server.leave_room(sid,f'project:{pid}',namespace='/')
            socketio.server.leave_room(sid,f'team:{tid}',namespace='/')
            if nid: socketio.server.leave_room(sid,f'file:{nid}',namespace='/')
            peer.update(team_id=None,project_id=None,node_id=None,state='viewing',cursor=None)
            socketio.emit('access_changed',{},to=sid)
        elif nid:
            node=db.session.get(WorkspaceNode,nid)
            permission=effective(node,peer['uid']) if node else 'NO_ACCESS'
            if permission == 'NO_ACCESS':
                socketio.server.leave_room(sid,f'file:{nid}',namespace='/'); peer.update(node_id=None,cursor=None,state='viewing')
            elif permission == 'VIEW': peer['state']='viewing'

from . import is_allowed_origin

@socketio.on('connect')
def connect(auth):
    token=session.get('csrf')
    if not current_user.is_authenticated or not isinstance(auth,dict) or not isinstance(auth.get('csrf'),str) or not token or not secrets.compare_digest(token,auth['csrf']): return False
    origin = request.headers.get('Origin')
    if origin and not is_allowed_origin(origin, current_app.config.get('FRONTEND_ORIGIN', ''), request.host_url): return False
    connections()[request.sid]=dict(uid=current_user.id,csrf=token,team_id=None,project_id=None,node_id=None,state='viewing',cursor=None,last=0)
    join_room(f'user:{current_user.id}')

@socketio.on('join_context')
def join_context(data):
    peer=connections().get(request.sid)
    if not peer or not current_user.is_authenticated or not isinstance(data,dict): return dict(ok=False,error='Sign in to collaborate.')
    tid=data.get('team_id'); pid=data.get('project_id'); nid=data.get('node_id')
    if type(tid) is not int or not membership(peer['uid'],tid): return dict(ok=False,error='Team access denied.')
    project=db.session.get(Project,pid) if type(pid) is int else None
    if pid is not None and (not project or project.team_id != tid): return dict(ok=False,error='Project access denied.')
    node=db.session.get(WorkspaceNode,nid) if type(nid) is int else None
    if nid is not None and (not node or node.project_id != pid or effective(node,peer['uid']) == 'NO_ACCESS'): return dict(ok=False,error='File access denied.')
    for kind,key in [('team','team_id'),('project','project_id'),('file','node_id')]:
        if peer.get(key): leave_room(f'{kind}:{peer[key]}')
    peer.update(team_id=tid,project_id=pid,node_id=nid,state='viewing',cursor=None)
    join_room(f'team:{tid}')
    if pid: join_room(f'project:{pid}')
    if nid: join_room(f'file:{nid}')
    snapshots(); return dict(ok=True)

@socketio.on('editing')
def editing(data):
    peer=connections().get(request.sid)
    if not peer or not isinstance(data,dict) or not peer.get('node_id'): return dict(ok=False)
    node=db.session.get(WorkspaceNode,peer['node_id'])
    permission=effective(node,peer['uid']) if node else 'NO_ACCESS'
    if permission == 'NO_ACCESS': reconcile(); snapshots(); return dict(ok=False)
    if time.monotonic()-peer['last'] < .15: return dict(ok=True)
    peer['last']=time.monotonic()
    peer['state']='editing' if data.get('editing') is True and permission in ('EDIT','FULL_ACCESS') else 'viewing'
    cursor=data.get('cursor')
    peer['cursor']=dict(line=cursor['line'],column=cursor['column']) if isinstance(cursor,dict) and type(cursor.get('line')) is int and type(cursor.get('column')) is int and 1 <= cursor['line'] <= len(node.content.split('\n')) and 1 <= cursor['column'] <= 100000 else None
    snapshots(); return dict(ok=True)

@socketio.on('disconnect')
def disconnect(reason=None):
    connections().pop(request.sid,None); snapshots()

def register_handlers():
    # Every factory instance has a fresh Socket.IO server (including isolated tests).
    for event, handler in [('connect',connect),('disconnect',disconnect),('join_context',join_context),('editing',editing)]:
        socketio.on_event(event,handler)

def publish_response(response):
    if not 200 <= response.status_code < 300 or request.method not in ('POST','PATCH','PUT','DELETE'): return response
    reconcile()
    for pid in db.session.info.pop('changed_projects',set()):
        # Per-connection delivery rechecks membership even after permission/member changes.
        project=db.session.get(Project,pid)
        if not project: continue
        for sid,peer in list(connections().items()):
            if peer.get('project_id') == pid and membership(peer['uid'],project.team_id):
                socketio.emit('project_changed',dict(project_id=pid,actor_id=getattr(current_user,'id',None)),to=sid)
    for uid in db.session.info.pop('notification_users',set()): socketio.emit('notifications_changed',{},to=f'user:{uid}')
    if request.path.startswith('/api/notifications'): socketio.emit('notifications_changed',{},to=f'user:{current_user.id}')
    if request.path.startswith('/api/teams') or request.path == '/api/users/me':
        for sid,peer in list(connections().items()): socketio.emit('team_changed',{},to=sid)
    if request.path == '/api/auth/logout':
        for sid,peer in list(connections().items()):
            if peer['uid'] == getattr(g,'socket_uid',None) and peer['csrf'] == getattr(g,'socket_csrf',None): socketio.server.disconnect(sid,namespace='/')
    snapshots()
    return response
