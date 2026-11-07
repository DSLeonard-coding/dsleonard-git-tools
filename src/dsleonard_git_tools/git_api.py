#git_api.py implementation by Douglas S. Leonard, Copyright 2024.  MIT license.
from typing import Union, List, Optional
__all__=["git"]
__export_all__ = True
from  dsleonard_qx import *

import platform
import shutil

# Determine the right shell executable based on OS
def get_default_shell():
    if platform.system() == "Windows":
        # Look for git-bash on Windows, otherwise fall back to None (which uses cmd.exe)
        # shutil.which can check common paths if git is in PATH
        return shutil.which("bash") or r"C:\Program Files\Git\bin\bash.exe"
    else:
        return "/bin/bash"

def git(args: Union[str, List[str]], pretend: Optional[bool] = None, check: bool = True, **kwargs) -> qx_out:
    """  A custom git API :P :) by D.S. Leonard, based on qx command executor by same.
         args can either be a single space-separated string, for shell execution (with related quoting and escaping headaches)
              or can be a list used for system call execution.
        Args:
        cmd: string or list including args
        **kwargs:  args to qx(...) namely verbose and, echo for output level.
        Originally published in git-alltrees, should be packaged :P
    """
    git_cmd: str = "git --no-pager"  # leading or trailing space with break things
    # ideally, this should be the only use of direct shell/process calls in the code:
    cmd =""
    if type(args) is list:
        cmd = git_cmd.split(' ')+args
    elif type(args) is str:  # mypy requires it explicit
        cmd = git_cmd + " " + args
    else:
        error("git():Shouldn't be here.")
        exit(1)  # silence mypy

    result = (qx(cmd, pretend=pretend, **kwargs))
    if check and not result:
        raise RuntimeError(
            f"{git_cmd} returned non-zero exit code. Std error output follows: \n"
            f"{result.stderr}\n"
        )

    return result
