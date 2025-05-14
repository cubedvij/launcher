# This file is part of minecraft-launcher-lib (https://codeberg.org/JakobDev/minecraft-launcher-lib)
# SPDX-FileCopyrightText: Copyright (c) 2019-2025 JakobDev <jakobdev@gmx.de> and contributors
# SPDX-License-Identifier: BSD-2-Clause

"""
natives contains a function for extracting native libraries to a specific folder
"""

import os
import json
import platform
import zipfile
from typing import Literal
from pathlib import Path

from ._internal_types.shared_types import ClientJson, ClientJsonLibrary
from ._helper import parse_rule_list, inherit_json, get_library_path
from .exceptions import VersionNotFound

__all__ = ["extract_natives"]


def get_natives(data: ClientJsonLibrary) -> str:
    """
    Returns the native part from the json data.
    """
    arch_type = "32" if platform.architecture()[0] == "32bit" else "64"
    natives = data.get("natives", {})

    system_map = {
        "Windows": "windows",
        "Darwin": "osx",
        "Linux": "linux"
    }
    system_key = system_map.get(platform.system())
    if not system_key:
        return ""

    native = natives.get(system_key)
    if native:
        return native.replace("${arch}", arch_type)
    return ""


def extract_natives_file(filename: str, extract_path: str, extract_data: dict[Literal["exclude"], list[str]]) -> None:
    """
    Unpack natives from a zip file, excluding specified files.
    """
    os.makedirs(extract_path, exist_ok=True)

    with zipfile.ZipFile(filename, "r") as zf:
        excludes = set(extract_data.get("exclude", []))
        for member in zf.namelist():
            if not any(member.startswith(e) for e in excludes):
                zf.extract(member, extract_path)


def extract_natives(versionid: str, path: str | os.PathLike, extract_path: str) -> None:
    """
    Extract all native libraries from a version into the given directory.
    The directory will be created if it does not exist.

    :param versionid: The Minecraft version
    :param path: The path to your Minecraft directory
    :param extract_path: The directory to extract natives to
    :raises VersionNotFound: The Minecraft version was not found
    """
    version_json_path = Path(path) / "versions" / versionid / f"{versionid}.json"
    if not version_json_path.is_file():
        raise VersionNotFound(versionid)

    with version_json_path.open("r", encoding="utf-8") as f:
        data: ClientJson = json.load(f)

    if "inheritsFrom" in data:
        data = inherit_json(data, path)

    for lib in data.get("libraries", []):
        # Skip libraries not allowed by rules
        if "rules" in lib and not parse_rule_list(lib["rules"], {}):
            continue

        native = get_natives(lib)
        if not native:
            continue

        current_path = get_library_path(lib["name"], path)
        lib_path, extension = os.path.splitext(current_path)
        native_file = f"{lib_path}-{native}{extension}"
        extract_data = lib.get("extract", {"exclude": []})
        extract_natives_file(native_file, extract_path, extract_data)
