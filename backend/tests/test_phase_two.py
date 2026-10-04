import io
from datetime import date, timedelta
import pytest
from app import create_app
from app.extensions import db
from app.models import Activity, Task, Project
from test_phase_one import mutate as raw_mutate, register, create

def mutate(client, method, path, data=None):
    # Legacy behavioral cases now send the version required by the final API.
    if method=='patch' and path.startswith('/api/tasks/') and path.count('/')==3 and data is not None and 'version' not in data:
        response=client.get(path)
        if response.status_code==200: data={**data,'version':response.json['task']['version']}
    return raw_mutate(client,method,path,data)

@pytest.fixture
def world(tmp_path):
    app = create_app({'TESTING': True, 'SECRET_KEY': 'phase-two', 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:', 'UPLOAD_FOLDER': str(tmp_path / 'uploads')})
    leader, member, other, outsider = [app.test_client() for _ in range(4)]
    register(leader); team = create(leader)
    for index, client in enumerate((member, other, outsider)):
        register(client, f'person{index}@example.com')
        if client is not outsider:
            mutate(client, 'post', '/api/teams/join', {'team_code': team['team_code']})
    project = mutate(leader, 'post', f"/api/teams/{team['id']}/projects", {'name': 'Core Platform', 'description': 'A real project', 'deadline': '2026-12-01'}).json['project']
    mid = member.get('/api/auth/me').json['user']['id']
    oid = other.get('/api/auth/me').json['user']['id']
    return dict(app=app, leader=leader, member=member, other=other, outsider=outsider, team=team, project=project, mid=mid, oid=oid, uploads=tmp_path/'uploads')

def task(world, **changes):
    data = dict(title='Build the API', assigned_to=world['mid'], priority='HIGH', deadline='2026-10-01')
    data.update(changes)
    return mutate(world['leader'], 'post', f"/api/projects/{world['project']['id']}/tasks", data).json['task']

def test_project_management_and_access(world):
    w = world; pid = w['project']['id']; tid = w['team']['id']
    assert mutate(w['member'], 'post', f'/api/teams/{tid}/projects', {'name': 'Forbidden'}).status_code == 403
    assert mutate(w['leader'], 'patch', f'/api/projects/{pid}', {'name': 'Renamed', 'deadline': None}).status_code == 200
    assert w['member'].get(f'/api/projects/{pid}').json['project']['name'] == 'Renamed'
    for endpoint in ('', '/tasks', '/dashboard', '/activity'):
        assert w['outsider'].get(f'/api/projects/{pid}{endpoint}').status_code == 403
    assert mutate(w['outsider'], 'patch', f'/api/projects/{pid}', {'name': 'Hijack'}).status_code == 403
    assert len(w['leader'].get(f'/api/teams/{tid}/projects').json['projects']) == 1

@pytest.mark.parametrize('bad', [{'title': ''}, {'priority': 'EXTREME'}, {'status': 'MAYBE'}, {'progress': -1}, {'progress': 101}, {'progress': True}, {'assigned_to': 999}, {'assigned_to': True}, {'deadline': '2026-02-31'}, {'description': 42}])
def test_task_validation(world, bad):
    data = {'title': 'Valid task', **bad}
    assert mutate(world['leader'], 'post', f"/api/projects/{world['project']['id']}/tasks", data).status_code == 400

def test_task_permissions_and_version(world):
    w = world; item = task(w); path = f"/api/tasks/{item['id']}"
    assert item['version'] == 1 and item['assignee']['id'] == w['mid']
    assert mutate(w['member'], 'post', f"/api/projects/{w['project']['id']}/tasks", {'title': 'Forbidden'}).status_code == 403
    assert mutate(w['other'], 'patch', path, {'progress': 20}).status_code == 403
    assert mutate(w['member'], 'patch', path, {'title': 'Forbidden'}).status_code == 403
    assert w['outsider'].get(path).status_code == 403
    changed = mutate(w['member'], 'patch', path, {'status': 'IN_PROGRESS', 'progress': 60, 'version': 1})
    assert changed.status_code == 200 and changed.json['task']['version'] == 2
    assert mutate(w['leader'], 'patch', path, {'progress': 70, 'version': 1}).status_code == 409
    assert mutate(w['leader'], 'patch', path, {'assigned_to': w['oid']}).json['task']['assignee']['id'] == w['oid']
    assert mutate(w['member'], 'patch', path, {'progress': 75}).status_code == 403
    assert mutate(w['other'], 'patch', path, {'progress': 75}).status_code == 200
    # A no-op does not increase the version.
    before = w['leader'].get(path).json['task']['version']
    assert mutate(w['leader'], 'patch', path, {'progress': 75}).json['task']['version'] == before
    outsider_id = w['outsider'].get('/api/auth/me').json['user']['id']
    assert mutate(w['leader'], 'patch', path, {'assigned_to': outsider_id}).status_code == 400

def test_done_progress_rules(world):
    w = world; item = task(w); path = f"/api/tasks/{item['id']}"
    done = mutate(w['member'], 'patch', path, {'status': 'DONE'}).json['task']
    assert done['progress'] == 100
    reopened = mutate(w['member'], 'patch', path, {'status': 'REVIEW'}).json['task']
    assert reopened['progress'] == 0 and reopened['status'] == 'REVIEW'
    assert mutate(w['member'], 'patch', path, {'progress': 100}).json['task']['status'] == 'DONE'
    lower = mutate(w['member'], 'patch', path, {'progress': 45}).json['task']
    assert lower['status'] == 'IN_PROGRESS' and lower['progress'] == 45

def test_comments_activity_and_counts(world):
    w=world; item=task(w); path=f"/api/tasks/{item['id']}"
    assert mutate(w['other'], 'post', path+'/comments', {'content': 'A multiline\ncomment'}).status_code == 201
    assert mutate(w['member'], 'post', path+'/comments', {'content': '  '}).status_code == 400
    assert mutate(w['outsider'], 'post', path+'/comments', {'content': 'Forbidden'}).status_code == 403
    detail = w['leader'].get(path).json
    assert detail['comments'][0]['content'] == 'A multiline\ncomment'
    assert detail['task']['comment_count'] == 1 and detail['task']['version'] == 2
    types = [a['action_type'] for a in w['leader'].get(f"/api/projects/{w['project']['id']}/activity").json['activity']]
    assert {'PROJECT_CREATED','TASK_CREATED','TASK_ASSIGNED','COMMENT_ADDED'} <= set(types)

def upload(client, path, name='reference.txt', content=b'reference contents'):
    token = client.get('/api/auth/csrf').json['csrf_token']
    return client.post(path, data={'file': (io.BytesIO(content), name)}, content_type='multipart/form-data', headers={'X-CSRF-Token': token})

def test_attachment_upload_download_delete_and_security(world):
    w=world; item=task(w); path=f"/api/tasks/{item['id']}/attachments"
    assert upload(w['outsider'], path).status_code == 403
    assert upload(w['member'], path, 'evil.html').status_code == 400
    assert upload(w['member'], path, content=b'').status_code == 400
    assert upload(w['member'], path, content=b'x'*(10*1024*1024+1)).status_code == 413
    result = upload(w['member'], path, '../../reference.txt')
    assert result.status_code == 201
    attachment = result.json['attachment']; download_path = path+f"/{attachment['id']}"
    assert attachment['filename'] == 'reference.txt' and attachment['size'] == 18
    assert len(list(w['uploads'].iterdir())) == 1
    assert w['leader'].get(download_path).data == b'reference contents'
    assert 'attachment;' in w['leader'].get(download_path).headers['Content-Disposition']
    assert w['outsider'].get(download_path).status_code == 403
    assert mutate(w['other'], 'delete', download_path).status_code == 403
    assert mutate(w['member'], 'delete', download_path).status_code == 200
    assert not list(w['uploads'].iterdir())
    detail = w['leader'].get(f"/api/tasks/{item['id']}").json
    assert detail['task']['attachment_count'] == 0 and detail['task']['version'] == 3

def test_dashboard_workload_and_overdue(world):
    w = world
    task(w, status='DONE', progress=10)
    task(w, title='Active', status='IN_PROGRESS', progress=50, priority='URGENT')
    task(w, title='Due today', deadline='2026-10-04', progress=20, priority='HIGH')
    task(w, title='Unassigned', assigned_to=None, deadline=None, progress=30)
    stats = w['leader'].get(f"/api/projects/{w['project']['id']}/dashboard?today=2026-10-04").json['dashboard']
    assert stats['total'] == 4 and stats['progress'] == 50 and stats['overdue'] == 1
    assert stats['statuses'] == {'TODO':2, 'IN_PROGRESS':1, 'REVIEW':0, 'DONE':1}
    person = next(p for p in stats['members'] if p['user']['id'] == w['mid'])
    assert person['assigned'] == 3 and person['active'] == 2 and person['completed'] == 1 and person['overdue'] == 1
    assert person['progress'] == 56.7 and person['workload_score'] == 9 and person['workload'] == 'High'
    assert 'members' not in w['member'].get(f"/api/projects/{w['project']['id']}/dashboard").json['dashboard']
    assert w['leader'].get(f"/api/projects/{w['project']['id']}/dashboard?today=bad").status_code == 400

def test_departing_members_unassign_tasks(world):
    w=world; item=task(w)
    assert mutate(w['leader'], 'delete', f"/api/teams/{w['team']['id']}/members/{w['mid']}").status_code == 200
    detail = w['leader'].get(f"/api/tasks/{item['id']}").json
    assert detail['task']['assigned_to'] is None and detail['task']['version'] == 2
    assert any(a['action_type'] == 'TASK_REASSIGNED' for a in detail['activity'])

def test_additive_initialization_preserves_phase_one(tmp_path):
    config={'TESTING':True,'SECRET_KEY':'same','SQLALCHEMY_DATABASE_URI':'sqlite:///'+str(tmp_path/'existing.db'),'UPLOAD_FOLDER':str(tmp_path/'files')}
    app=create_app(config); client=app.test_client(); register(client); team=create(client)
    new=create_app(config); new_client=new.test_client()
    mutate(new_client,'post','/api/auth/login',{'email':'leader@example.com','password':'Password123'})
    assert new_client.get('/api/auth/me').json['teams'][0]['id'] == team['id']
    assert mutate(new_client,'post',f"/api/teams/{team['id']}/projects",{'name':'After restart'}).status_code == 201
