import io
import time
import zipfile
from datetime import date
import pytest
from app import create_app
from app.extensions import db
from app.models import Project
from app.services.planning import insights
from test_phase_one import mutate as raw_mutate, register, create
from test_phase_two import world, task, mutate
from test_phase_three import node, rule, connection

def archive(entries):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
        for path,value in entries.items(): z.writestr(path,value)
    raw=stream.getvalue()
    for path in entries:
        if '\\' in path: raw=raw.replace(path.replace('\\','/').encode(),path.encode())
    return io.BytesIO(raw)

def upload(w,entries,client=None):
    client=client or w['leader'];token=client.get('/api/auth/csrf').json['csrf_token']
    return client.post(f"/api/projects/{w['project']['id']}/workspace/import",data={'file':(archive(entries),'project.zip')},headers={'X-CSRF-Token':token})

def test_zip_roundtrip_latest_hierarchy_and_collision(world):
    w=world;pid=w['project']['id']
    assert upload(w,{'backend/auth.py':'value = 1\n','tests/':'','README.md':'Project','asset.bin':b'\xff\x00'}).status_code==201
    tree=w['leader'].get(f'/api/projects/{pid}/workspace').json['nodes']
    file=next(n for n in tree if n['path']=='backend/auth.py')
    assert mutate(w['leader'],'patch',f"/api/workspace/nodes/{file['id']}",{'content':'value = 2\n','version':1}).status_code==200
    result=mutate(w['leader'],'post',f'/api/projects/{pid}/workspace/export')
    with zipfile.ZipFile(io.BytesIO(result.data)) as z:
        assert z.read('backend/auth.py')==b'value = 2\n'
        assert z.read('asset.bin')==b'\xff\x00'
        assert 'tests/' in z.namelist()
    assert upload(w,{'other.py':'print(1)'}).status_code==409
    assert mutate(w['member'],'post',f'/api/projects/{pid}/workspace/export').status_code==403
    assert mutate(w['outsider'],'post',f'/api/projects/{pid}/workspace/export').status_code==403
    assert upload(w,{'a.py':'1'},w['outsider']).status_code==403

@pytest.mark.parametrize('path',['../outside.py','/absolute.py','C:/secret.py','a/../../secret.py','a\\b.py','CON.py','padded /a.py'])
def test_zip_rejects_unsafe_paths_atomically(world,path):
    w=world
    assert upload(w,{'valid.py':'1',path:'2'}).status_code==400
    assert not w['leader'].get(f"/api/projects/{w['project']['id']}/workspace").json['nodes']

def test_zip_invalid_binary_duplicate_and_size(world):
    w=world;client=w['leader'];path=f"/api/projects/{w['project']['id']}/workspace/import";token=client.get('/api/auth/csrf').json['csrf_token']
    assert client.post(path,data={'file':(io.BytesIO(b'invalid'),'bad.zip')},headers={'X-CSRF-Token':token}).status_code==400
    assert upload(w,{'a.py':'x','A.py':'y'}).status_code==400
    assert upload(w,{'a.py':'x'*600000}).status_code==413
    assert not client.get(f"/api/projects/{w['project']['id']}/workspace").json['nodes']

def test_task_required_version_safe_merge_same_field_resolution(world):
    w=world;t=task(w);path=f"/api/tasks/{t['id']}"
    assert raw_mutate(w['leader'],'patch',path,{'priority':'LOW'}).status_code==400
    first=mutate(w['leader'],'patch',path,{'priority':'LOW','version':1});assert first.status_code==200
    conflict=mutate(w['leader'],'patch',path,{'deadline':'2026-12-12','version':1})
    assert conflict.status_code==409 and conflict.json['conflicts']==[]
    merged=mutate(w['leader'],'patch',path,{'deadline':'2026-12-12','version':1,'merge':True})
    assert merged.status_code==200 and merged.json['task']['priority']=='LOW'
    conflict=mutate(w['leader'],'patch',path,{'priority':'URGENT','version':1,'merge':True})
    assert conflict.status_code==409 and 'priority' in conflict.json['conflicts']
    version=conflict.json['current']['version']
    assert mutate(w['leader'],'patch',path,{'priority':'URGENT','version':version}).status_code==200

def test_dependencies_cycle_blocking_duration_critical_path_and_health(world):
    w=world;a=task(w,title='API',estimated_duration=2);b=task(w,title='UI',estimated_duration=3);c=task(w,title='Release',estimated_duration=1)
    for target,source in [(b,a),(c,b)]: assert mutate(w['leader'],'post',f"/api/tasks/{target['id']}/dependencies",{'depends_on_id':source['id']}).status_code==201
    assert w['leader'].get(f"/api/tasks/{b['id']}").json['task']['blocked'] is True
    assert mutate(w['leader'],'post',f"/api/tasks/{a['id']}/dependencies",{'depends_on_id':c['id']}).status_code==409
    assert mutate(w['leader'],'post',f"/api/tasks/{a['id']}/dependencies",{'depends_on_id':a['id']}).status_code==400
    assert mutate(w['member'],'post',f"/api/tasks/{a['id']}/dependencies",{'depends_on_id':b['id']}).status_code==403
    assert mutate(w['leader'],'post',f"/api/tasks/{b['id']}/dependencies",{'depends_on_id':a['id']}).status_code==409
    dashboard=w['leader'].get(f"/api/projects/{w['project']['id']}/dashboard?today=2026-10-04").json['dashboard']
    assert dashboard['critical_path']['task_ids']==[a['id'],b['id'],c['id']]
    assert dashboard['critical_path']['remaining_days']==6
    assert dashboard['blocked']==2 and dashboard['health']['score']<85 and dashboard['risks']
    assert dashboard['members'][1]['workload']=='Overloaded'
    assert mutate(w['leader'],'patch',f"/api/tasks/{a['id']}",{'status':'DONE'}).status_code==200
    assert not w['leader'].get(f"/api/tasks/{b['id']}").json['task']['blocked']
    assert mutate(w['leader'],'delete',f"/api/tasks/{c['id']}/dependencies/{b['id']}").status_code==200

