#Define default package imports if desired, examples below
import importlib
import pkgutil

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
__all__ = core.__all__ + submodule_names