import logging
import os
import sys
import platform
import psutil

from pathlib import Path
import _version

# _COMPILED = getattr(nuitka, "__compiled__", False)
_COMPILED = getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")

if _COMPILED:
    # If the script is compiled, use the directory of the executable
    LAUNCHER_VERSION = _version.version
    LAUNCHER_DIRECTORY = os.path.dirname(sys.executable)
    MEIPASS_FOLDER_NAME = os.path.basename(sys._MEIPASS)
    BASE_PATH = sys._MEIPASS
else:
    LAUNCHER_VERSION = "[DEV]"
    LAUNCHER_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
    MEIPASS_FOLDER_NAME = None
    BASE_PATH = os.path.dirname(__file__)

LAUNCHER_NAME = "Кубічний Лаунчер"
WINDOW_SIZE = (900, 564)

AUTH_URL = "https://auth.cubedvij.pp.ua"
SKIN_RENDER_URL = "https://skins.cubedvij.pp.ua"
STATS_URL = "https://stats.cubedvij.pp.ua"
STATS_API_VERSION = "v1"
SERVER_IP = "play.cubedvij.pp.ua"
AUTHLIB_INJECTOR_URL = "https://auth.cubedvij.pp.ua/authlib-injector"

RULES_URL = "https://telegra.ph/Pravila-serveru-06-05"

MODPACK_REPO = "cubedvij/modpack"

CHANGELOG_URL = (
    f"https://raw.githubusercontent.com/{MODPACK_REPO}/refs/heads/main/README.md"
)

MODPACK_INDEX_URL = (
    f"https://raw.githubusercontent.com/{MODPACK_REPO}/refs/heads/main/modrinth.index.json"
)
MODPACK_REPO_URL = f"https://github.com/{MODPACK_REPO}"
LATEST_LAUNCHER_RELEASE_URL = (
    "https://api.github.com/repos/cubedvij/launcher/releases/latest"
)
SYSTEM_OS = platform.system()

if SYSTEM_OS == "Windows":
    APPDATA_FOLDER = Path.home() / "AppData" / "Roaming"
if SYSTEM_OS == "Linux":
    APPDATA_FOLDER = Path.home() / ".local" / "share"

APPDATA_FOLDER /= "cubedvij"
SKINS_CACHE_FOLDER = APPDATA_FOLDER / ".skins_cache"
if not os.path.exists(SKINS_CACHE_FOLDER):
    os.makedirs(SKINS_CACHE_FOLDER)
if not os.path.exists(APPDATA_FOLDER):
    os.makedirs(APPDATA_FOLDER)


ACCOUNT_FILE = APPDATA_FOLDER / "account.json"
if not os.path.exists(ACCOUNT_FILE):
    with open(ACCOUNT_FILE, "w") as f:
        f.write("{}")

USER_FILE = APPDATA_FOLDER / "user.json"
if not os.path.exists(USER_FILE):
    with open(USER_FILE, "w") as f:
        f.write("{}")

JVM_ARGS = [
    "-XX:+UnlockExperimentalVMOptions",
    "-XX:+UseShenandoahGC",
    "-XX:ShenandoahGCHeuristics=adaptive",
]

# IN MB
RAM_SIZE = psutil.virtual_memory().total // 1024 // 1024
RAM_STEP = 256

LAUNCHER_THEMES = {
    "system": "Системна",
    "light": "Світла",
    "dark": "Темна",
}

LAUNCHER_COLORS = {
    "red": "Червоний",
    "pink": "Рожевий",
    "purple": "Фіолетовий",
    "deeppurple": "Темно-фіолетовий",
    "indigo": "Індиго",
    "blue": "Синій",
    "lightblue": "Блакитний",
    "cyan": "Бірюзовий",
    "teal": "Синьо-зелений",
    "green": "Зелений",
    "lightgreen": "Світло-зелений",
    "lime": "Лаймовий",
    "yellow": "Жовтий",
    "amber": "Бурштиновий",
    "orange": "Помаранчевий",
    "deeporange": "Темно-помаранчевий",
    "brown": "Коричневий",
    "bluegrey": "Сіро-синій",
}

if _COMPILED:
    logging.basicConfig(
        filename=APPDATA_FOLDER / "launcher.log",
        level=logging.INFO,
        # make it more readable for the user
        format="%(asctime)s [%(levelname)s] %(module)s:%(funcName)s %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("flet_core").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.ERROR)
else:
    logging.basicConfig(
        level=logging.INFO,
        # make it more readable for the user
        format="%(asctime)s [%(levelname)s] %(module)s:%(funcName)s %(message)s",
        datefmt="%H:%M:%S",
    )
    
    logging.getLogger("flet_core").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.ERROR)

logging.info(f"Launcher version: {LAUNCHER_VERSION}")
logging.info(f"Launcher directory: {LAUNCHER_DIRECTORY}")