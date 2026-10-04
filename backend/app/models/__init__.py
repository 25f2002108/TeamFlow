from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from ..extensions import db

def now():
    return datetime.now(timezone.utc)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now, nullable=False)
    memberships = db.relationship('TeamMember', back_populates='user', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return dict(id=self.id, name=self.name, email=self.email)

class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    team_code = db.Column(db.String(12), unique=True, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now, nullable=False)
    memberships = db.relationship('TeamMember', back_populates='team', cascade='all, delete-orphan')

    def to_dict(self, role):
        data = dict(id=self.id, name=self.name, role=role, created_at=self.created_at.isoformat()+'Z', member_count=len(self.memberships))
        if role == 'LEADER':
            data['team_code'] = self.team_code
        return data

class TeamMember(db.Model):
    __table_args__ = (db.UniqueConstraint('user_id', 'team_id'), db.CheckConstraint("role IN ('LEADER', 'MEMBER')"))
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    role = db.Column(db.String(10), nullable=False)
    joined_at = db.Column(db.DateTime, default=now, nullable=False)
    user = db.relationship('User', back_populates='memberships')
    team = db.relationship('Team', back_populates='memberships')

from .project import Project, Task, Comment, Attachment, Activity
from .workspace import WorkspaceNode, WorkspaceAsset, FilePermission, TaskFile, CodeComment, Notification
from .planning import TaskPlan, Dependency, TaskRevision, DevelopmentConfig, Execution
