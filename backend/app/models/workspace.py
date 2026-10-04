from ..extensions import db
from . import now
from .project import timestamp

class WorkspaceNode(db.Model):
    __table_args__ = (db.UniqueConstraint('project_id','parent_scope','name_key'), db.CheckConstraint("kind IN ('file','folder')"))
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('workspace_node.id'), index=True)
    parent_scope = db.Column(db.Integer, default=0, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    name_key = db.Column(db.String(120), nullable=False)
    kind = db.Column(db.String(10), nullable=False)
    content = db.Column(db.Text, default='', nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now, nullable=False)
    version = db.Column(db.Integer, default=1, nullable=False)
    __mapper_args__ = {'version_id_col': version}
    project = db.relationship('Project', backref=db.backref('nodes', cascade='all, delete-orphan'))
    parent = db.relationship('WorkspaceNode', remote_side=[id], back_populates='children')
    children = db.relationship('WorkspaceNode', back_populates='parent', cascade='all, delete-orphan')
    permissions = db.relationship('FilePermission', back_populates='node', cascade='all, delete-orphan')
    comments = db.relationship('CodeComment', back_populates='node', cascade='all, delete-orphan', order_by='CodeComment.id')
    links = db.relationship('TaskFile', back_populates='node', cascade='all, delete-orphan')

    @property
    def path(self):
        return f'{self.parent.path}/{self.name}' if self.parent else self.name

    def to_dict(self, permission, content=False):
        value = dict(id=self.id, project_id=self.project_id, parent_id=self.parent_id, name=self.name, kind=self.kind, path=self.path, permission=permission, version=self.version, created_by=self.created_by, created_at=timestamp(self.created_at), updated_at=timestamp(self.updated_at))
        value['binary'] = self.asset is not None
        if content and self.kind == 'file': value['content'] = self.content
        return value

class WorkspaceAsset(db.Model):
    node_id = db.Column(db.Integer, db.ForeignKey('workspace_node.id'), primary_key=True)
    data = db.Column(db.LargeBinary, nullable=False)
    node = db.relationship('WorkspaceNode', backref=db.backref('asset', uselist=False, cascade='all, delete-orphan'))

class FilePermission(db.Model):
    __table_args__ = (db.UniqueConstraint('node_id','user_id'), db.CheckConstraint("permission IN ('VIEW','EDIT','NO_ACCESS','FULL_ACCESS')"))
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    node_id = db.Column(db.Integer, db.ForeignKey('workspace_node.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    permission = db.Column(db.String(15), nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now, nullable=False)
    node = db.relationship('WorkspaceNode', back_populates='permissions')

class TaskFile(db.Model):
    __table_args__ = (db.UniqueConstraint('task_id','node_id'),)
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False, index=True)
    node_id = db.Column(db.Integer, db.ForeignKey('workspace_node.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    task = db.relationship('Task', backref=db.backref('file_links', cascade='all, delete-orphan'))
    node = db.relationship('WorkspaceNode', back_populates='links')

class CodeComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    node_id = db.Column(db.Integer, db.ForeignKey('workspace_node.id'), nullable=False, index=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    line_start = db.Column(db.Integer, nullable=False)
    line_end = db.Column(db.Integer, nullable=False)
    file_version = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    resolved = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now, nullable=False)
    node = db.relationship('WorkspaceNode', back_populates='comments')
    user = db.relationship('User')

    def to_dict(self):
        return dict(id=self.id, node_id=self.node_id, task_id=self.task_id, author=self.user.to_dict(), line_start=self.line_start, line_end=self.line_end, file_version=self.file_version, content=self.content, resolved=self.resolved, created_at=timestamp(self.created_at), updated_at=timestamp(self.updated_at))

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    kind = db.Column(db.String(40), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'))
    node_id = db.Column(db.Integer, db.ForeignKey('workspace_node.id', ondelete='SET NULL'))
    read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    project = db.relationship('Project')
    node = db.relationship('WorkspaceNode', backref=db.backref('notifications', passive_deletes=False))

    def to_dict(self):
        return dict(id=self.id, project_id=self.project_id, team_id=self.project.team_id, kind=self.kind, message=self.message, task_id=self.task_id, node_id=self.node_id, read=self.read, created_at=timestamp(self.created_at))
