# This file is part of minecraft-launcher-lib (https://codeberg.org/JakobDev/minecraft-launcher-lib)
# SPDX-FileCopyrightText: Copyright (c) 2019-2025 JakobDev <jakobdev@gmx.de> and contributors
# SPDX-License-Identifier: BSD-2-Clause

"""
utils contains a few functions for helping you that doesn't fit in any other category
"""

import json
import os
import pathlib
import platform
import random
import shutil
import uuid
from datetime import datetime

from ._helper import assert_func, get_requests_response_cache
from ._internal_types.shared_types import ClientJson, VersionListManifestJson
from .types import LatestMinecraftVersions, MinecraftOptions, MinecraftVersionInfo
from .version import __version__


def get_minecraft_directory() -> str:
    """
    Returns the default path to the .minecraft directory.
    """
    home = str(pathlib.Path.home())
    system = platform.system()
    if system == "Windows":
        appdata = os.getenv("APPDATA", os.path.join(home, "AppData", "Roaming"))
        return os.path.join(appdata, ".minecraft")
    elif system == "Darwin":
        return os.path.join(home, "Library", "Application Support", "minecraft")
    else:
        return os.path.join(home, ".minecraft")


def get_latest_version() -> LatestMinecraftVersions:
    """
    Returns the latest version of Minecraft.
    """
    url = "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json"
    return get_requests_response_cache(url).json()["latest"]


def get_version_list() -> list[MinecraftVersionInfo]:
    """
    Returns all versions that Mojang offers to download.
    """
    url = "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json"
    vlist: VersionListManifestJson = get_requests_response_cache(url).json()
    return [
        {
            "id": v["id"],
            "type": v["type"],
            "releaseTime": datetime.fromisoformat(v["releaseTime"]),
            "complianceLevel": v["complianceLevel"],
        }
        for v in vlist["versions"]
    ]


def get_installed_versions(minecraft_directory: str | os.PathLike) -> list[MinecraftVersionInfo]:
    """
    Returns all installed versions.
    """
    modpacks = os.listdir(minecraft_directory)
    modpacks = [d for d in modpacks if os.path.isdir(os.path.join(minecraft_directory, d))]

    dir_list = []

    for modpack in modpacks:
        versions_path = os.path.join(minecraft_directory, modpack, "versions")
        try:
            dir_list.extend(os.listdir(versions_path))
        except FileNotFoundError:
            return []

    version_list: list[MinecraftVersionInfo] = []
    for version_id in dir_list:
        json_path = os.path.join(versions_path, version_id, f"{version_id}.json")
        if not os.path.isfile(json_path):
            continue
        with open(json_path, "r", encoding="utf-8") as f:
            version_data: ClientJson = json.load(f)
        try:
            release_time = datetime.fromisoformat(version_data["releaseTime"])
        except (ValueError, KeyError):
            release_time = datetime.fromtimestamp(0)
        version_list.append({
            "id": version_data.get("id", version_id),
            "type": version_data.get("type", "unknown"),
            "releaseTime": release_time,
            "complianceLevel": version_data.get("complianceLevel", 0),
        })
    return version_list


def get_available_versions(minecraft_directory: str | os.PathLike) -> list[MinecraftVersionInfo]:
    """
    Returns all installed versions and all versions that Mojang offers to download.
    """
    available = get_version_list()
    known_ids = {v["id"] for v in available}
    for v in get_installed_versions(minecraft_directory):
        if v["id"] not in known_ids:
            available.append(v)
    return available


def get_java_executable() -> str:
    """
    Tries to find out the path to the default java executable.
    Returns 'java' or 'javaw' if no path was found.
    """
    system = platform.system()
    java_home = os.getenv("JAVA_HOME")
    if system == "Windows":
        if java_home:
            return os.path.join(java_home, "bin", "javaw.exe")
        path = r"C:\Program Files (x86)\Common Files\Oracle\Java\javapath\javaw.exe"
        if os.path.isfile(path):
            return path
        return shutil.which("javaw") or "javaw"
    if java_home:
        return os.path.join(java_home, "bin", "java")
    if system == "Darwin":
        return shutil.which("java") or "java"
    # Linux/Other
    if os.path.islink("/etc/alternatives/java"):
        return os.readlink("/etc/alternatives/java")
    if os.path.islink("/usr/lib/jvm/default-runtime"):
        return os.path.join(
            "/usr", "lib", "jvm",
            os.readlink("/usr/lib/jvm/default-runtime"),
            "bin", "java"
        )
    return shutil.which("java") or "java"

_version_cache = None

def get_library_version() -> str:
    """
    Returns the version of minecraft-launcher-lib.
    """
    global _version_cache
    if _version_cache is None:
        _version_cache = str(__version__)
    return _version_cache

def generate_test_options() -> MinecraftOptions:
    """
    Generates test options to launch minecraft.
    This includes a random name and a random uuid.
    """
    return {
        "username": f"Player{random.randrange(100, 1000)}",
        "uuid": str(uuid.uuid4()),
        "token": "",
    }

def is_version_valid(version: str, minecraft_directory: str | os.PathLike) -> bool:
    """
    Checks if the given version exists (installed or downloadable).
    """
    if os.path.isdir(os.path.join(minecraft_directory, "versions", version)):
        return True
    return any(v["id"] == version for v in get_version_list())

def is_vanilla_version(version: str) -> bool:
    """
    Checks if the given version is a vanilla version.
    """
    return any(v["id"] == version for v in get_version_list())

def is_platform_supported() -> bool:
    """
    Checks if the current platform is supported.
    """
    return platform.system() in {"Windows", "Darwin", "Linux"}

def is_minecraft_installed(minecraft_directory: str | os.PathLike) -> bool:
    """
    Checks if there is an existing Minecraft installation in the given directory.
    """
    try:
        assert_func(os.path.isdir(os.path.join(minecraft_directory, "versions")))
        assert_func(os.path.isdir(os.path.join(minecraft_directory, "libraries")))
        assert_func(os.path.isdir(os.path.join(minecraft_directory, "assets")))
        return True
    except AssertionError:
        return False
