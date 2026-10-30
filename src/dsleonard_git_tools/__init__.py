# DSL's package init/ name export MIT 2026
#
# #########Quick Use insturctions##########
# 1) Don't edit this file
# 2) Prefer to use one module (file) per class (like a good language) and
#     subdirectories for namespaces (with this __init__.py copied into them)
# 3) Use core.py as your example:
#     Include an __all__ = [ class_name_in_module ]
#     and, in these single-class modules, also set:
#     __export__ = True
#     To export the class directly.
# 4) Import from other local modules INSIDE the class. Top-level local imports can break.
# 5)  Now you can use from '{{cookiecutter.project_pkg}}' import *
#     and can use my_class() directly instead of my_class.MyClass()

# ##########Philosophy: ##############
# Python style embraces throwing tons of classes in one file.
# Then the module is the namespace and we should just export the module
# names.  Best practice in all other languages is one class per file (with exceptions).
# Then we should export the contents, ie __all__ and not the module name
# (which might collide with the contents).  If we have one class per file and instead export
# the module name, we'd always have my_class.MyClass, which is ugly.
#
# We can still use directories for namespaces (with this same __init__.py)
#
# ############What it does: ###############
# Here I export all module names that don't include an __all__ and all directory names.
# And for modules that do include __all__, we add its __all__ but NOT its module name.
#
# Downside/gotcha: eager loading means we can't reliably (alphabet dependent)
#      import between local modules from the top level of a module
#      Do local imports from inside a function instead.
#

import importlib
import pkgutil
import os


# Extract the clean package folder name dynamically 
current_package_name = __package__.split('.')[-1] if __package__ else ""

# Filter out the parent package folder name along with standard underscores
submodules = [
    m.name for m in pkgutil.iter_modules(__path__) 
    if not m.name.startswith("_") and m.name != current_package_name
]
__all__ = []

#submodules = [m.name for m in pkgutil.iter_modules(__path__) if not m.name.startswith("_")]
#__all__ = []

#Build pyi file for IDE static analysis:
pyi_lines = []

# 2. SINGLE PASS: Import, update globals, and prepare stub strings
for name in submodules:
    mod_obj = importlib.import_module(f".{name}", package=__package__)
    mod_all = getattr(mod_obj, "__all__", None)
    export_all = getattr(mod_obj, "__export_all__", False)
    # if module contains __all__ or is
        # Just the module name
    if export_all and mod_all:
        # we have a safe __all__ list to hoist
        # Add to globals and __all__
        for export in mod_all:
            globals()[export] = getattr(mod_obj, export)
            __all__.append(export)
            pyi_lines.append(f"from .{name} import {', '.join(mod_all)}")
    else:
        __all__.append(name)
        pyi_lines.append(f"from . import {name} as {name}")

try:
    if os.path.exists(__file__):
        stub_path = __file__ + "i"
        new_content = f"__all__ = {__all__}\n" + "\n".join(pyi_lines)

        # Check if write is actually needed to prevent redundant IDE indexing
        if not os.path.exists(stub_path) or open(stub_path).read() != new_content:
            with open(stub_path, "w") as f:
                f.write(new_content)
except Exception:
    pass

