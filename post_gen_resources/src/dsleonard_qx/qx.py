# Douglas S. Leonard 2023
# MIT expat license
""" Provides qx callable to run shell commands with subprocess.run

Closest we can get to perl/shell bakcticks (command-line execution), but better.
Includes optional log-level control for stdout,stderr and echoing the cmd
as well as a simple messaging interface piggy-backing on that.  

qx(<cmd>,<optional args>):  
    Requied arguments:  
    <cmd>   The shell command to execute and arguments, all as a single string or list of strings.  

    Example usage, interpretted as if entered in sequence:  
    qxv(["echo", "Hello"])        :   runs "echo" command with "Hello" argument.  By defalt, displays output.
        (  same as qx(["echo", "Hello"],out_lvl=qx.HIGHEST  )  
    x = qx("echo Hello").stdout  :   same, and stores output ("Hello") in x.   
    qx(f"echo say {x}")          :   runs "echo" command with arguments "say Hello".  
    qx.defaults(pretend=True); qx(f"echo say {x}")  : prints full command "echo say Hello" to screen
                                                      without running it.  This is meant to temporarily 
                                                      disable running commands,  and print them instead    
                                                     msg() is better for just printing a message.
    x = qx("ls -1").lines        :   collects file names as a list in x.   
    msg("Hello")                 :  Prints hello to screen, if verbosity <= INFO. 
    dbg("You are here.")         :  Prints "DEBUG: You are here." if verbosity <= DEBUG. (see others below)
                                           
    USE CASES from simplest to advanced:  
    from qx import *  # Note: imports qx.qx to qx  

    1) Default:  
    Just use qx(<cmd>).  Commands will be run, with output available in the return value.

    2) Dead-Simple:  
    Same as 1 but at start of main() call qx.verbosity_thresholds(qx.DEBUG) to print all commands and outputs.

    3) Easy:  
    Same as 2 but set verbose=<LEVEL> on each call to differntiate which calls will have output at each threshold.
    See level aliases below.  

    4) Advanced:  
    For more control just call qx.defaults(out_lvl=qx.<X>,echo_lvl=qx.<Y>), not err_lvl, 
    and  then err_lvl will track out_lvl for per-call adjustments (because it has no default).
    Actually this is true even without setting defaults at all, but then you get the default default of DEBUG
    and both err_lvl and echo_lvl will track out_lvl if they are not explicitly set on each call to qx  

    Return value (via call to qx() ):
    a qx_out object, an extended CompletedProcess,  with attributes of: stdout, stderr, returncode, args, 
    and check_returncode(). Also includes lines and errlines list attributes with output lines split and 
    newlines removed. These always contain at least an empty list, not None.  

    qx uses a typical log-level system for output verbosity for printing the command itself and its 
    stdout and stderr, with independent controls for all three or simplified combined controls. (See USE CASES below)
    Each call optionally sets the "importance" level for all three outputs which are compared to the corresponding 
    global threshold settings that are then increased and decreased to adjust which things will be output.  

    Optional args with initial defaults:  
    out_lvl : Optional[int] = qx.DEBUG    # if >=  qx.out_thrsh,   
                                            #   cmd stdout is printed   
    err_lvl     : Optional[int] =  None   # if >= qx.err_thrsh,  
                                            #   stderr is printed.  
    echo_lvl    : Optional[int] =  None       # if >= qx.echo_thrsh,  
                                            #   the <cmd> is printed.  
    verbose     : Optional[int]  = None    #  Sets all output levels                                        
    pretend : bool None                   #  Can override class attribute to force command to  
                                            #  run even if qx.pretend == True.  

    Default values are set with qx.defaults().  
    For each call...  
    err_lvl will be set to the first non-None value in the list:  
                err_lvl, verbose, qx.err_lvl (class default), out_lvl  
    echo_lvl will be set to the first non-None value in:  
                echo_lvl, verbose, qx.echo_lvl (class default), out_lvl  
    out_lvl will be set to the first non-None value in:  
                out_lvl, verbose, qx.out_lvl (if modified), DEBUG (initial default),    
    If nothing is set, everything defaults to DEBUG via fallback through out_lvl,  
    and no output will be emitted unless the thresholds are also raised to at least DEBUG.  


qx.verbosity_thresholds(verbose_thrsh, out_thrsh=None,err_thrsh=None,echo_thrsh=None,):
    Sets the following verbosity levels (with initial values):  

    out_thrsh:     int = INFO    # Threshold for output of stdout  
    err_thrsh:     int = INFO    # Threshold for output of stderr  
    echo_thrsh:    int = INFO    # Threshold for printing command to stdout  
    verbose_thrsh  int = NONE    # Just an alias to set all three above thresholds  

    NOTE: Unset options are set to out_thrsh after out_thrsh is set or defaulted.  


    Threshold aliases, names are intentionally a little different  
    Since the use is for important command output, not necessarily warnings and errors.  
    qx.NEVER = 0       # Stuff that should never be output, makes sense in context of 3 channels of output.  
    qx.TRACE = 10      # Things to print at high versobisty  
    qx.DEBUG = 20      # Debugging iformation  
    qx.INFO = 30       # Stanardard  
    qx.PRIORITY = 40   # Only High Priority messages, ex: warnings.  
    qx.CRITICAL = 50   # For fatal errors for example  
    qx.HIGHEST = 100   # Probably no messages should have this level.  
                        # So setting the threshold to HIGHEST can produce silence.  
                        # But that is not enforced.  

qxv(...)  
    Just a shortcut to qx but with verbose = True by default.  

Messaging Functions:  (built on command echoing and level system above)  
msg(msg,**kwargs)  

takes an optional verbose or echo_lvl arg and prints msg.  
verbosity default = INFO.

dbg(msg)  

Prints DEBUG: {msg} at level <= qx.DEBUG and exits  

warn(msg)  

Prints WARNING: {msg} at level <= qx.PRIORITY  

error(msg)  

Prints FATAL ERROR: {msg} at level <= qx.CRITICAL and exits  

trace(msg)  

Prints Trace: {msg} at level <= qx.TRACE and exits  
"""

