# This file is part of minecraft-launcher-lib (https://codeberg.org/JakobDev/minecraft-launcher-lib)
# SPDX-FileCopyrightText: Copyright (c) 2019-2025 JakobDev <jakobdev@gmx.de> and contributors
# SPDX-License-Identifier: BSD-2-Clause

"""java_utils contains some functions to help with Java"""

import os
import platform
import re
import subprocess

from ._helper import SUBPROCESS_STARTUP_INFO
from .types import JavaInformation


def get_java_information(path: str | os.PathLike) -> JavaInformation:
    """
    Returns information about the given Java installation.

    :param path: Path to the Java installation directory.
    :return: A dict with information about the Java installation.
    :raises ValueError: If the Java executable is not found.
    """
    system = platform.system()
    java_exec = "java.exe" if system == "Windows" else "java"
    java_path = os.path.join(path, "bin", java_exec)

    if not os.path.isfile(java_path):
        raise ValueError(f"{os.path.abspath(java_path)} was not found")

    result = subprocess.run(
        [java_path, "-showversion"],
        capture_output=True,
        text=True,
        startupinfo=SUBPROCESS_STARTUP_INFO,
    )
    lines = result.stderr.splitlines()
    if not lines:
        raise ValueError("Could not retrieve Java version information.")

    version_match = re.search(r'(?<=version ")[\d._]+(?=")', lines[0])
    if not version_match:
        raise ValueError("Could not parse Java version.")

    information: JavaInformation = {
        "path": str(path),
        "name": os.path.basename(path),
        "version": version_match.group(),
        "is_64bit": "64-Bit" in lines[2] if len(lines) > 2 else False,
        "openjdk": lines[0].startswith("openjdk"),
        "java_path": os.path.abspath(java_path),
        "javaw_path": (
            os.path.join(os.path.abspath(path), "bin", "javaw.exe")
            if system == "Windows"
            else None
        ),
    }
    return information


def _search_java_directory(path: str | os.PathLike) -> list[str]:
    """Helper to find Java installations in a directory."""
    if not os.path.isdir(path):
        return []

    java_dirs = []
    for entry in os.listdir(path):
        current = os.path.join(path, entry)
        if not os.path.isdir(current):
            continue
        if (
            os.path.isfile(os.path.join(current, "bin", "java"))
            or os.path.isfile(os.path.join(current, "bin", "java.exe"))
        ):
            java_dirs.append(current)
    return java_dirs


def find_system_java_versions(
    additional_directories: list[str | os.PathLike] | None = None,
) -> list[str]:
    """
    Finds all Java installations on the system.

    :param additional_directories: Additional directories to search.
    :return: List of Java installation directories.
    """
    java_dirs: list[str] = []
    system = platform.system()

    if system == "Windows":
        java_dirs += _search_java_directory(r"C:\Program Files (x86)\Java")
        java_dirs += _search_java_directory(r"C:\Program Files\Java")
    elif system == "Linux":
        java_dirs += _search_java_directory("/usr/lib/jvm")
        java_dirs += _search_java_directory("/usr/lib/sdk")

    if additional_directories:
        for directory in additional_directories:
            java_dirs += _search_java_directory(directory)

    return java_dirs


def find_system_java_versions_information(
    additional_directories: list[str | os.PathLike] | None = None,
) -> list[JavaInformation]:
    """
    Finds all Java installations and returns their information.

    :param additional_directories: Additional directories to search.
    :return: List of JavaInformation dicts.
    """
    return [
        get_java_information(path)
        for path in find_system_java_versions(additional_directories)
    ]
