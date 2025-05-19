# This file is part of minecraft-launcher-lib (https://codeberg.org/JakobDev/minecraft-launcher-lib)
# SPDX-FileCopyrightText: Copyright (c) 2019-2025 JakobDev <jakobdev@gmx.de> and contributors
# SPDX-License-Identifier: BSD-2-Clause
"""This module contains some helper functions. It should not be used outside minecraft_launcher_lib"""

import datetime
import hashlib
import json
import lzma
import os
import platform
import re
import subprocess
import sys
import time
import zipfile
from typing import Any, Literal, Optional

import httpx

from ._internal_types.helper_types import MavenMetadata, RequestsResponseCache
from ._internal_types.shared_types import ClientJson, ClientJsonLibrary, ClientJsonRule
from .exceptions import FileOutsideMinecraftDirectory, InvalidChecksum, VersionNotFound
from .types import CallbackDict, MinecraftOptions
from .version import __version__

if os.name == "nt":
    info = subprocess.STARTUPINFO()  # type: ignore
    info.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # type: ignore
    info.wShowWindow = subprocess.SW_HIDE  # type: ignore
    SUBPROCESS_STARTUP_INFO: Optional[subprocess.STARTUPINFO] = info  # type: ignore
else:
    SUBPROCESS_STARTUP_INFO = None

def empty(_: Any) -> None:
    """Placeholder function."""
    pass

def check_path_inside_minecraft_directory(
    minecraft_directory: str | os.PathLike, path: str | os.PathLike
) -> None:
    """Raise FileOutsideMinecraftDirectory if path is not inside minecraft_directory."""
    abs_dir = os.path.abspath(str(minecraft_directory))
    abs_path = os.path.abspath(str(path))
    if not abs_path.startswith(abs_dir):
        raise FileOutsideMinecraftDirectory(abs_path, abs_dir)

def download_file(
    url: str,
    path: str,
    callback: CallbackDict = {},
    sha1: Optional[str] = None,
    lzma_compressed: bool = False,
    session: Optional[httpx.Client] = None,
    minecraft_directory: Optional[str | os.PathLike] = None,
    overwrite: bool = False,
    retries: int = 3,
    retry_delay: float = 1.0,
) -> bool:
    """
    Download a file to the given path, optionally verifying sha1 and decompressing lzma.
    Retries download up to `retries` times on failure.
    """
    if minecraft_directory is not None:
        check_path_inside_minecraft_directory(minecraft_directory, path)

    if os.path.isfile(path) and not overwrite:
        if sha1 is None or get_sha1_hash(path) == sha1:
            return False

    os.makedirs(os.path.dirname(path), exist_ok=True)
    session = session or httpx.Client()

    for attempt in range(retries):
        try:
            with session.stream("GET", url, headers={"user-agent": get_user_agent()}) as r:
                r.raise_for_status()
                total = int(r.headers.get("Content-Length", 0))
                callback.get("setStatus", empty)(f"Завантаження {os.path.basename(path)}...")
                callback.get("setMax", empty)(total)
                len_chunk = 0
                with open(path, "wb") as f:
                    for chunk in r.iter_bytes(chunk_size=1024 * 10):
                        f.write(chunk)
                        len_chunk += len(chunk)
                        if len_chunk % 2 == 0:
                            callback.get("setProgress", empty)(len_chunk)
                        # callback.get("setProgress", empty)(len_chunk)
            break
        except Exception:
            if attempt < retries - 1:
                time.sleep(retry_delay)
            else:
                raise

    if lzma_compressed:
        with open(path, "rb") as f:
            data = lzma.decompress(f.read())
        with open(path, "wb") as f:
            f.write(data)

    if sha1 is not None:
        checksum = get_sha1_hash(path)
        if checksum != sha1:
            raise InvalidChecksum(url, path, sha1, checksum)

    return True

def parse_single_rule(rule: ClientJsonRule, options: MinecraftOptions) -> bool:
    """Parse a single rule from the versions.json."""
    returnvalue = rule["action"] == "disallow"

    for os_key, os_value in rule.get("os", {}).items():
        if os_key == "name":
            if os_value == "windows" and platform.system() != "Windows":
                return returnvalue
            if os_value == "osx" and platform.system() != "Darwin":
                return returnvalue
            if os_value == "linux" and platform.system() != "Linux":
                return returnvalue
        elif os_key == "arch":
            if os_value == "x86" and platform.architecture()[0] != "32bit":
                return returnvalue
        elif os_key == "version":
            if not re.match(os_value, get_os_version()):
                return returnvalue

    for features_key in rule.get("features", {}):
        if features_key == "has_custom_resolution" and not options.get("customResolution", False):
            return returnvalue
        if features_key == "is_demo_user" and not options.get("demo", False):
            return returnvalue
        if features_key == "has_quick_plays_support" and options.get("quickPlayPath") is None:
            return returnvalue
        if features_key == "is_quick_play_singleplayer" and options.get("quickPlaySingleplayer") is None:
            return returnvalue
        if features_key == "is_quick_play_multiplayer" and options.get("quickPlayMultiplayer") is None:
            return returnvalue
        if features_key == "is_quick_play_realms" and options.get("quickPlayRealms") is None:
            return returnvalue

    return not returnvalue

def parse_rule_list(rules: list[ClientJsonRule], options: MinecraftOptions) -> bool:
    """Parse a list of rules."""
    return all(parse_single_rule(rule, options) for rule in rules)

def _get_lib_name_without_version(lib: ClientJsonLibrary) -> str:
    """Return the library name without the version part."""
    return ":".join(lib["name"].split(":")[:-1])

