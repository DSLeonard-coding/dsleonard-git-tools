#git_api.py implementation by Douglas S. Leonard, Copyright 2024.  MIT license.
from typing import Union, List, Optional

from  dsleonard_qx import *

def git(args: Union[str, List[str]], pretend: Optional[bool] = None, **kwargs) -> qx_out:
    """  A custom git API :P :) by D.S. Leonard, based on qx command executor by same.
         args can either be a single space-separated string, for shell execution (with related quoting and escaping headaches)
              or can be a list used for system call execution.
        Args:
        cmd: string or list including args
        **kwargs:  args to qx(...) namely verbose and, echo for output level.
        Originally published in git-alltrees, should be packaged :P
    """
    git: str = "git --no-pager"  # leading or trailing space with break things
    # ideally, this should be the only use of direct shell/process calls in the code:
    if type(args) is list:
        return (qx(git.split(' ')+args, pretend=pretend))
    elif type(args) is str:  # mypy requires it explicit
        return (qx(git+" "+args, pretend=pretend))
    else:
        error("git():Shouldn't be here.")
        exit(1)  # silence mypy
        
