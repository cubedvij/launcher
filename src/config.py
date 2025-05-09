import os
import sys
import platform
import psutil

from pathlib import Path
import _version

# _COMPILED = getattr(nuitka, "__compiled__", False)
_COMPILED = getattr(sys, 'frozen', False)

if _COMPILED:
    # If the script is compiled, use the directory of the executable
    LAUNCHER_VERSION = _version.version
    LAUNCHER_DIRECTORY = os.path.dirname(sys.executable)
    MEIPASS_FOLDER_NAME = os.path.basename(sys._MEIPASS)
else:
    LAUNCHER_VERSION = "[DEV]"
    LAUNCHER_DIRECTORY = os.path.dirname(os.path.abspath(__file__))


WINDOW_SIZE = (900, 564)

AUTH_URL = "https://auth.cubedvij.pp.ua"
SERVER_IP = "play.cubedvij.pp.ua"
AUTHLIB_INJECTOR_URL = " https://auth.cubedvij.pp.ua/authlib-injector"
CHANGELOG_URL = "https://raw.githubusercontent.com/cubedvij/modpack/refs/heads/main/README.md"
MODPACK_REPO_URL = "https://github.com/cubedvij/modpack"
LATEST_LAUNCHER_RELEASE_URL = "https://api.github.com/repos/cubedvij/launcher/releases/latest"


LAUNCHER_NAME = "Кубічний Лаунчер"

SYSTEM_OS = platform.system()

if SYSTEM_OS == "Windows":
    APPDATA_FOLDER = Path.home() / "AppData" / "Roaming"
if SYSTEM_OS == "Linux":
    APPDATA_FOLDER = Path.home() / ".config"

APPDATA_FOLDER /= "cubedvij"
SKINS_CACHE_FOLDER = APPDATA_FOLDER / ".skins_cache"
if not os.path.exists(SKINS_CACHE_FOLDER):
    os.makedirs(SKINS_CACHE_FOLDER)
if not os.path.exists(APPDATA_FOLDER):
    os.makedirs(APPDATA_FOLDER)

MINECRAFT_FOLDER = APPDATA_FOLDER / ".minecraft"
if not os.path.exists(MINECRAFT_FOLDER):
    os.makedirs(MINECRAFT_FOLDER)


ACCOUNT_FILE = APPDATA_FOLDER / "account.json"
if not os.path.exists(ACCOUNT_FILE):
    with open(ACCOUNT_FILE, "w") as f:
        f.write("{}")

USER_FILE = APPDATA_FOLDER / "user.json"
if not os.path.exists(USER_FILE):
    with open(USER_FILE, "w") as f:
        f.write("{}")

# TODO: -XX:+UnlockExperimentalVMOptions -XX:+UseShenandoahGC -XX:ShenandoahGCHeuristics=adaptive
# TODO: User Azul Java 17+ for Shenandoah
JVM_ARGS = [
    "-XX:+UnlockExperimentalVMOptions",
    "-XX:+UseG1GC",
    "-XX:G1NewSizePercent=20",
    "-XX:G1ReservePercent=20",
    "-XX:MaxGCPauseMillis=50",
    "-XX:G1HeapRegionSize=32M",
]

# IN MB
RAM_SIZE = psutil.virtual_memory().total // 1024 // 1024
RAM_STEP = 256
