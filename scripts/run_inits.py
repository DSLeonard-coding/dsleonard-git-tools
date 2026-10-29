# / script
# requires-python = ">=3.12"
# dependencies = []
# ///
#D.S. Leonard 2026
#Run all __init__.py files in project to generate .pyi files for IDE autocompletion.

import os
import sys
import importlib
from pathlib import Path

def sync_all_stubs(src_dir="src"):
    pwd=os.getcwd()
    print (pwd)
    abs_src = os.path.abspath(src_dir)
    print(abs_src)
    if not os.path.exists(abs_src):
        print(f"Error in sync_all_stubs.  Path {abs_src} not found")
        sys.exit(1)

    for root, dirs, files in os.walk(abs_src):
        if "__init__.py" in files:
            print(files)
            rel_path = os.path.relpath(root, abs_src)
            print(rel_path)
            if rel_path == ".":
                print("skipping")
                continue

            module_name = rel_path.replace(os.sep, ".")
            print(module_name)
            try:
                if module_name in sys.modules:
                    del sys.modules[module_name]
                importlib.import_module(module_name)
                print(f"✓ Synced: {module_name}")
            except Exception as e:
                print(f"✗ Failed {module_name}: {e}")

if __name__ == "__main__":
    sync_all_stubs()
