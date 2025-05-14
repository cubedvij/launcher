# update the version with the latest git commit
import sys
import subprocess

git_commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True)
if sys.argv[1] == "--release":
    new_version = subprocess.check_output(["git", "describe", "--tags", "--abbrev=0"], text=True).strip()
elif sys.argv[1] == "--dev":
    new_version = f"dev-{git_commit.strip()}"
else:
    print("Unknown argument, use --release or --dev")
    sys.exit(1)
print("Building with new version number", new_version)
with open("_version.py", "w") as f:
    f.write(f'version = "{new_version}"\n')