from curses import echo
import errno
from genericpath import exists
import subprocess
import os
import sys
from tabnanny import verbose
from typing import List, NoReturn, Optional, Union
import typing


class qx_out(subprocess.CompletedProcess):
    """ 
    Like a CompletedProcess, holds results of process, but sanitized a little
    stdout and std err are in Lists with lines broken and newlines stripped.
    """

    def __init__(self, args: List[str], returncode: int, stdout=None, stderr=None):
        super().__init__(args, returncode, stdout, stderr)
        self.extend()

    @classmethod
    def from_CompletedProcess(cls, proc: subprocess.CompletedProcess) -> 'qx_out':
        """Build directly from a CompletedProcess, the primary use"""
        output = cls(args=proc.args, stdout=proc.stdout,
                     stderr=proc.stderr, returncode=proc.returncode)
        output.extend()
        return (output)

    def extend(self) -> None:
        """ extends the CompletedProcess with sanitized output """
        self.lines: List[str] = (self.stdout or '').splitlines()  # can't splitlines with None
        # can't splitlines with None
        self.errlines: List[str] = (self.stderr or '').splitlines()


class Qx:  # lower case because it mostly behaves like a function.

    _pretend: Optional[bool] = False  # only print cmd, don't run,

    # Stuff that should never be output, makes sense in context of 3 channels of output.
    NEVER = 0
    TRACE = 10      # Things to print at high versobisty
    DEBUG = 20      # Debugging iformation
    INFO = 30       # Stanardard
    PRIORITY = 40   # Only High Priority messages, ex: warnings.
    CRITICAL = 50   # For fatal errors for example
    HIGHEST = 100   # Probably no messages should have this level.
    # So setting the threshold to HIGHEST can produce silence.
    # But that is not enforced.

    _out_thrsh:  int = INFO    # Threshold for output of stdout/stderr
    _echo_thrsh:  int = INFO    # Threshold for printing command to stdout
    _err_thrsh:  int = INFO    #

    # Default output levels for commands,
    # Overrideable on each call:
    _out_lvl:  int = DEBUG
    _echo_lvl:  Optional[int] = None
    _err_lvl:  Optional[int] = None

    @classmethod
    def verbosity_thresholds(cls, verbose_thrsh: Optional[int] = None, out_thrsh: Optional[int] = None,
                             echo_thrsh: Optional[int] = None, err_thrsh: Optional[int] = None) -> None:
        """Sets global verbosity thresholds for qx output"""
        cls._out_thrsh = (verbose_thrsh if verbose_thrsh is not None
                          else out_thrsh if out_thrsh is not None else cls._out_thrsh)
        cls._echo_thrsh = (verbose_thrsh if verbose_thrsh is not None
                           else echo_thrsh if echo_thrsh is not None else cls._out_thrsh)
        cls._err_thrsh = (verbose_thrsh if verbose_thrsh is not None
                          else err_thrsh if err_thrsh is not None else cls._out_thrsh)

    @classmethod
    def defaults(cls, out_lvl: Optional[int], echo_lvl: Optional[int] = None,
                 err_lvl: Optional[int] = None, pretend: Optional[bool] = None) -> None:
        """ Sets defatuls for qx including output levels"""
        cls._out_lvl = out_lvl if out_lvl is not None else qx._out_lvl
        cls._err_lvl = err_lvl
        cls._echo_lvl = echo_lvl
        cls._pretend = pretend

    def __call__(self, cmd: Union[str, List[str]], verbose: Optional[int] = None, out_lvl: Optional[int] = None,
                 err_lvl: Optional[int] = None, echo_lvl: Optional[int] = None, pretend: Optional[bool] = None,
                 **kwargs
                 ) -> qx_out:  #
        """ This does the work, no instance is made """
        run: bool = True  # run the command
        self.pretend = pretend if pretend is not None else qx._pretend
        # Prioritize direct arg, then verbose arg, then default.
        # err_lvl will fall_back to out_lvl if nothing is set (including a default)
        out_lvl = (
            out_lvl if out_lvl is not None
            else verbose if verbose is not None
            else qx._out_lvl
        )
        err_lvl = (
            err_lvl if err_lvl is not None
            else verbose if verbose is not None
            else qx._err_lvl if qx._err_lvl is not None
            else out_lvl
        )
        echo_lvl = (
            echo_lvl if echo_lvl is not None
            else verbose if verbose is not None
            else qx._echo_lvl if qx._echo_lvl is not None
            else out_lvl
        )
        if self.pretend: # don't print empty output
            out_lvl = self.NEVER
            err_lvl = self.NEVER

        self.print = False
        self.print_cmd = False
        self.print_err = False
        is_shell = False
        if self.pretend:
            run = False
        if out_lvl >= qx._out_thrsh:
            self.print = True
        if echo_lvl >= qx._echo_thrsh:
            self.print_cmd = True
        if err_lvl >= qx._err_thrsh:
            self.print_err = True
        if type(cmd) is list:
            if self.print_cmd:
                for word in cmd:
                    print('"'+word.replace('"', r'\"')+'" ', end='')
                print("\n")
        else:
            is_shell = True
            if self.print_cmd:
                print(cmd, "\n")
        if run:
            output: 'subprocess.CompletedProcess[str]' = subprocess.run(
                cmd, capture_output=True,text=True,shell=is_shell,**kwargs)
        else:
            output = subprocess.CompletedProcess(cmd, 0)
        # replace None outputs with empty strings
        output = qx_out.from_CompletedProcess(output)
        # FIXME:  We need popen above and two async reader threads here
        # This solution is kind of a quick hack
        if self.print:
            print(output.stdout)
            sys.stdout.flush()
        if self.print_err:
            print(output.stderr, file=sys.stderr)
            sys.stderr.flush()
        return (output)