@pytest.fixture
def execution_world(tmp_path):
    app=create_app({'TESTING':True,'SECRET_KEY':'execution','SQLALCHEMY_DATABASE_URI':'sqlite:///'+str(tmp_path/'execution.db'),'UPLOAD_FOLDER':str(tmp_path/'uploads'),'EXECUTION_MODE':'trusted-local','EXECUTION_TIMEOUT':5})
    leader,member,outsider=[app.test_client() for _ in range(3)]
    register(leader);team=create(leader);register(member,'member@demo.test');register(outsider,'outsider@demo.test');mutate(member,'post','/api/teams/join',{'team_code':team['team_code']})
    project=mutate(leader,'post',f"/api/teams/{team['id']}/projects",{'name':'Executable demo'}).json['project']
    return dict(app=app,leader=leader,member=member,outsider=outsider,team=team,project=project,mid=member.get('/api/auth/me').json['user']['id'])

def finished(w,eid):
    for _ in range(150):
        response=w['leader'].get(f"/api/projects/{w['project']['id']}/executions/{eid}")
        if response.json['execution']['status']!='running': return response.json
        time.sleep(.05)
    pytest.fail('Process did not finish within timeout.')

def test_real_execution_fail_fix_pass_export_and_authorization(execution_world):
    w=execution_world;pid=w['project']['id'];base=f'/api/projects/{pid}'
    assert upload(w,{'app.py':'print("actual output", flush=True)\n','calc.py':'def add(a,b): return a-b\n','test_calc.py':'from calc import add\ndef test_add(): assert add(2,3)==5\n'}).status_code==201
    config=dict(run_command='python app.py',test_command='python -m pytest -q',working_directory='.',allow_edit_execution=True)
    assert mutate(w['leader'],'put',base+'/development',config).status_code==200
    assert mutate(w['outsider'],'post',base+'/executions',{'kind':'run'}).status_code==403
    assert mutate(w['member'],'post',base+'/executions',{'kind':'run'}).status_code==403
    assert mutate(w['outsider'],'put',base+'/development',config).status_code==403
    tree=w['leader'].get(base+'/workspace').json['nodes']
    for item in tree: assert rule(w,item['id'],'EDIT').status_code==200
    leader_socket=connection(w,w['leader']);leader_socket.emit('join_context',{'team_id':w['team']['id'],'project_id':pid},callback=True)
    started=mutate(w['member'],'post',base+'/executions',{'kind':'test'});assert started.status_code==202
    failed=finished(w,started.json['execution']['id']);assert failed['execution']['status']=='failed',failed
    assert '1 failed' in failed['execution']['output'],failed['execution']['output']
    assert any(e['name']=='execution_update' for e in leader_socket.get_received())
    file=next(t for t in tree if t['name']=='calc.py')
    assert mutate(w['member'],'patch',f"/api/workspace/nodes/{file['id']}",{'content':'def add(a,b): return a+b\n','version':1}).status_code==200
    assert w['leader'].get(base+'/executions/'+started.json['execution']['id']).json['stale']
    passed=mutate(w['member'],'post',base+'/executions',{'kind':'test'});result=finished(w,passed.json['execution']['id']);assert result['execution']['status']=='passed',result
    assert '1 passed' in result['execution']['output']
    ran=mutate(w['leader'],'post',base+'/executions',{'kind':'run'});result=finished(w,ran.json['execution']['id']);assert 'actual output' in result['execution']['output'] and result['execution']['exit_code']==0
    assert w['outsider'].get(base+'/executions/'+ran.json['execution']['id']).status_code==403
    zipdata=mutate(w['leader'],'post',base+'/workspace/export').data
    with zipfile.ZipFile(io.BytesIO(zipdata)) as z: assert b'a+b' in z.read('calc.py')
    leader_socket.disconnect()

def test_execution_stop_paths_limits_and_environment(execution_world):
    w=execution_world;pid=w['project']['id'];base=f'/api/projects/{pid}'
    node(w,name='wait.py',content='import time\nprint("started", flush=True)\ntime.sleep(30)\n')
    for command in ('python ../secret.py','python /secret.py','python -c "print(1)"','python a.py && whoami','cmd /c dir'):
        assert mutate(w['leader'],'post',base+'/executions',{'kind':'terminal','command':command}).status_code==400
    assert mutate(w['leader'],'put',base+'/development',{'working_directory':'../outside'}).status_code==400
    assert mutate(w['leader'],'post','/api/projects/99999/executions',{'kind':'run'}).status_code==404
    started=mutate(w['leader'],'post',base+'/executions',{'kind':'terminal','command':'python wait.py'});assert started.status_code==202
    assert mutate(w['leader'],'post',base+'/executions',{'kind':'terminal','command':'python wait.py'}).status_code==409
    eid=started.json['execution']['id'];assert mutate(w['leader'],'post',base+f'/executions/{eid}/stop').status_code==200
    assert finished(w,eid)['execution']['status']=='stopped'
    node(w,name='guard.py',content='import os\nassert "SECRET_KEY" not in os.environ\nopen("C:/Users/ASUS/Desktop/TeamFlow/backend/instance/teamflow.db", "rb")\n')
    result=mutate(w['leader'],'post',base+'/executions',{'kind':'terminal','command':'python guard.py'})
    result=finished(w,result.json['execution']['id']);assert result['execution']['status']=='failed' and 'outside its project' in result['execution']['output']
