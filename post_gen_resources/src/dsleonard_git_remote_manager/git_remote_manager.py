# git_remote_manager.py in dsl_get_remote_manager
# methods for creating and manipulting repos on remote gitlab/github/(etc?) hosts.
# D.S. Leonard code originally from 2024, collected 2026
# MIT license
import contextlib
from getpass import getpass
import gitlab
from github import GithubException, Auth, Github
from typing import Any, List, Optional, Union
import json
import webbrowser
import pathlib
import subprocess
from dsleonard_qx import *
from dsleonard_git_api import *
import sys
import getpass
import requests

import requests
import os

# Unified mapping for the "Big 4"
# Key: (GitHub_Field, GitLab_Field, Transform_Func)
ATTR_MAP = {
    "desc": ("description", "description", lambda x: x),
    "public": ("private", "visibility", lambda v: (not v) if isinstance(v, bool) else v),
    "wiki": ("has_wiki", "wiki_enabled", lambda x: x),
    "issues": ("has_issues", "issues_enabled", lambda x: x),
}

def detect_repo_type(host):
    """
    Fingerprints a remote host to determine if it's GitHub or GitLab.
    """
    try:
        url = f"https://{host}"
        response = requests.head(url, timeout=5, allow_redirects=True)
        headers = response.headers
        cookies = response.cookies.get_dict()

        # GitHub Signatures
        if "X-GitHub-Request-Id" in headers:
            return "github"

        # GitLab Signatures
        if "X-Gitlab-Feature-Id" in headers or "_gitlab_session" in cookies:
            return "gitlab"

        # Fallback: Probe versioned API endpoints if headers are stripped
        # GitHub Enterprise uses /api/v3
        if requests.get(f"{url}/api/v3", timeout=3).status_code in [200, 401]:
            return "github"

        # GitLab uses /api/v4
        if requests.get(f"{url}/api/v4/metadata", timeout=3).status_code in [200, 401]:
            return "gitlab"

    except requests.RequestException:
        pass

    return None


def CreateRemoteManager(host,
                        repo_namespace,
                        project_slug,
                        recreate_repo=False,
                        description="",
                        repo_type=None,
                        remote_alias="origin",
                        local_path=None):
    if repo_type is None:
        repo_type = detect_repo_type(host)
        if not repo_type:
            raise RuntimeError(f"Could not auto-detect host type for {host}. Please specify repo_type.")

    match repo_type:
        case "github":
            return GitHubRemoteManager(host, repo_namespace, project_slug, recreate_repo, description,local_path)
        case "gitlab":
            return GitLabRemoteManager(host, repo_namespace, project_slug, recreate_repo, description,local_path)
        case _:
            raise RuntimeError(f"Invalid/Unknown remote host type {repo_type}")

import os
import subprocess

def CreateRemoteManagerFromPrompt():
    CreateRemoteManagerFromGitConfig(prompt=True)

def CreateRemoteManagerFromGitConfig(git_path=None,
                                     remote_alias="origin",
                                     recreate_repo=False,
                                     description="",
                                     prompt=False):
    """
    Scans a specific directory (or PWD) for a git remote,
    parses it, and create GitHost object (with auto-detected server type)
    """
    # Use CWD if no path is provided
    alias="origin"
    if prompt:
        alias = input(f"Git remote alias [{alias}]: ").strip() or alias

    target_dir = os.path.abspath(git_path) if git_path else os.getcwd()

    if not os.path.exists(os.path.join(target_dir, ".git")):
            raise RuntimeError(f"Directory '{target_dir}' is not a git repository.")

    host, namespace, slug = "", "", ""
    try:
        # Run git command inside the specified directory
        cmd = ["git", "-C", target_dir, "remote", "get-url", remote_alias]
        remote_url = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode().strip()
        if prompt:
            msg("Found default configuration in git config")
        else:
            msg("Found configuration in git config")
        # Parse the URL (using the parser from the previous step)
        host, namespace, slug = parse_git_remote(remote_url)
    except subprocess.CalledProcessError:
        if not prompt:
            raise RuntimeError(f"Could not find remote '{remote_alias}' in {target_dir}")

    if prompt:
        print("Configure remote location as in  host:namespace/slug:")
        host = input(f"Project host (ex: gitlab.com) [{host}]: ").strip() or host
        namespace=input(f"Project namespace  [{namespace}]: ").strip() or namespace
        slug = input(f"Project slug [{slug}]: ").strip() or slug
        recreate_repo=input(f"DANGEROUS: Recreate remote repo if it exists?\n"
                      "           Must type YES to confirm [no]:").strip()
        recreate_repo=True if recreate_repo == "YES" else False
        description = input(f"Input brief project description [{description}]: ").strip() or description

    # Call main factory with repo_type=None for auto-detection
    return CreateRemoteManager(
        host=host,
        repo_namespace=namespace,
        project_slug=slug,
        recreate_repo=recreate_repo,
        description=description,
        repo_type=None,
        remote_alias=alias,
        local_path=git_path
    )


