# dsleonard-git-tools
> Tools for git and provisioning github/gitlab repos  
By Douglas Leonard, Copyright 2026

## License

This project is licensed under the following terms:  
MIT, attribution required  

### Install uv if you don't have it
```
curl -LsSf https://astral.sh/uv/install.sh | sh    # or with pip:  pip install pipx; pip install uv
```

### Install and run the app/command:
```bash
uv tool install "git+https://github.com/DSLeonard-coding/dsleonard-git-tools.git"
dsleonard-git-tools
```

To use ssh (if this is a private project) use:
```bash
uv tool install "git+ssh://git@github.com/DSLeonard-coding/dsleonard-git-tools.git"
```

If want to use libraries provided by the application...

### Use in your custom library or app
To use dsleonard-git-tools in a python program, cd to your working directory or project directory, if it's already a  project, and just do:
```bash
uv add "dsleonard-git-tools @ git+https://github.com/DSLeonard-coding/dsleonard-git-tools.git"
uv sync   # redundant here actually.
uv run myscript.py

```
for private repos replace ```git+https://```   with ```git+ssh://git@``` to use ssh authentication.


### Use in a quick script:
The --script option will embedd the dependencies to the top of your script, avoiding the need for a pyproject.toml
```bash
uv add --script myscript.py "dsleonard-git-tools @ git+https://github.com/DSLeonard-coding/dsleonard-git-tools.git"
uv run --python 3.13 myscript.py    # the --python <version> is optional
```
or use the uv shebang at the top or the script
```sh
#!/usr/bin/env -S uv run --script
```
and just after the ```uv add```:
```bash
./myscript.py
```
However for your script to not break when dependencies change, you need an extra lock file anyway, made with:
```bash
uv lock --script myscript.py
```
### Explanation, uv vs conda, pip,  and best practices
Here ```uv add``` adds the dependency to an existing pyproject.toml file, or creates a new one, and actually
does a ``` uv sync ```, which replaces ```conda activate``` and ```pip install```.  It creates a venv that applies within that directory and all subdirectories,  installs the latest version of the library in it, and creates the uv.lock file to lock dependency versions for future use.  

To make sure your script always builds with the same library version you tested with, include the created uv.lock file in your distribution of the script (git or otherwise).  Further use of ```uv sync``` will be version pinned, insuring old git commits are locked to build the same as when the commit was made.  

Do not be tempted to select a tag in the add command.  This will strongly restrict/break dependency resolution in even moderately bigger projects.  This is what uv.lock is for, especially with source dependencies.

Resolving dependency problems with source builds has become almost impossible with pip and was never great.  The lock file and various overrides make
uv a clear winner for source-based (non-pypi) github sharing.


---
This project was made and launched using the [dsleonard-pylauch](https://github.com/DSLeonard-coding/dsleonard-pylaunch.git) cookie cutter.  To launch your own just do:
```bash
uvx cookiecutter https://github.com/DSLeonard-coding/dsleonard-pylaunch.git
```



