#D.S. Leonard 2026
#Define default package imports if desired, examples below
#The automation here was in a prototype stage when this repo was built by pylaunch.
#As pylaunch itself depends on this.  Just by-hand hoisting here really:
import importlib
import pkgutil
from .core import *
from . import git_api
from .git_api import *
from . import git_remote_manager
from .git_remote_manager import *

#get names of all public modules except core
submodule_names = [
    name for _, name, _ in pkgutil.iter_modules(__path__)
    if not name.startswith("_") and name != "core"
]

#import them and add them to __all__ exports
__all__ = []
for name in submodule_names:
    importlib.import_module(f".{name}", package=__package__)
    __all__.append(name)

#import core lib. Its name doesn't get exported
core = importlib.import_module(".core",package=__package__)

#but everything in it does...
__all__ = core.__all__ + git_api.__all__ + git_remote_manager.__all__ + submodule_names