# Env bootstrapper by Douglas S. Leonard 2026
#(C) D.S. Leonard 2026
# MIT,  use with attribution only.

import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path


def find_or_install_uv(venv_dir, toml_dir,reset=False):
    """
    spin up a venv in venv_dir using pyproject.toml in toml_dir
    """
    abs_venv_dir = os.path.abspath(venv_dir)
    os.chdir(toml_dir) # make pyproject.toml visible.

    uv_bin = find_uv()
    if not uv_bin:
        print("🚀 UV not found. Downloading standalone binary...")
        cmd = "curl -LsSf https://astral.sh/uv/install.sh | sh"
        subprocess.run(cmd, shell=True, check=True)
        uv_bin = find_uv()

    if not uv_bin:
        raise Exception(f"failed to install uv with {cmd}")

    return uv_bin

def find_uv():
    found = shutil.which("uv")
    if found:
        return found

    home = Path.home()
    if os.name == "nt":
        guesses = [
            home / "AppData/Roaming/uv/bin/uv.exe",
            home / ".cargo/bin/uv.exe"
        ]
    else:
        guesses = [
            home / ".cargo/bin/uv",
            home / ".local/bin/uv"
        ]

    for path in guesses:
        if path.exists():
            return str(path)

    return None