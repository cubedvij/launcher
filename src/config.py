import os
import platform

from pathlib import Path

AUTH_URL = "https://auth.cubedvij.pp.ua"

if platform.system() == "Windows":
    APPDATA_FOLDER = Path.home() / "AppData" / "Roaming"  
if platform.system() == "Linux":
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