import re
from urllib.parse import urlparse


def parse_git_remote(url):
    """
    Parses a git remote URL to extract host, namespace, and slug.
    Works for:
    - https://github.com/user/project.git
    - git@gitlab.com:group/subgroup/project.git
    """
    # Remove .git suffix if present
    url = url.replace(".git", "")

    # Handle SSH format: git@github.com:user/project
    if url.startswith("git@") or "://" not in url:
        # Regex to split git@host:path
        match = re.search(r"^(?:git@|ssh://git@)?([^:/]+)[:/](.+)$", url)
        if match:
            host = match.group(1)
            path = match.group(2)
        else:
            raise ValueError(f"Could not parse SSH URL: {url}")
    else:
        # Handle HTTPS format
        parsed = urlparse(url)
        host = parsed.netloc
        path = parsed.path.lstrip("/")

    # Split the path into namespace and slug
    # GitLab can have multiple subgroups (e.g., 'group/subgroup/slug')
    parts = path.split("/")
    project_slug = parts[-1]
    repo_namespace = "/".join(parts[:-1])

    return host, repo_namespace, project_slug



class RemoteManager:
    """
    Manages remote repository creation and deployment for
    various hosting providers.
    """

    def __init__(self,
                 host,
                 repo_namespace,
                 project_slug,
                 recreate_repo=False,
                 description="",
                 token=None,
                 remote_alias="origin",
                 local_path=None):
        # Required attributes
        self._host = host
        self._repo_namespace = repo_namespace
        self._project_slug = project_slug
        self._recreate_repo = recreate_repo
        self._repo_full_name = f"{self._repo_namespace}/{self._project_slug}"
        # Optional attributes / Defaults
        self._description = description

        # Placeholders for authentication objects (lazy-loaded later)
        self._remote_manager = None
        self._repo = None

        # Construct the base SSH URL early as a convenience
        self.git_url = f"git@{self._host}:{self._repo_namespace}/{self._project_slug}.git"
        self.pygit_url = f"git+ssh://git@{self._host}/{self._repo_namespace}/{self._project_slug}.git"
        self.CREDENTIALS_FILE = pathlib.Path.home() / f".my_repo_keys.json"

        self._repo_type = ""  # set by concrete ctor
        self.https_url = self._get_https_url()
        self._token = None
        self._remote_alias = remote_alias
        self._local_path = os.path.abspath(local_path) if local_path else os.getcwd()

    def delete_repo(self):
        try:
            repo = self.get_remote_manager()
            repo.delete()
            msg(f"Remote repository {self._repo_full_name} deleted.")
        except gitlab.exceptions.GitlabGetError as e:
            if e.response_code == 404:
                warn(f"Remote repository {self._repo_full_name} not found. Skipping deletion.")
            else:
                raise RuntimeError(f"Error deleting {self.repo_type} repository: {e}")

    def _get_remote_repo(self):
        """
        Abstract method to be implemented by subclasses.
        Should return the provider-specific repository object.
        """
        raise NotImplementedError("Subclasses must implement _get_remote_repo")

    def create_remote_repo_if_allowed(self):
        self.create_and_set_remote_manager()

        existing_remote_repo = None
        try:
            existing_remote_repo = self._get_remote_repo()
        except Exception:
            pass

        if existing_remote_repo:
            if not self._recreate_repo:
                raise RuntimeError(f"\n\nRemote repo '{self._repo_full_name}' already exists and overwrite_repo is NO. \n\n")
            else:
                msg(f"Remote repo exists and overwrite is YES. Deleting {self._repo_full_name}...")
                try:
                    existing_remote_repo.delete()
                    # GitHub deletion is usually fast, but a small sleep avoids
                    # race conditions if you recreate immediately.
                    import time
                    time.sleep(1)
                except Exception as e:
                    raise RuntimeError(f"Failed to delete existing GitHub repo: {e}\n")

        self._repo = self._create_remote_repo()

    def _create_remote_repo(self):
        msg("Not implemented in base class")
        return None

    def get_remote_manager(self):
        if self._remote_manager:
            return self._remote_manager
        self.create_and_set_remote_manager()

    def _get_https_url(self):
        return f"https://{self._host}/{self._repo_namespace}/{self._project_slug}.git"

    def get_push_dest(self):
        match self._repo_type:
            case "gitlab":
                return f"https://oauth2:{self._token}@{self._host}/{self._repo_namespace}/{self._project_slug}.git"
            case "github":
                return f"https://{self._token}@{self._host}/{self._repo_namespace}/{self._project_slug}.git"
            case _:
                raise RuntimeError(f"Don't know how to push repo of type {self._repo_type}")


    def push_git_webhost(self, branch: str, force: bool):
        msg(f"Setting remote origin to {self.git_url}")
        with contextlib.chdir(self._local_path):
            git(["remote", "remove", "origin"])
            git(["remote", "add", "origin", self.git_url])
            msg("Attempting to push to remote:")
            self.get_token()
            push_dest = self.get_push_dest()
            cmd = ["push", "-u", self.git_url, f"{branch}:{branch}"]
            if force:
                cmd.append("-f")

        push_result = git(cmd)

        if push_result.returncode == 0:
            msg("Push successful!")
        else:
            full_error_output = "\n".join(push_result.errlines)
            error_text = full_error_output.replace(str(self.get_token()), "********")
            raise RuntimeError(f"Push to remote repo failed: {error_text}\n"
                               f"{push_result.lines}\n")



    def create_and_set_remote_manager(self) -> Any:
        # Get raw token string first
        token_val = self.get_token()
        manager = None
        try:
            match self._repo_type:
                case "github":
                    auth = Auth.Token(token_val)
                    manager = Github(auth=auth)
                case "gitlab":
                    manager = gitlab.Gitlab(url=f"https://{self._host}", private_token=self._token)
                    manager.auth()
            self._remote_manager = manager

        except Exception as e:
            error(f"Error in {self._repo_type} authentication. Your saved token may be invalid: {e}")
            error(f"Attempting to continue..")

    def get_token(self):
        if self._is_token_valid(self._token):
            return self._token
        if (token := self._load_token()) and self._is_token_valid(token):
            self._token = token
            return token
        msg(f"No {self._repo_type} credentials found.")
        self.get_token_from_provider()
        return self._token

    def set_token(self, token: str):
        #default, token is a string:
        retval= token
        if hasattr(token, 'token'):
            retval = token.token
            # If it's a dict (common in JSON storage)
        if isinstance(token, dict):
            retval = token.get('token')
        self._token = str(retval)

    def _load_token(self):
        try:
            with open(self.CREDENTIALS_FILE, "r") as f:
                credentials = json.load(f)
                if self._repo_type in credentials and "token" in credentials[self._repo_type]:
                    if self._repo_type == "github":
                        token=credentials[self._repo_type]["token"]
                    elif self._repo_type == "gitlab":
                        token=credentials[self._repo_type]["token"]
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            pass
        dbg(f"{self._repo_type} token read:{token}")
        if not token or not self._is_token_valid(token):
            return None
        else:
            return token

    def _save_token(self):
        try:
            with open(self.CREDENTIALS_FILE, "r") as f:
                credentials = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            credentials = {}

        if self._repo_type not in credentials:
            credentials[self._repo_type] = {}

        credentials[self._repo_type]["token"] = self._token

        with open(self.CREDENTIALS_FILE, "w") as f:
            json.dump(credentials, f, indent=4)

        os.chmod(self.CREDENTIALS_FILE, 0o600)

    def _is_token_valid(self, token):
        """Checks if the stored token is still active and authorized."""
        token_val = token.token if hasattr(token, 'token') else token
        retval = False
        if token_val:
            try:
                if self._repo_type == "github":
                    g = Github(token_val)
                    _ = g.get_user().login
                else:
                    gl = gitlab.Gitlab(f"https://{self._host}", private_token=token_val)
                    gl.auth()
                retval = True
            except Exception:
                pass
        dbg(f"Token for {self._repo_type} is not valid.\n")
        return retval


    def get_token_from_provider(self):
        msg(f"Opening browser to create a Personal Access Token...")
        msg(f"You will be prompted to login to {self._repo_type} if not already logged in.")
        msg("To use CI/CD (auto major-version-tag updating, etc) set the expiration to the longest allowed")
        msg("Click the create button and then the copy icon next to the generated key to paste it here")
        msg("The cursor will not move when you paste the key. Just hit enter.")
        match self._repo_type:
            case "github":
                scopes = "repo,delete_repo,write:org,admin:repo_hook,admin:public_key,workflow"
                webbrowser.open(
                    f"https://github.com/settings/tokens/new?scopes={scopes}&description=dsl-pylaunch-key"
                )
            case "gitlab":
                scopes = "api, read_user, write_repository, delete_repository"
                webbrowser.open(
                    f"https://{self._host}/-/user_settings/personal_access_tokens?name=Cookiecutter-pygit&scopes={scopes}")

        self.set_token(getpass.getpass("Paste the generated GitHub PAT here (cursor will not move): "))
        self._save_token()

    def is_ssh_available(self):
        result = qx(["ssh", "-T", f"git@{self._host}"])
        dbg(f"in is_ssh_available result.return code {result.returncode}", )
        output = f"{result.stdout} {result.stderr}"

        if "successfully authenticated" in output or "Welcome" in output:
            return True

        return False

    def setup_ssh_keys(self):
        if self.is_ssh_available():
            return

        # Generate a new ssh key if one doesn't exist
        key_path = pathlib.Path.home() / ".ssh" / f"id_rsa_{self._repo_type}_auto"
        if not key_path.exists():
            msg(f"Generating new SSH key at {key_path}...")
            subprocess.run([
                "ssh-keygen", "-t", "ed25519",
                "-C", f"auto-generated-{self._repo_type}",
                "-f", str(key_path), "-N", ""
            ], check=True)

        pub_key = pathlib.Path(str(key_path) + ".pub").read_text().strip()

        # Upload to GitHub/GitLab using the token you already have
        self.get_token()
        token_val = self._token

        msg(f"Uploading public key to {self._repo_type}...")
        try:
            match self._repo_type:
                case "github":
                    self._remote_manager.get_user().create_key("DSL-Auto-Key", pub_key)
                case "gitlab":
                    self._remote_manager.userkeys.create({'title': 'DSL-Auto-Key', 'key': pub_key})
        except Exception as e:
            if "already in use" in str(e).lower() or "already exists" in str(e).lower():
                msg("Key is already registered with the provider. Skipping upload.")
            else:
                raise e

        ssh_config = pathlib.Path.home() / ".ssh" / "config"
        config_entry = (
            f"\nHost {self._host}\n"
            f"  HostName {self._host}\n"
            f"  IdentityFile {key_path}\n"
            f"  StrictHostKeyChecking no\n"
        )
        with open(ssh_config, "a") as f:
            f.write(config_entry)

        if self.is_ssh_available():
            msg("SSH keys configured and uploaded. You can now push via SSH.")
        else:
            warn("Failed to configure SSH keys.  You will need to set them up before pushing in the futulre.")

    def update_settings(self, **kwargs):
        """
        Normalized updater for: desc, public, wiki, issues.
        Also accepts raw provider-specific kwargs for other settings.
        """
        raise NotImplementedError("Subclasses must implement update_settings")

    def set_branch_wiki_link(self,branch, file):
        if self._repo_type == "github":
            url =  self._get_branch_file_url(branch,file)
            msg(f"Linking wiki to repo page")
            self.update_settings(homepage=url)
        elif self._repo_type == "gitlab":
            url =  self._get_branch_file_url(branch,file)
            msg(f"Linking wiki to repo paege")
            project = self._get_remote_repo()
            current_desc = getattr(project, 'description', "") or ""
            link_markdown = f"[See the Wiki for details]({url})"
            if url not in current_desc:
                separator = " | " if current_desc else ""
                new_desc = f"{current_desc}{separator}{link_markdown}"
                self.update_settings(desc=new_desc)
            else:
                msg("Wiki link already exists in GitLab description. Skipping.")
        return url

    def _get_branch_file_url(self, branch="docs", filename="home.md"):
        """
        Constructs a direct web link to a file on a specific branch.
        """
        base = f"https://{self._host}/{self._repo_namespace}/{self._project_slug}"
        if self._repo_type == "github":
            # GitHub format: /blob/branch/file
            return f"{base}/blob/{branch}/{filename}"
        elif self._repo_type == "gitlab":
            # GitLab format: /-/blob/branch/file
            return f"{base}/-/blob/{branch}/{filename}"
        return base

