import pytest
from app.extensions import socketio
from test_phase_two import world, task
from test_phase_one import mutate

def node(w, **changes):
    data=dict(name='auth.py',kind='file',content='def authenticate():\n    return True\n')
    data.update(changes)
    return mutate(w['leader'],'post',f"/api/projects/{w['project']['id']}/workspace",data)

def rule(w,nid,value,uid=None):
    return mutate(w['leader'],'put',f'/api/workspace/nodes/{nid}/permissions',{'permissions':[{'user_id':uid or w['mid'],'permission':value}]})

def test_nested_workspace_management_and_cleanup(world):
    w=world; folder=node(w,name='backend',kind='folder').json['node']; child=node(w,parent_id=folder['id']).json['node']; path=f"/api/workspace/nodes/{child['id']}"
    assert child['path']=='backend/auth.py'
    assert len(w['member'].get(f"/api/projects/{w['project']['id']}/workspace").json['nodes'])==2
    assert node(w,parent_id=folder['id']).status_code==409
    assert node(w,name='AUTH.py',parent_id=folder['id']).status_code==409
    assert mutate(w['leader'],'patch',f"/api/workspace/nodes/{folder['id']}",{'name':'server','version':1}).status_code==200
    assert w['leader'].get(path).json['node']['path']=='server/auth.py'
    assert mutate(w['leader'],'delete',f"/api/workspace/nodes/{folder['id']}").status_code==200
    assert w['leader'].get(path).status_code==404

@pytest.mark.parametrize('bad',['../evil.py','a/b.py','a\\b.py','..','.','bad\x00.py','file:code','file.',''])
def test_workspace_name_safety(world,bad):
    assert node(world,name=bad).status_code==400

def test_permission_inheritance_and_direct_api_enforcement(world):
    w=world; folder=node(w,name='src',kind='folder').json['node']; child=node(w,parent_id=folder['id']).json['node']; path=f"/api/workspace/nodes/{child['id']}"
    assert w['member'].get(path).json['node']['permission']=='VIEW'
    assert mutate(w['member'],'patch',path,{'content':'forbidden','version':1}).status_code==403
    assert mutate(w['member'],'post',f"/api/projects/{w['project']['id']}/workspace",{'name':'x.py','kind':'file'}).status_code==403
    assert rule(w,folder['id'],'EDIT').status_code==200
    changed=mutate(w['member'],'patch',path,{'content':'allowed\n','version':1})
    assert changed.status_code==200 and changed.json['node']['version']==2
    assert mutate(w['member'],'patch',path,{'name':'renamed.py','version':2}).status_code==403
    assert rule(w,child['id'],'FULL_ACCESS').status_code==200
    assert mutate(w['member'],'patch',path,{'name':'renamed.py','version':2}).status_code==200
    assert rule(w,folder['id'],'NO_ACCESS').status_code==200
    assert w['member'].get(path).status_code==403
    assert not w['member'].get(f"/api/projects/{w['project']['id']}/workspace").json['nodes']
    assert w['leader'].get(path).status_code==200
    assert rule(w,folder['id'],None).status_code==200
    assert w['member'].get(path).json['node']['permission']=='FULL_ACCESS'
    assert mutate(w['member'],'put',path+'/permissions',{'permissions':[]}).status_code==403
    assert w['outsider'].get(path).status_code==403

def test_full_access_creation_and_protected_descendant_delete(world):
    w=world; folder=node(w,name='src',kind='folder').json['node']; rule(w,folder['id'],'FULL_ACCESS')
    result=mutate(w['member'],'post',f"/api/projects/{w['project']['id']}/workspace",{'name':'member.js','kind':'file','parent_id':folder['id']})
    assert result.status_code==201
    nid=result.json['node']['id'];rule(w,nid,'VIEW')
    assert mutate(w['member'],'delete',f"/api/workspace/nodes/{folder['id']}").status_code==403
    assert mutate(w['leader'],'delete',f"/api/workspace/nodes/{folder['id']}").status_code==200

def test_file_stale_version_preserves_current_and_noop(world):
    w=world; item=node(w).json['node'];path=f"/api/workspace/nodes/{item['id']}"
    assert mutate(w['leader'],'patch',path,{'content':'new server\n','version':1}).json['node']['version']==2
    stale=mutate(w['leader'],'patch',path,{'content':'stale draft\n','version':1})
    assert stale.status_code==409 and stale.json['current']['content']=='new server\n'
    assert w['leader'].get(path).json['node']['content']=='new server\n'
    assert mutate(w['leader'],'patch',path,{'content':'new server\n','version':2}).json['node']['version']==2
    assert mutate(w['leader'],'patch',path,{'content':'missing version'}).status_code==400

