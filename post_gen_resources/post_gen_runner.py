#dsl-pylaunch post_gen_project script to setup local and remote repo, etc.
#(C) D.S. Leonard 2025
# MIT,  use with attribution only.

import os
import platform
import textwrap
import traceback
from datetime import datetime

from pathlib import Path
import webbrowser

from typing import Any, List, Optional, Union
import getpass

from dsleonard_qx import *
#TODO
from dsleonard_cc_rc_merge import merge_rc_from_json
#from dsleonard_cc_rc_merge.cc_rc_merge import merge_rc_from_json

from dsleonard_git_api import *
#from dsleonard_git_tools.git_api import *

from dsleonard_git_remote_manager import *
#from dsleonard_git_tools.git_remote_manager import *
import json

# post_gen_project.by implementation by Douglas S. Leonard, Copyright 2024.  MIT license.
import sys
# Initialize the Git repository and push it to GitLab
repo_name = "dsleonard-git-tools"
description = "Tools for git and provisioning github/gitlab repos"
repo_namespace = "DSLeonard-coding"
host = "github.com"
author_name = "Douglas Leonard"
author_email = "dleonard.dev@gmail.com"
overwrite_repo = "YES"
repo_type = "github"
#Somehow the CC vars get pasted as capitlaized True/False:
make_repo_public = False
is_create_wiki = True
is_executable_project = True
project_pkg = "dsleonard_git_tools"
show_repo = True
main_proj_dir = ""

debug = False  # verbose output

def main():
    global main_proj_dir
    main_proj_dir=os.getcwd()
    uv_bin = sys.argv[1]
    os.environ["SETUPTOOLS_SCM_PRETEND_VERSION"] = "0.1.0"
    qx(f"{uv_bin} add -r dependencies.txt")
    qx(f"{uv_bin} lock")

    initialize_git_with_remote(uv_bin,
                               host,
                               repo_namespace,
                               repo_name,
                               overwrite_repo,
                               description,
                               repo_type,
                               author_name,
                               author_email)

    # Save cc defaults for local editing
    rc_path = os.path.expanduser("~/.cookiecutterrc")
    cc_data = json.loads(r'{    "__executable_name": "dsleonard-git-tools",    "__repo_slug": "dsleonard-git-tools",    "_checkout": null,    "_copy_without_render": [        ".github/workflows/*",        ".github/*",        "post_gen_resources/src/*",        "post_gen_resources/.venv",        "post_gen_resources/.setup_env",        ".*env",        ".idea/*"    ],    "_dsleonard_cc_rc_merge_path": "/home/osboxes/repos/dsleonard-cc-rc-merge/",    "_dsleonard_git_tools_path": "/home/osboxes/repos/dsleonard-git-tools/",    "_exclude_from_rc": [        "project_name",        "project_pkg",        "overwrite_repo",        "description"    ],    "_output_dir": "/home/osboxes/repos",    "_repo_dir": "/tmp/cookiecutterogc1z3jh/pylaunch",    "_template": "pylaunch",    "_use_local_deps": false,    "author_email": "dleonard.dev@gmail.com",    "author_name": "Douglas Leonard",    "auto_push_new_repo": true,    "create_wiki_page": true,    "description": "Tools for git and provisioning github/gitlab repos",    "install_command_entry_point": true,    "license": "MIT, attribution required",    "make_repo_public": false,    "overwrite_repo": "YES",    "project_name": "dsleonard-git-tools",    "project_pkg": "dsleonard_git_tools",    "python_version": "3.10",    "repo": "github.com",    "repo_namespace": "DSLeonard-coding",    "repo_type": "github"}')

    #merge configs with user defaults, silence status output:
    qx.verbosity_thresholds(verbose_thrsh=qx.PRIORITY)
    merge_rc_from_json(cc_data, rc_path=rc_path)
    qx.verbosity_thresholds(verbose_thrsh=qx_verbosity)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"     [ {timestamp} Requirements locked in uv.lock. ]")
    print(f"     [ {timestamp} Editable default mission parameters stored in {rc_path}. ]")
    print(f"     [ {timestamp} All systems nominal. ]")
    print("\n\n")

def add_requirements(uv_bin):
    qx(f"{uv_bin} add -r dependencies.txt")
    qx("rm requirements-cleaned.txt")
    qx("rm dependencies.txt")

def open_docs(filepath="README.md"):
    if platform.system() == 'Darwin':  # macOS
        subprocess.call(('open', filepath))
    elif platform.system() == 'Windows':
        os.startfile(filepath)
    else:  # Linux
        subprocess.call(('xdg-open', filepath))