class GitHubRemoteManager(RemoteManager):

    # Manages a github host
    # Handle remote repository creation (if needed)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._repo_type = "github"

    def _get_remote_repo(self):
        if not self._repo:
            # Will throw if doesn't exist:
            self._repo = self._remote_manager.get_repo(self._repo_full_name)
        return self._repo


    def _create_remote_repo(self):
        msg(f"Creating project in namespace :{self._repo_namespace}")

        # Explicitly resolving the Owner Type
        try:  # organization namespace
            owner = self._remote_manager.get_organization(self._repo_namespace)
            is_org = True
        except Exception:  # fallpack to user namespace.
            owner = self._remote_manager.get_user()
            is_org = False

        try:
            new_project = owner.create_repo(
                name=self._project_slug,
                description=self._description,
                private=True
            )

        except Exception:
            raise RuntimeError(f"\nFailed to create remote Github project:\n")

        msg(f"Repository created on GitHub: {self.https_url}")
        return new_project


    def setup_ci_secrets(self):
        """
        Injects the PAT into the project's CI/CD variables
        so the pipeline can push git tags back to itself.
        """
        token = self.get_token()
        msg(f"Injecting Actions Secret into {self._repo.name}...")

        try:
            self._repo.create_secret(
                secret_name="GH_RELEASE_TOKEN",
                unencrypted_value=token
            )
            msg("Actions secret GH_RELEASE_TOKEN created successfully.")

        except Exception as e:
            warn(f"Failed to setup GitHub Secrets. Non-fatal error: {e}")

    # ... existing methods ...
    def get_protection_settings(self, branch="main"):
        """Extracts protection settings for a specific branch."""
        msg(f"Extracting protection settings for {branch} on GitHub...")
        try:
            repo = self._remote_manager.get_repo(self._repo_full_name)
            protection = repo.get_branch(branch).get_protection()

            # This returns a Protection object. To make it 'portable', 
            # we'd usually map it to a dict of kwargs for edit_protection.
            return protection
        except Exception as e:
            warn(f"Could not fetch protection for {branch}: {e}")
            return None

    def apply_protection_settings(self, branch="main"):
        """Applies a 'Standard' security suite to a new repo."""
        msg(f"Applying standard protection to {branch}...")
        repo = self._remote_manager.get_repo(self._repo_full_name)

        # GitHub requires specific kwargs for this call
        repo.get_branch(branch).edit_protection(
            enforce_admins=True,
            dismiss_stale_reviews=True,
            required_approving_review_count=1,
            user_push_restrictions=[],  # Passing empty list means 'no one' (or keep current)
            team_push_restrictions=[]
        )
        
    def apply_github_rulesets(self, ruleset_list):
        # This look incomplete, it's for setting protected branches and tag rules.
        # Not used/tested yet.
        url = f"https://api.github.com/repos/{self._repo_full_name}/rulesets"
        headers = {"Authorization": f"token {self._token}"}
        for rs in ruleset_list:
            # Note: You'll need to strip the 'id' and 'node_id' from the extracted
            # data before POSTing it back as a new ruleset.
            requests.post(url, json=rs, headers=headers)


        # Extract Tags
        for t in project.protectedtags.list():
            data["tags"].append({
                "name": t.name,
                "create_access_level": t.create_access_levels[0]['access_level']
            })

        return data

    def extract_github_rulesets(self):
        """
        Extracts modern Repository Rulesets (which support patterns).
        """
        repo = self._remote_manager.get_repo(self._repo_full_name)

        # GitHub Rulesets API via PyGithub (or raw requests if using an older version)
        # Using raw requests here to ensure we catch the 'patterns' logic
        url = f"https://api.github.com/repos/{self._repo_full_name}/rulesets"
        headers = {"Authorization": f"token {self._token}", "Accept": "application/vnd.github+json"}

        response = requests.get(url, headers=headers)
        rulesets = response.json()

        extracted_rules = []
        for rs in rulesets:
            # Get the full detail for each ruleset
            detail = requests.get(f"{url}/{rs['id']}", headers=headers).json()
            extracted_rules.append({
                "name": detail['name'],
                "target": detail['target'],  # 'branch' or 'tag'
                "include": detail['conditions']['ref_name']['include'],  # The patterns!
                "exclude": detail['conditions']['ref_name']['exclude'],
                "rules": detail['rules']
            })
        return extracted_rules


    def update_settings(self, **kwargs):
        repo = self._get_remote_repo()
        payload = {}

        for key in list(kwargs.keys()):
            if key in ATTR_MAP:
                val = kwargs.pop(key)
                gh_key, _, transform = ATTR_MAP[key]
                payload[gh_key] = transform(val)

        # Merge remaining "free-form" kwargs
        payload.update(kwargs)

        try:
            repo.edit(**payload)
            msg(f"GitHub settings updated: {payload}")
        except Exception as e:
            error(f"GitHub update failed: {e}")

