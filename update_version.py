# update the version with the latest git commit
import sys
import subprocess
import tomllib

git_commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True)
pyproject = tomllib.load(open("pyproject.toml", "rb"))
version = pyproject["project"]["version"]
if sys.argv[1] == "release":
    new_version = version
elif sys.argv[1] == "dev":
    new_version = f"{version}-dev-{git_commit.strip()}"
print("Building with new version number", new_version)
with open("_version.py", "w") as f:
    f.write(f'version = "{new_version}"\n')
