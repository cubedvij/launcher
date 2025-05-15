# This file is part of minecraft-launcher-lib (https://codeberg.org/JakobDev/minecraft-launcher-lib)
# SPDX-FileCopyrightText: Copyright (c) 2019-2025 JakobDev <jakobdev@gmx.de> and contributors
# SPDX-License-Identifier: BSD-2-Clause

"""
runtime allows to install the java runtime. This module is used by :func:`~minecraft_launcher_lib.install.install_minecraft_version`,
so you don't need to use it in your code most of the time.
"""

import os
import platform
import shutil
import zipfile
from pathlib import Path

import httpx

from ._helper import (
    check_path_inside_minecraft_directory,
    download_file,
    get_client_json,
    get_user_agent,
)
from .exceptions import PlatformNotSupported, VersionNotFound
from .types import CallbackDict, VersionRuntimeInformation

# Azul Zulu API endpoint
AZUL_API = "https://api.azul.com/metadata/v1/zulu/packages"


def _get_jvm_platform_string() -> str:
    """Get the name that is used to identify the platform."""
    system = platform.system()
    arch = platform.architecture()[0]
    machine = platform.machine()

    if system == "Windows":
        return "windows-x86" if arch == "32bit" else "windows-x64"
    if system == "Linux":
        return "linux-i386" if arch == "32bit" else "linux"
    if system == "Darwin":
        return "mac-os-arm64" if machine == "arm64" else "mac-os"
    return "gamecore"


def get_installed_jvm_runtimes(minecraft_directory: str | os.PathLike) -> list[str]:
    """
    Returns a list of all installed jvm runtimes.
    """
    runtime_dir = os.path.join(minecraft_directory, "runtime")
    try:
        return os.listdir(runtime_dir)
    except FileNotFoundError:
        return []


def install_jvm_runtime(
    jvm_version: str,
    jvm_mojang_name: str,
    minecraft_directory: str | os.PathLike,
    callback: CallbackDict | None = None,
) -> None:
    """
    Installs the given jvm runtime from Azul Zulu (Azul) as a JRE.
    """

    callback = callback or {}

    # Map platform to Azul Zulu API params
    system = platform.system()
    arch = platform.machine().lower()
    if system == "Windows":
        os_name = "windows"
    elif system == "Linux":
        os_name = "linux"
    elif system == "Darwin":
        os_name = "macos"
    else:
        raise PlatformNotSupported(f"Unsupported OS: {system}")

    # Azul arch mapping
    if arch in ("x86_64", "amd64", "x64"):
        arch_name = "x64"
    else:
        raise PlatformNotSupported(f"Unsupported architecture: {arch}")

    # Query Azul Zulu API for the latest JRE with the requested major version
    params = {
        "java_version": jvm_version,
        "os": os_name,
        "arch": arch_name,
        "archive_type": "zip",
        "java_package_type": "jre",
        "release_status": "ga",
        "latest": "true",
        "features": "",
        "hw_bitness": "64",
        "bundle_type": "jre",
        "certification": "tck",
        "fx": "false",
    }
    resp = httpx.get(AZUL_API, params=params, headers={"user-agent": get_user_agent()})
    resp.raise_for_status()
    pkgs = resp.json()
    if not pkgs:
        raise VersionNotFound(
            f"No Azul Zulu JRE found for version {jvm_version} on {os_name} {arch_name}"
        )
    pkg = pkgs[0]
    download_url = pkg["download_url"]
    version_name = pkg["java_version"][0]
    filename = download_url.split("/")[-1]

    # Prepare destination
    base_path = Path(minecraft_directory) / "runtime" / jvm_mojang_name
    os.makedirs(base_path, exist_ok=True)
    archive_path = base_path / filename

    # Clean up old version if exists
    if archive_path.is_file():
        archive_path.unlink(missing_ok=True)
    if base_path.is_dir():
        shutil.rmtree(base_path, ignore_errors=True)
        os.makedirs(base_path, exist_ok=True)

    # Download archive
    download_file(download_url, str(archive_path), callback=callback)

    # Extract archive
    with zipfile.ZipFile(archive_path, "r") as zf:
        zf.extractall(base_path)

    # Optionally move contents up if Azul puts them in a subdir
    extracted_dirs = [d for d in base_path.iterdir() if d.is_dir()]
    if len(extracted_dirs) == 1:
        for item in extracted_dirs[0].iterdir():
            shutil.move(str(item), str(base_path))
        extracted_dirs[0].rmdir()

    # Clean up
    archive_path.unlink(missing_ok=True)
    # Write .version file
    version_path = Path(minecraft_directory) / "runtime" / jvm_mojang_name / ".version"
    check_path_inside_minecraft_directory(minecraft_directory, str(version_path))
    with open(version_path, "w", encoding="utf-8") as f:
        f.write(str(version_name))

    # make java executable (linux)
    if system == "Linux":
        # make all files executable 
        for root, _, files in os.walk(base_path):
            # Skip if the file is already executable
            for file in files:
                file_path = os.path.join(root, file)
                if os.access(file_path, os.X_OK):
                    continue
                try:
                    os.chmod(file_path, 0o755)
                except PermissionError:
                    pass
        


def get_executable_path(
    jvm_version: str, minecraft_directory: str | os.PathLike
) -> str | None:
    """
    Returns the path to the executable. Returns None if none is found.
    """
    base = os.path.join(minecraft_directory, "runtime", jvm_version)
    java_path = os.path.join(base, "bin", "java")
    if os.path.isfile(java_path):
        return java_path
    if os.path.isfile(java_path + ".exe"):
        return java_path + ".exe"
    alt_path = os.path.join(base, "jre.bundle", "Contents", "Home", "bin", "java")
    if os.path.isfile(alt_path):
        return alt_path
    return None


def get_version_runtime_information(
    version: str, minecraft_directory: str | os.PathLike
) -> VersionRuntimeInformation | None:
    """
    Returns information about the runtime used by a version.
    """
    data = get_client_json(version, minecraft_directory)
    java_version = data.get("javaVersion")
    if not java_version:
        return None
    return {
        "name": java_version["component"],
        "javaMajorVersion": java_version["majorVersion"],
    }
