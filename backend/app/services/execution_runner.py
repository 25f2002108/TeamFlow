"""Accidental-access guard for TRUSTED local Python projects, not a security sandbox.

Copied into each disposable execution directory. Never enable local execution for
untrusted users/code. CPython audit hooks are bypassable by malicious native code.
"""
import os
import sys
import runpy
import pathlib
import json

root=pathlib.Path(sys.argv[1]).resolve()
cwd=pathlib.Path(sys.argv[2]).resolve()
args=json.loads(sys.argv[3])
runtime=[pathlib.Path(sys.base_prefix).resolve(),pathlib.Path(sys.prefix).resolve()]
def inside(path,base):
    return path==base or base in path.parents
def pathcheck(value,write=False):
    if isinstance(value,int) or value is None: return
    if os.fsdecode(value).lower()==os.devnull.lower(): return
    p=pathlib.Path(os.fsdecode(value)).resolve()
    if p==pathlib.Path(os.devnull).resolve(): return
    if inside(p,root): return
    if not write and any(inside(p,r) for r in runtime): return
    raise PermissionError('TeamFlow execution cannot access paths outside its project/runtime.')
def guard(event,values):
    if event=='open':
        mode=values[1];flags=values[2]
        write=bool(isinstance(mode,str) and any(x in mode for x in 'wax+')) or bool(isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))
        pathcheck(values[0],write)
    elif event in ('os.listdir','os.scandir','os.chdir'): pathcheck(values[0])
    elif event in ('os.remove','os.rmdir','os.mkdir','os.chmod','os.utime'): pathcheck(values[0],True)
    elif event in ('os.rename','os.link','os.symlink'): pathcheck(values[0],True);pathcheck(values[1],True)
    elif event.startswith(('subprocess.','socket.','ctypes.')) or event in ('os.system','os.exec','os.posix_spawn','os.spawn','os.startfile','os.fork'):
        raise PermissionError('Network and child processes are unavailable in guarded local execution.')
    elif event=='import' and values[0].split('.')[0] in ('ctypes','_ctypes','winreg','_winapi'):
        raise PermissionError('Native system access is unavailable in guarded local execution.')
os.chdir(cwd)
sys.dont_write_bytecode=True
sys.path.insert(0,str(cwd))
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
# Initialize the trusted test harness before restricting project imports. Pytest
# imports Windows process support even when no project subprocess is requested.
if args[:2]==['-m','pytest']:
    import pytest
    import colorama
elif args[:2]==['-m','unittest']:
    import unittest
sys.addaudithook(guard)
if args[:1]==['-m']:
    sys.argv=[args[1]]+(['--rootdir',str(cwd),'--confcutdir',str(cwd)] if args[1]=='pytest' else [])+args[2:]
    runpy.run_module(args[1],run_name='__main__',alter_sys=True)
else:
    pathcheck(cwd/args[0])
    sys.argv=args
    runpy.run_path(str(cwd/args[0]),run_name='__main__')