def test_task_file_linking_comments_resolve_and_notifications(world):
    w=world; file=node(w).json['node'];item=task(w);nid=file['id'];tid=item['id'];path=f'/api/workspace/nodes/{nid}'
    assert mutate(w['leader'],'post',f'/api/tasks/{tid}/files',{'node_id':nid}).status_code==201
    assert mutate(w['member'],'post',f'/api/tasks/{tid}/files',{'node_id':nid}).status_code==403
    assert w['member'].get(f'/api/tasks/{tid}/files').json['files'][0]['id']==nid
    posted=mutate(w['member'],'post',path+'/comments',{'content':'Check this line\nPlease.','line_start':1,'line_end':2,'version':1,'task_id':tid})
    assert posted.status_code==201
    cid=posted.json['comment']['id']
    assert mutate(w['other'],'patch',f'/api/workspace/comments/{cid}',{'resolved':True}).status_code==403
    assert mutate(w['member'],'patch',f'/api/workspace/comments/{cid}',{'resolved':True}).json['comment']['resolved'] is True
    assert mutate(w['member'],'post',path+'/comments',{'content':'Invalid','line_start':999,'version':1}).status_code==400
    notifications=w['member'].get('/api/notifications').json
    assert notifications['unread']>=1
    notice=notifications['notifications'][0]
    assert mutate(w['other'],'patch',f"/api/notifications/{notice['id']}/read").status_code==404
    assert mutate(w['member'],'patch',f"/api/notifications/{notice['id']}/read").status_code==200
    assert mutate(w['member'],'post','/api/notifications/read-all').status_code==200
    assert w['member'].get('/api/notifications').json['unread']==0
    rule(w,nid,'NO_ACCESS')
    assert not w['member'].get(f'/api/tasks/{tid}/files').json['files']
    assert w['member'].get(path+'/permissions').status_code==403
    assert mutate(w['leader'],'delete',path).status_code==200
    assert not w['leader'].get(f'/api/tasks/{tid}/files').json['files']

def connection(w,client):
    csrf=client.get('/api/auth/csrf').json['csrf_token']
    return socketio.test_client(w['app'],flask_test_client=client,auth={'csrf':csrf})

def test_two_clients_socket_auth_presence_tasks_comments_and_revocation(world):
    w=world; pid=w['project']['id'];tid=w['team']['id'];context=dict(team_id=tid,project_id=pid)
    anonymous=socketio.test_client(w['app']);assert not anonymous.is_connected()
    wrong=socketio.test_client(w['app'],flask_test_client=w['member'],auth={'csrf':'bad'});assert not wrong.is_connected()
    leader=connection(w,w['leader']);member=connection(w,w['member']);outsider=connection(w,w['outsider'])
    assert outsider.emit('join_context',context,callback=True)['ok'] is False
    assert leader.emit('join_context',context,callback=True)['ok'] is True
    assert member.emit('join_context',context,callback=True)['ok'] is True
    events=leader.get_received();snap=[e for e in events if e['name']=='presence_snapshot'][-1]['args'][0]
    assert {u['user']['id'] for u in snap['users']}=={w['mid'],w['leader'].get('/api/auth/me').json['user']['id']}
    member.get_received(); item=task(w)
    received=member.get_received();assert any(e['name']=='project_changed' for e in received);assert any(e['name']=='notifications_changed' for e in received)
    leader.get_received(); mutate(w['member'],'patch',f"/api/tasks/{item['id']}",{'progress':80,'version':1})
    assert any(e['name']=='project_changed' for e in leader.get_received())
    assert w['leader'].get(f'/api/projects/{pid}/dashboard').json['dashboard']['progress']==80
    file=node(w).json['node'];nid=file['id'];rule(w,nid,'EDIT');member.get_received()
    assert member.emit('join_context',{**context,'node_id':nid},callback=True)['ok'] is True
    leader.get_received();member.emit('editing',{'editing':True,'cursor':{'line':1,'column':3}},callback=True)
    peer=[e for e in leader.get_received() if e['name']=='presence_snapshot'][-1]['args'][0]['users']
    assert any(p['user']['id']==w['mid'] and p['state']=='editing' for p in peer)
    leader.get_received()
    assert mutate(w['member'],'post',f'/api/workspace/nodes/{nid}/comments',{'content':'Live code review','line_start':1,'version':1}).status_code==201
    assert any(e['name']=='project_changed' for e in leader.get_received())
    assert mutate(w['member'],'patch',f'/api/workspace/nodes/{nid}',{'content':'shared save\n','version':1}).status_code==200
    assert any(e['name']=='project_changed' for e in leader.get_received())
    assert w['leader'].get(f'/api/workspace/nodes/{nid}').json['node']['content']=='shared save\n'
    member.disconnect()
    member=connection(w,w['member'])
    assert member.emit('join_context',{**context,'node_id':nid},callback=True)['ok'] is True
    rule(w,nid,'NO_ACCESS');assert member.emit('join_context',{**context,'node_id':nid},callback=True)['ok'] is False
    mutate(w['leader'],'delete',f'/api/teams/{tid}/members/{w["mid"]}')
    assert member.emit('join_context',context,callback=True)['ok'] is False
    member.get_received();node(w,name='private.py')
    assert not any(e['name']=='project_changed' for e in member.get_received())
    leader.disconnect();member.disconnect();outsider.disconnect()

def test_hidden_workspace_activity_and_cross_project_links(world):
    w=world;file=node(w).json['node'];rule(w,file['id'],'NO_ACCESS')
    feed=w['member'].get(f"/api/projects/{w['project']['id']}/activity").json['activity']
    assert not any(a['entity_type']=='node' for a in feed)
    assert all('_audience' not in a['details'] for a in w['leader'].get(f"/api/projects/{w['project']['id']}/activity").json['activity'])
    second=mutate(w['leader'],'post',f"/api/teams/{w['team']['id']}/projects",{'name':'Other project'}).json['project']
    other=mutate(w['leader'],'post',f"/api/projects/{second['id']}/workspace",{'name':'other.py','kind':'file'}).json['node']
    item=task(w)
    assert mutate(w['leader'],'post',f"/api/tasks/{item['id']}/files",{'node_id':other['id']}).status_code==400
    assert node(w,parent_id=other['id']).status_code==400
