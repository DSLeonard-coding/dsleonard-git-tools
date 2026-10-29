#!/bin/env python3
# main.py
# Copyright  Douglas Leonard 2026.
#
# License: MIT, attribution required
#
# provided skeleton by D.S. Leonard, MIT licensed.

#Setup useful verbosity controls for messaging and shell command execution via qx:
#see https://github.com/DSLeonard-coding/qx
from dsleonard_qx import *  # noqa so linters won't move this # type: ignore

#Names available
#from  'dsleonard_git_tools'.core import *
__all__=[
    'dsleonard_git_tools',
]
# Set __export__all__ to True to elevate names in __all__ to package level,  ie now
# from 'dsleonard_git_tools' import *
# For single modules, this prevents my_class.MyClass() redundancy.
__export_all__ = True

#From bash, use export dsleonard_git_tools_DEBUG="True" to enable debug output
_DEBUG: bool = False   # print commands called with qx commands
if "dsleonard_git_tools_DEBUG" in os.environ:
    _DEBUG = True
_PRETEND: bool = False  #Option to only print qx commands, not run.

def _setup_qx():
    qx.verbosity_thresholds(qx.INFO)
    if _DEBUG or _PRETEND:
        qx.verbosity_thresholds(qx.DEBUG)   # Debug output level
    # Edit default output severity for qx command echoing and stdout, and set pretend
    qx.defaults(out_lvl=qx.INFO, echo_lvl=qx.INFO, pretend=_PRETEND)


#Edit project.scripts in pyproject.toml if you rename it, or to change the cli name

def dsleonard_git_tools():
    _setup_qx()
    msg("This is dsleonard_git_tools")  #qx.INFO level message
    msg("Edit this code in src/dsleonard_git_tools/main.py")  #qx.INFO level message
    qx(f'echo Hello World')  # a simple shell command.
    dbg("This method only displays with _DEBUG == True")

