import pytest
from app import create_app
from app.extensions import db
from app.models import User, TeamMember

@pytest.fixture
def app():
    return create_app({'TESTING': True, 'SECRET_KEY': 'test-secret', 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})

@pytest.fixture
def client(app):
    return app.test_client()

def mutate(client, method, path, data=None):
    token = client.get('/api/auth/csrf').json['csrf_token']
    return getattr(client, method)(path, json=data, headers={'X-CSRF-Token': token})

def register(client, email='leader@example.com'):
    return mutate(client, 'post', '/api/auth/register', dict(name='Test Person', email=email, password='Password123', confirm_password='Password123'))

def create(client):
    return mutate(client, 'post', '/api/teams', {'name': 'Studio North'}).json['team']

def test_registration_and_password_hash(client, app):
    assert register(client).status_code == 201
    assert client.get('/api/auth/me').json['user']['email'] == 'leader@example.com'
    with app.app_context():
        user = db.session.scalar(db.select(User))
        assert user.password_hash != 'Password123'
        assert user.check_password('Password123')

def test_duplicate_registration_normalizes_email(client):
    register(client)
    assert register(client, 'LEADER@example.com').status_code == 409

@pytest.mark.parametrize('changes', [{'name': ''}, {'email': 'bad'}, {'password': 'short'}, {'confirm_password': 'different'}, {'password': 123}])
def test_registration_validation(client, changes):
    data = dict(name='A Person', email='a@example.com', password='Password123', confirm_password='Password123')
    data.update(changes)
    assert mutate(client, 'post', '/api/auth/register', data).status_code == 400

def test_login_logout_and_protection(client):
    assert client.get('/api/auth/me').status_code == 401
    assert mutate(client, 'post', '/api/teams', {'name': 'No access'}).status_code == 401
    register(client)
    assert mutate(client, 'post', '/api/auth/logout').status_code == 200
    assert client.get('/api/auth/me').status_code == 401
    assert mutate(client, 'post', '/api/auth/login', {'email': 'leader@example.com', 'password': 'wrong'}).status_code == 401
    assert mutate(client, 'post', '/api/auth/login', {'email': 'leader@example.com', 'password': 'Password123', 'remember': True}).status_code == 200

def test_creation_and_multiple_teams(client, app):
    register(client)
    team = create(client)
    assert team['role'] == 'LEADER'
    assert team['team_code'].startswith('TF-') and len(team['team_code']) == 9
    assert create(client)['team_code'] != team['team_code']
    assert len(client.get('/api/auth/me').json['teams']) == 2
    with app.app_context():
        assert db.session.scalar(db.select(TeamMember)).role == 'LEADER'

def test_join_roles_and_duplicate_membership(client, app):
    register(client)
    team = create(client)
    member = app.test_client()
    register(member, 'member@example.com')
    assert mutate(member, 'post', '/api/teams/join', {'team_code': 'TF-NOPE'}).status_code == 404
    assert member.get(f"/api/teams/{team['id']}").status_code == 403
    joined = mutate(member, 'post', '/api/teams/join', {'team_code': team['team_code'].lower()})
    assert joined.status_code == 201 and joined.json['team']['role'] == 'MEMBER'
    assert 'team_code' not in joined.json['team']
    assert mutate(member, 'post', '/api/teams/join', {'team_code': team['team_code']}).status_code == 409
    assert len(client.get(f"/api/teams/{team['id']}").json['members']) == 2
    member_id = member.get('/api/auth/me').json['user']['id']
    leader_id = client.get('/api/auth/me').json['user']['id']
    assert mutate(member, 'patch', f"/api/teams/{team['id']}", {'name': 'Hijack'}).status_code == 403
    assert mutate(member, 'delete', f"/api/teams/{team['id']}/members/{leader_id}").status_code == 403
    assert mutate(client, 'delete', f"/api/teams/{team['id']}/members/{leader_id}").status_code == 400
    assert mutate(client, 'patch', f"/api/teams/{team['id']}", {'name': 'New Name'}).status_code == 200
    assert client.get(f"/api/teams/{team['id']}").json['team']['name'] == 'New Name'
    assert mutate(client, 'delete', f"/api/teams/{team['id']}/members/{member_id}").status_code == 200
    assert member.get(f"/api/teams/{team['id']}").status_code == 403

def test_leave_and_profile(client, app):
    register(client)
    team = create(client)
    assert mutate(client, 'post', f"/api/teams/{team['id']}/leave").status_code == 400
    member = app.test_client(); register(member, 'member@example.com')
    mutate(member, 'post', '/api/teams/join', {'team_code': team['team_code']})
    assert mutate(member, 'post', f"/api/teams/{team['id']}/leave").status_code == 200
    assert member.get('/api/auth/me').json['teams'] == []
    assert mutate(client, 'patch', '/api/users/me', {'name': 'Updated Person'}).status_code == 200
    assert client.get('/api/auth/me').json['user']['name'] == 'Updated Person'

def test_csrf_and_invalid_json(client):
    assert client.post('/api/auth/register', json={}).status_code == 403
    token = client.get('/api/auth/csrf').json['csrf_token']
    assert client.post('/api/auth/login', json={}, headers={'X-CSRF-Token': token, 'Origin': 'https://evil.example'}).status_code == 403
    assert mutate(client, 'post', '/api/auth/register', []).status_code == 400

def test_sqlite_persistence_across_app_restart(tmp_path):
    config = {'TESTING': True, 'SECRET_KEY': 'persistent-test', 'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + str(tmp_path / 'persist.db')}
    first = create_app(config).test_client()
    register(first)
    team = create(first)
    mutate(first, 'patch', '/api/users/me', {'name': 'Persisted Name'})
    second = create_app(config).test_client()
    assert mutate(second, 'post', '/api/auth/login', {'email': 'leader@example.com', 'password': 'Password123'}).status_code == 200
    assert second.get('/api/auth/me').json['user']['name'] == 'Persisted Name'
    assert second.get(f"/api/teams/{team['id']}").json['team']['team_code'] == team['team_code']