def initialize_git_with_remote(uv_bin,host, repo_namespace, repo_name, overwrite_repo, description, repo_type,author_name,author_email):
    if author_name == None:
        git_name_result = git("config --get user.name")
        if git_name_result.stdout.strip():
            author_name = git_name_result.stdout.strip()

        else:
            raise RuntimeError("No git author_name provided or found.") from None
    if author_email == None:
        git_email_result = git("config --get user.email")
        if git_email_result.stdout.strip():
            raise RuntimeError("No git author_email provided or found.") from None

    msg(f"Initializing git repository for {repo_name}...")
    git("init")

    git(f"config user.name {author_name}")
    git(f"config user.email {author_email}")

    git(["add", "."])
    git(f"commit -m 'Initial commit of {repo_name}'")

    dflt_branch = git(["rev-parse", "--abbrev-ref", "HEAD"]).lines[0]
    msg(f"Local git repository has been created and and is ready to push:")



    force_flag, recreate_repo = (True, True ) if overwrite_repo == "YES" else (True, False)

    try:
        repo=CreateRemoteManager(host,repo_namespace,repo_name,recreate_repo,description,repo_type)
        repo.create_remote_repo_if_allowed()
        repo.setup_ssh_keys()  #optional, can push with token directly.
        repo.push_git_webhost(dflt_branch,force_flag)
    except Exception as e:
        print (str(e).split("Traceback")[0].strip())
        raise RuntimeError("\n\n\nUnable to create or push to remote repo.\n"
                           "Your local repository is setup.\n"
                           "You can manually setup your remote or review error messages above and try again.\n\n")
    try:
        repo.setup_ci_secrets()
    except Exception as e:
        print (str(e).split("Traceback")[0].strip())
        raise RuntimeError("\n\n\nUnable to setup authorization keys for CI/CD\n"
                           "Your repo was successfully created and pushed to the remote.\n"
                           "This only impacts automation on the remote, which you can setup manually.\n")
    wiki_url=""
    if is_create_wiki:
        git("checkout --orphan wiki")
        git("rm -rf . --cached")
        git("rm -rf .")
        qx(f"echo '# {repo_name} Wiki  \n' >> home.md")
        #TODO, mark the url as public (no _)
        qx(f'echo "[Link to the project repo]({repo.https_url})\n" >> home.md')

        # Add a doctoc tag to home.md.  Optional but makes TOC location explicit:
        doctoc_tags=textwrap.dedent('''
            <!-- START doctoc generated TOC please keep comment here to allow auto update -->
            <!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
            
            <!-- END doctoc generated TOC please keep comment here to allow auto update -->
            '''
        )
        qx(f'echo "{doctoc_tags}" >> home.md')
        qx(f"echo '\n\n## Section to be written' >> home.md")
        qx(f"echo '### Subsection to be written' >> home.md")
        git("add home.md")
        # Add the doctoc action workflow for github:
        git("add .github/workflows/toc.yml")
        git("commit -m 'First commit of wiki'")
        git('push -u origin wiki')
        wiki_url = repo.set_branch_wiki_link("wiki","home.md")
        git(f'checkout -f {dflt_branch}')

    #push a tag, trigger workflow
    git('tag v0.0.1')
    git('push origin --tags')

    if make_repo_public:
        repo.update_settings(public=True)

    def link(url, text=None):
        # OSC 8 escape sequence for clickable terminal links
        text = text if text is not None else url
        return f"\033]8;;{url}\033\\{text}\033]8;;\033\\"

    # Setup paths and links
    abs_path = os.path.abspath(main_proj_dir)
    local_base_raw = f"{abs_path}"
    local_base = link(local_base_raw)
    remote_orbit = link(repo.https_url, repo.https_url)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n")
    print(f"\n     🚀 {'-' * 80} 🚀")
    print(f"\n     [ {timestamp} Mission Report: ]")
    print(f"     🚀 PYLAUNCH SUCCESSFUL")
    print(f"\n     🚀📂 LOCAL BASE   {local_base}")
    print(f"\n     🚀🌐 REMOTE ORBIT {remote_orbit}")

    def code(text):
        return f"\033[48;5;236m\033[38;5;253m {text} \033[0m"

    if is_create_wiki:
        wiki_link = link(wiki_url, wiki_url)
        print(f"\n     🚀📖 Wiki COMMS   {wiki_link}")

    command = f"uvx {repo.pygit_url}"
    if is_executable_project:
        print(f"\n     🚀📡 EXECUTE mission ops: {code(link(command))}")

    command = f"uv add {repo.pygit_url}"
    print(f"\n     🚀🛰️  MODULE integration: {code(link(command))}")
    src_dir = f"{local_base_raw}/src/{project_pkg}"
    print(f"\n     🚀🛰️  PAYLOAD MAINTENANCE: {code(link(src_dir))}")

    print(f"\n     🚀 {'-' * 80} 🚀")

    if show_repo:
        webbrowser.open(repo.https_url)

project_path = os.getcwd()
print(f"\n🚀 New repo created at: {project_path}")

qx_verbosity = qx.INFO
if debug:
    qx_verbosity=qx.DEBUG
    qx.verbosity_thresholds(verbose_thrsh=qx_verbosity)

try:
    cwd = os.getcwd()
    main()
except (SystemExit,Exception) as e:
    if isinstance(e, SystemExit) and (e.code == 0 or e.code is None):
        sys.exit(0)

    print("")
    print("***************Errors occurred in post-project generation*********")
    print("Your project,repo, or remotes may not be fully configured.")
    if not isinstance(e, SystemExit):
        os.chdir(cwd)
        errfile="post-gen-runner-error-log.txt"
        with open(errfile, "w") as f:
            traceback.print_exc(file=f)
            print(e, file=f)
        print(f"Traceback dumped to {cwd}/{errfile}")
        print("")
    sys.exit(1)