def inherit_json(original_data: ClientJson, path: str | os.PathLike) -> ClientJson:
    """
    Implement the inheritsFrom function.
    See https://github.com/tomsik68/mclauncher-api/wiki/Version-Inheritance-&-Forge
    """
    inherit_version = original_data["inheritsFrom"]
    inherit_path = os.path.join(path, "versions", inherit_version, f"{inherit_version}.json")
    with open(inherit_path, encoding="utf-8") as f:
        new_data: ClientJson = json.load(f)

    # Merge libraries, avoiding duplicates
    original_libs = {_get_lib_name_without_version(lib): True for lib in original_data.get("libraries", [])}
    lib_list = original_data.get("libraries", [])
    for lib in new_data.get("libraries", []):
        lib_name = _get_lib_name_without_version(lib)
        if lib_name not in original_libs:
            lib_list.append(lib)
    new_data["libraries"] = lib_list

    for key, value in original_data.items():
        if key == "libraries":
            continue
        if isinstance(value, list) and isinstance(new_data.get(key), list):
            new_data[key] = value + new_data[key]  # type: ignore
        elif isinstance(value, dict) and isinstance(new_data.get(key), dict):
            for a, b in value.items():
                if isinstance(b, list):
                    new_data[key][a] = new_data[key][a] + b  # type: ignore
        else:
            new_data[key] = value  # type: ignore

    return new_data

def get_library_path(name: str, path: str | os.PathLike) -> str:
    """Return the path from a library name."""
    libpath = os.path.join(path, "libraries")
    parts = name.split(":")
    base_path, libname, version = parts[0:3]
    for part in base_path.split("."):
        libpath = os.path.join(libpath, part)
    try:
        version, fileend = version.split("@")
    except ValueError:
        fileend = "jar"
    filename = f"{libname}-{version}{''.join(f'-{p}' for p in parts[3:])}.{fileend}"
    return os.path.join(libpath, libname, version, filename)

def get_jar_mainclass(path: str) -> str:
    """Return the main class of a given jar."""
    with zipfile.ZipFile(path) as zf:
        with zf.open("META-INF/MANIFEST.MF") as f:
            lines = f.read().decode("utf-8").splitlines()
    content = {}
    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            content[key.strip()] = value.strip()
    return content["Main-Class"]

def get_sha1_hash(path: str) -> str:
    """Calculate the sha1 checksum of a file."""
    BUF_SIZE = 65536
    sha1 = hashlib.sha1()
    with open(path, "rb") as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha1.update(data)
    return sha1.hexdigest()

def get_os_version() -> str:
    """
    Try to implement System.getProperty("os.version") from Java for use in rules.
    This doesn't work on mac yet.
    """
    if platform.system() == "Windows":
        ver = sys.getwindowsversion()  # type: ignore
        return f"{ver.major}.{ver.minor}"
    elif platform.system() == "Darwin":
        return ""
    else:
        return platform.uname().release

_user_agent_cache: Optional[str] = None

def get_user_agent() -> str:
    """Return the user agent of minecraft-launcher-lib."""
    global _user_agent_cache
    if _user_agent_cache is None:
        _user_agent_cache = f"minecraft-launcher-lib/{__version__}"
    return _user_agent_cache

def get_classpath_separator() -> Literal[":", ";"]:
    """Return the classpath separator for the current OS."""
    return ";" if platform.system() == "Windows" else ":"

_requests_response_cache: dict[str, RequestsResponseCache] = {}

def get_requests_response_cache(url: str) -> httpx.Response:
    """
    Cache the result of httpx.get(). If a request was made to the same URL within the last hour,
    the cache will be used.
    """
    global _requests_response_cache
    cache = _requests_response_cache.get(url)
    if (
        cache is None
        or (datetime.datetime.now() - cache["datetime"]).total_seconds() >= 3600
    ):
        r = httpx.get(url, headers={"user-agent": get_user_agent()})
        if r.status_code == 200:
            _requests_response_cache[url] = {
                "response": r,
                "datetime": datetime.datetime.now(),
            }
        return r
    return cache["response"]

def parse_maven_metadata(url: str) -> MavenMetadata:
    """Parse a maven metadata file."""
    r = get_requests_response_cache(url)
    return {
        "release": re.search(r"(?<=<release>).*?(?=</release>)", r.text).group(),  # type: ignore
        "latest": re.search(r"(?<=<latest>).*?(?=</latest>)", r.text).group(),    # type: ignore
        "versions": re.findall(r"(?<=<version>).*?(?=</version>)", r.text),
    }

def extract_file_from_zip(
    handler: zipfile.ZipFile,
    zip_path: str,
    extract_path: str,
    minecraft_directory: Optional[str | os.PathLike] = None,
) -> None:
    """Extract a file from a zip handler into the given path."""
    if minecraft_directory is not None:
        check_path_inside_minecraft_directory(minecraft_directory, extract_path)
    os.makedirs(os.path.dirname(extract_path), exist_ok=True)
    with handler.open(zip_path, "r") as f, open(extract_path, "wb") as w:
        w.write(f.read())

def assert_func(expression: bool) -> None:
    """
    Drop-in replacement for the assert keyword, which is not available in optimized mode.
    """
    if not expression:
        raise AssertionError()

def get_client_json(version: str, minecraft_directory: str | os.PathLike) -> ClientJson:
    """Load the client.json for the given version."""
    local_path = os.path.join(minecraft_directory, "versions", version, f"{version}.json")
    if os.path.isfile(local_path):
        with open(local_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "inheritsFrom" in data:
            data = inherit_json(data, minecraft_directory)
        return data

    version_list = get_requests_response_cache(
        "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json"
    ).json()
    for i in version_list["versions"]:
        if i["id"] == version:
            return get_requests_response_cache(i["url"]).json()

    raise VersionNotFound(version)
