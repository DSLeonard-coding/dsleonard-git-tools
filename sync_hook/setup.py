"""
   sync_hook/setup.py  
   D.S. Leonard 2026, MIT
   just spawns a daemon process using uv run
   that runs after the top-level uv sync completes and releases the lock.
   Setup to call run_inits.py after uv runs to run __init__.py files to create .pyi files
   that IDE needs for autocompletion :P
"""   

import subprocess
import sys
import os
import time
from pathlib import Path
import fcntl
from contextlib import contextmanager

this_file=os.path.abspath(__file__)
project_root=os.path.dirname(os.path.dirname(this_file))

script_file=os.path.join(project_root,"scripts/run_inits.py")
script_working_dir = project_root


@contextmanager
def locked_file(path):
    with open(path, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield f
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)

def spawn_script(script,working_directory):
    this_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(this_dir, "hook_output.log")
    with open(log_path, "a") as f:
        print(f"sync_hook working directory: {this_dir}",file=f,flush=True)
        print(f"sync_hook sript: {script}",file=f,flush=True)
        print(f"sync_hook sript working directory: {working_directory}",file=f,flush=True)

        try:
            pid = os.fork()
            # parent returns to finish setup.py
            if pid > 0:
                # allow child time to grab the lock. Could be improved.
                time.sleep(0.1)
                return 
        except OSError:
            return

        #disconnect first child
        os.setsid()

        try:
            pid = os.fork()
            if pid > 0:
                os._exit(0) # First child dies, second child is now an orphan
        except OSError:
            os._exit(1)

        with locked_file(this_file):
            os.chdir("/")

            devnull = os.open(os.devnull, os.O_RDWR)
            for fd in range(3):
                os.dup2(devnull, fd)

            env = os.environ.copy()
            for key in list(env.keys()):
                if key.startswith("UV_") or key.startswith("VIRTUAL_ENV"):
                    env.pop(key, None)

            with open(log_path, "a") as f:
                subprocess.run(
                    ["uv", "run", script],
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=working_directory,
                    env=env
                )
            os.chdir(this_dir)
            Path("setup.py").touch()
            os._exit(0)

from setuptools import setup
setup(name="sync-hook", version="0.1.dev", packages=[])

if "egg_info" not in sys.argv:
    if any(arg in sys.argv for arg in ['install', 'bdist_wheel', 'develop', 'editable_wheel']):
        try:
            spawn_script(script_file,script_working_dir)
        except:
            pass #We never want to fail and block the build.
        
