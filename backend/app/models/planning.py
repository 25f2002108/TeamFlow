from ..extensions import db
from . import now
from .project import timestamp


class TaskPlan(db.Model):
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), primary_key=True)
    duration = db.Column(db.Float, nullable=False, default=1)
    task = db.relationship('Task', backref=db.backref('plan', uselist=False, cascade='all, delete-orphan'))


class Dependency(db.Model):
    __table_args__ = (db.UniqueConstraint('task_id', 'depends_on_id'), db.CheckConstraint('task_id != depends_on_id'))
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False, index=True)
    depends_on_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    task = db.relationship('Task', foreign_keys=[task_id], backref=db.backref('dependencies', cascade='all, delete-orphan'))
    prerequisite = db.relationship('Task', foreign_keys=[depends_on_id], backref=db.backref('dependents', cascade='all, delete-orphan'))


class TaskRevision(db.Model):
    __table_args__ = (db.UniqueConstraint('task_id', 'version'),)
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    version = db.Column(db.Integer, nullable=False)
    fields = db.Column(db.JSON, nullable=False)
    task = db.relationship('Task', backref=db.backref('revisions', cascade='all, delete-orphan'))


class DevelopmentConfig(db.Model):
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), primary_key=True)
    run_command = db.Column(db.String(500), default='', nullable=False)
    test_command = db.Column(db.String(500), default='', nullable=False)
    working_directory = db.Column(db.String(500), default='.', nullable=False)
    allow_edit_execution = db.Column(db.Boolean, default=False, nullable=False)
    project = db.relationship('Project', backref=db.backref('development', uselist=False, cascade='all, delete-orphan'))

    def to_dict(self):
        return {key: getattr(self, key) for key in ('run_command','test_command','working_directory','allow_edit_execution')}


class Execution(db.Model):
    id = db.Column(db.String(32), primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    kind = db.Column(db.String(12), nullable=False)
    command = db.Column(db.String(500), nullable=False)
    working_directory = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(20), default='running', nullable=False)
    exit_code = db.Column(db.Integer)
    output = db.Column(db.Text, default='', nullable=False)
    fingerprint = db.Column(db.String(64), nullable=False)
    started_at = db.Column(db.DateTime, default=now, nullable=False)
    finished_at = db.Column(db.DateTime)
    project = db.relationship('Project', backref=db.backref('executions', cascade='all, delete-orphan'))

    def to_dict(self):
        return dict(id=self.id, project_id=self.project_id, user_id=self.user_id, kind=self.kind, command=self.command, working_directory=self.working_directory, status=self.status, exit_code=self.exit_code, output=self.output, fingerprint=self.fingerprint, started_at=timestamp(self.started_at), finished_at=timestamp(self.finished_at))
