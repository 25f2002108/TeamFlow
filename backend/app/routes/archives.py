import io
import stat
import zipfile
from pathlib import PurePosixPath
from flask import Blueprint, abort, request, send_file
from flask_login import current_user
from werkzeug.utils import secure_filename
from ..extensions import db
from ..models import WorkspaceNode, WorkspaceAsset
from ..services.project_service import project_access, record
from ..services.workspace_service import name, content, effective

bp=Blueprint('archives',__name__,url_prefix='/api')
MAX_ZIP=10*1024*1024
MAX_TOTAL=25*1024*1024
MAX_NODES=1000

def full_project(project,membership):
    if membership.role=='LEADER': return
    if not project.nodes or any(effective(n)!='FULL_ACCESS' for n in project.nodes):
        abort(403,description='Full access to the entire workspace is required.')

def safe_path(value, allow_dot=False):
    if allow_dot and value=='.': return '.'
    if not isinstance(value,str) or not value or '\\' in value or value.startswith('/') or ':' in value or '\x00' in value:
        abort(400,description='Use a relative project path with forward slashes.')
    parts=value.rstrip('/').split('/')
    if len(parts)>25 or len(value)>500: abort(400,description='Project path is too deep or long.')
    for part in parts:
        if name(part)!=part: abort(400,description='Paths may not contain padded names.')
    return '/'.join(parts)

@bp.post('/projects/<int:project_id>/workspace/import')
@project_access()
def import_zip(project,membership):
    full_project(project,membership)
    if project.nodes: abort(409,description='Import is available only for an empty workspace. Create another project to import this ZIP.')
    upload=request.files.get('file')
    if not upload or not upload.filename.lower().endswith('.zip'): abort(400,description='Choose a project ZIP file.')
    raw=upload.stream.read(MAX_ZIP+1)
    if len(raw)>MAX_ZIP: abort(413,description='Project ZIP must be at most 10 MB.')
    staged={}; total=0
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            if len(archive.infolist())>MAX_NODES: abort(400,description='A project ZIP may contain at most 1,000 entries.')
            for entry in archive.infolist():
                path=safe_path(entry.orig_filename); key=path.casefold()
                mode=entry.external_attr>>16
                if stat.S_IFMT(mode) not in (0,stat.S_IFREG,stat.S_IFDIR) or entry.flag_bits & 1:
                    abort(400,description='Links, special files and encrypted ZIP entries are not supported.')
                if key in staged: abort(400,description='Duplicate archive paths are not allowed.')
                total+=entry.file_size
                if total>MAX_TOTAL or entry.file_size>512*1024: abort(413,description='Maximum extracted size is 25 MB; each text file must be at most 512 KiB.')
                if entry.file_size>max(1,entry.compress_size)*200: abort(400,description='Archive compression ratio exceeds the safety limit.')
                raw_value=b'' if entry.is_dir() else archive.read(entry)
                try:
                    value=raw_value.decode('utf-8-sig')
                    if '\x00' in value: value=raw_value
                except UnicodeError: value=raw_value
                if isinstance(value,str) and not entry.is_dir(): content(value)
                staged[key]=(path,'folder' if entry.is_dir() else 'file',value)
    except (zipfile.BadZipFile,UnicodeError,RuntimeError,NotImplementedError):
        abort(400,description='Import a valid, unencrypted project ZIP.')
    if not staged: abort(400,description='The archive is empty.')
    for path,kind,value in list(staged.values()):
        parts=path.split('/')
        for depth in range(1,len(parts)):
            parent='/'.join(parts[:depth]); key=parent.casefold()
            if key in staged and staged[key][1]!='folder': abort(400,description='A file conflicts with a folder path.')
            staged.setdefault(key,(parent,'folder',''))
    if len(staged)>MAX_NODES: abort(400,description='The expanded tree exceeds 1,000 nodes.')
    created={}
    for key,(path,kind,value) in sorted(staged.items(),key=lambda pair:pair[1][0].count('/')):
        parent=created.get(path.rpartition('/')[0].casefold())
        node=WorkspaceNode(project_id=project.id,parent_id=parent.id if parent else None,parent_scope=parent.id if parent else 0,name=path.split('/')[-1],name_key=path.split('/')[-1].casefold(),kind=kind,content=value if isinstance(value,str) else '',created_by=current_user.id)
        db.session.add(node);db.session.flush();created[key]=node
        if isinstance(value,bytes): db.session.add(WorkspaceAsset(node_id=node.id,data=value))
    record(project,'WORKSPACE_IMPORTED','project',project.id,title=project.name,files=sum(n.kind=='file' for n in created.values()))
    db.session.commit()
    return dict(message='Project imported.',nodes=len(created),files=sum(n.kind=='file' for n in created.values())),201

@bp.post('/projects/<int:project_id>/workspace/export')
@project_access()
def export_zip(project,membership):
    full_project(project,membership)
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
        for node in sorted(project.nodes,key=lambda n:n.path):
            path=safe_path(node.path)
            archive.writestr(path+'/' if node.kind=='folder' else path,'' if node.kind=='folder' else node.asset.data if node.asset else node.content)
    record(project,'WORKSPACE_EXPORTED','project',project.id,title=project.name);db.session.commit()
    buffer.seek(0)
    return send_file(buffer,mimetype='application/zip',as_attachment=True,download_name=(secure_filename(project.name) or 'TeamFlow-project')+'.zip',max_age=0)
