from ..extensions import db
from . import now, User

def timestamp(value):
    return value.isoformat() + 'Z' if value else None

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default='', nullable=False)
    deadline = db.Column(db.Date)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now, nullable=False)
    team = db.relationship('Team', backref=db.backref('projects', cascade='all, delete-orphan'))
    tasks = db.relationship('Task', back_populates='project', cascade='all, delete-orphan')

    def to_dict(self):
        return dict(id=self.id, team_id=self.team_id, name=self.name, description=self.description, deadline=self.deadline.isoformat() if self.deadline else None, created_by=self.created_by, created_at=timestamp(self.created_at), updated_at=timestamp(self.updated_at))

class Task(db.Model):
    __table_args__ = (db.CheckConstraint("status IN ('TODO','IN_PROGRESS','REVIEW','DONE')"), db.CheckConstraint("priority IN ('LOW','MEDIUM','HIGH','URGENT')"), db.CheckConstraint('progress BETWEEN 0 AND 100'), db.CheckConstraint("(status = 'DONE' AND progress = 100) OR (status != 'DONE' AND progress < 100)"))
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, default='', nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    priority = db.Column(db.String(10), default='MEDIUM', nullable=False)
    deadline = db.Column(db.Date)
    status = db.Column(db.String(20), default='TODO', nullable=False)
    progress = db.Column(db.Integer, default=0, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now, nullable=False)
    version = db.Column(db.Integer, default=1, nullable=False)
    __mapper_args__ = {'version_id_col': version}
    project = db.relationship('Project', back_populates='tasks')
    assignee = db.relationship('User', foreign_keys=[assigned_to], backref='assigned_tasks')
    comments = db.relationship('Comment', back_populates='task', cascade='all, delete-orphan', order_by='Comment.created_at')
    attachments = db.relationship('Attachment', back_populates='task', cascade='all, delete-orphan', order_by='Attachment.created_at')

    def to_dict(self):
        blockers=[d.depends_on_id for d in self.dependencies if d.prerequisite.status!='DONE']
        return dict(id=self.id, project_id=self.project_id, title=self.title, description=self.description, assigned_to=self.assigned_to, assignee=self.assignee.to_dict() if self.assignee else None, priority=self.priority, deadline=self.deadline.isoformat() if self.deadline else None, status=self.status, progress=self.progress, created_by=self.created_by, created_at=timestamp(self.created_at), updated_at=timestamp(self.updated_at), version=self.version, comment_count=len(self.comments), attachment_count=len(self.attachments),estimated_duration=self.plan.duration if self.plan else 1, duration_estimated=self.plan is not None,depends_on=[d.depends_on_id for d in self.dependencies],blocks=[d.task_id for d in self.dependents],blocked=self.status!='DONE' and bool(blockers),blocker_ids=blockers)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now, nullable=False)
    user = db.relationship('User', backref='comments')
    task = db.relationship('Task', back_populates='comments')

    def to_dict(self):
        return dict(id=self.id, task_id=self.task_id, content=self.content, author=self.user.to_dict(), created_at=timestamp(self.created_at))

class Attachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False, index=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(80), unique=True, nullable=False)
    mime_type = db.Column(db.String(120), nullable=False)
    size = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    user = db.relationship('User', backref='uploads')
    task = db.relationship('Task', back_populates='attachments')

    def to_dict(self):
        return dict(id=self.id, task_id=self.task_id, filename=self.original_filename, mime_type=self.mime_type, size=self.size, author=self.user.to_dict(), created_at=timestamp(self.created_at))

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action_type = db.Column(db.String(40), nullable=False)
    entity_type = db.Column(db.String(30), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False)
    details = db.Column(db.JSON, default=dict, nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    user = db.relationship('User', backref='activities')
    project = db.relationship('Project', backref=db.backref('activities', cascade='all, delete-orphan'))

    def to_dict(self):
        return dict(id=self.id, project_id=self.project_id, actor=self.user.to_dict(), action_type=self.action_type, entity_type=self.entity_type, entity_id=self.entity_id, details={k:v for k,v in self.details.items() if not k.startswith('_')}, created_at=timestamp(self.created_at))
