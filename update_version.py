# update the version with the latest git commit
import sys
import subprocess

git_commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True)
version = subprocess.check_output(["git", "describe", "--tags", "HEAD"], text=True).strip()
if sys.argv[1] == "--release":
    new_version = version
elif sys.argv[1] == "--dev":
    new_version = f"{version}-dev-{git_commit.strip()}"
else:
    print("Unknown argument, use --release or --dev")
    sys.exit(1)
print("Building with new version number", new_version)
with open("_version.py", "w") as f:
    f.write(f'version = "{new_version}"\n')