qx = Qx()


def qxv(cmd: Union[str, List[str]], out_lvl=qx.CRITICAL, err_lvl=qx.CRITICAL) -> 'qx_out':  #
    """ 
       A shorthand wrapper for qx to pass through (print) stdout and stderr
    """
    output: qx_out = qx(cmd, out_lvl=out_lvl, err_lvl=err_lvl)
    return output

class Msg:
    def __call__(self, cmd: str, verbose: Optional[int] = None, echo_lvl: Optional[int] = None):
        echo_lvl = echo_lvl if echo_lvl is not None else verbose if verbose is not None else qx.INFO
        output: 'subprocess.CompletedProcess[str]' = qx(cmd, echo_lvl=echo_lvl, pretend=True, out_lvl=qx.NEVER,
                                                        err_lvl=qx.NEVER)
        return output    
msg = Msg()

class Warn:
    prefix = "WARNING: "
    level = qx.PRIORITY

    @classmethod
    def end(cls):  # stub for inheritted functionality
        pass

    def __call__(self, cmd: Union[str, List[str]]):
        if type(cmd) is list:
            cmd = [f"{self.prefix}"]+cmd
        elif type(cmd) is str:
            cmd = self.prefix+cmd
        output: qx_out = qx(cmd, out_lvl=qx.NEVER,
                            err_lvl=qx.NEVER, echo_lvl=self.level, pretend=True)
        warn.end()
        return output    
warn = Warn()

class Error(Warn):
    prefix = "FATAL ERROR: "
    level = qx.CRITICAL

    @classmethod
    def end(cls):
        print("     Exiting....")
        exit(1)
error = Error()

class Dbg(Warn):
    prefix = "DEBUG: "
    level = qx.DEBUG
dbg = Dbg()

class Trace(Warn):  # For very detailed output
    prefix = "Trace: "
    level = qx.TRACE

trace = Trace()
