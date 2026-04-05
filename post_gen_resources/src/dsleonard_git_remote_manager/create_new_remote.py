#Create and push new git remote repo from cli
# D.S. Leonard 2026, MIT
#
from git_remote_manager import *
from dsleonard_qx import *
from dsleonard_git_api import *

def main():
    manager=CreateRemoteManagerFromGitConfig()
    manager.create_remote_repo_if_allowed()
    manager.push_git_webhost()
    do_secrets = input("Setup CI/CD secrets for automation on remote? y/n (you can do it manually later) [n]:")
    if do_secrets == "y":
        manager.setup_ci_secrets()

if __name__ == "__main__":
    main()