class GitLabRemoteManager(RemoteManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._repo_type = "gitlab"

    def _get_remote_repo(self):
        if not self._repo:
            self._repo = self._remote_manager.get_project(self._reponame)
        return self._repo


    def _create_remote_repo(self):
        # groups = g.groups.list(search=self._repo_namespace)
        msg(f"Creating project in namespace :{self._repo_namespace}")
        dbg(f"Auth: {self._remote_manager}")
        ns = self._remote_manager.namespaces.get(self._repo_namespace)
        try:
            new_project = self._get_repo.create({
                'name': self._project_slug,
                'namespace_id': ns.id,
                'description': self._description,
                'visibility': 'private'
            })
            git(f"remote add origin {self.git_url}")
            msg(f"Project created: {new_project.web_url}")

        except Exception as e:
            raise RuntimeError(f"Failed to create remote GitLab project: {e}\n")

        return new_project

    def setup_ci_secrets(self):
        """
        Injects the Private Token into GitLab CI/CD variables.
        Used for automated tagging or mirroring.
        """
        token = self.get_token()
        msg(f"Injecting CI/CD Variable into {self._repo.name}...")
        try:
            # GitLab variables require a key and value
            self._repo.variables.create({
                'key': 'GL_RELEASE_TOKEN',
                'value': token,
                'protected': True,
                'masked': True  # Recommended for security
            })
            msg("CI/CD variable GL_RELEASE_TOKEN created successfully.")
        except Exception as e:
            warn(f"Failed to setup GitLab Variables. Non-fatal error: {e}")

    def apply_gitlab_protections(self, config_data):
        project = self._remote_manager.projects.get(self._repo_full_name)
        for b in config_data['branches']:
            project.protectedbranches.create(b)
        for t in config_data['tags']:
            project.protectedtags.create(t)
            
    def extract_gitlab_protections(self):
        """
        Returns a dict containing all protected branch and tag patterns.
        """
        project = self._remote_manager.projects.get(self._repo_full_name)

        data = {
            "branches": [],
            "tags": []
        }

        # Extract Branches
        for b in project.protectedbranches.list():
            data["branches"].append({
                "name": b.name,
                "push_access_level": b.push_access_levels[0]['access_level'],
                "merge_access_level": b.merge_access_levels[0]['access_level'],
                "allow_force_push": getattr(b, 'allow_force_push', False)
            })


    def update_settings(self, **kwargs):
        project = self._get_remote_repo()

        for key in list(kwargs.keys()):
            if key in ATTR_MAP:
                val = kwargs.pop(key)
                _, gl_key, transform = ATTR_MAP[key]
                # Special handle for visibility string
                if key == "public":
                    project.visibility = "public" if val else "private"
                else:
                    setattr(project, gl_key, transform(val))

        # Free-form tweaking: apply any leftovers directly
        for key, val in kwargs.items():
            setattr(project, key, val)

        try:
            project.save()
            msg(f"GitLab settings updated (including overflow: {list(kwargs.keys())})")
        except Exception as e:
            error(f"GitLab update failed: {e}")