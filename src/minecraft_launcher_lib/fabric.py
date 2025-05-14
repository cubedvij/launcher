# This file is part of minecraft-launcher-lib (https://codeberg.org/JakobDev/minecraft-launcher-lib)
# SPDX-FileCopyrightText: Copyright (c) 2019-2025 JakobDev <jakobdev@gmx.de> and contributors
# SPDX-License-Identifier: BSD-2-Clause
"""fabric contains functions for dealing with the `Fabric modloader <https://fabricmc.net/>`_."""

import json
import os
import subprocess
import tempfile

from ._helper import (
    download_file,
    empty,
    get_requests_response_cache,
    parse_maven_metadata,
)
from ._internal_types.shared_types import ClientJson
from .exceptions import ExternalProgramError, UnsupportedVersion, VersionNotFound
from .install import install_minecraft_version
from .runtime import get_executable_path
from .types import CallbackDict, FabricLoader, FabricMinecraftVersion
from .utils import is_version_valid

FABRIC_MINECRAFT_VERSIONS_URL = "https://meta.fabricmc.net/v2/versions/game"
FABRIC_LOADER_VERSIONS_URL = "https://meta.fabricmc.net/v2/versions/loader"
FABRIC_INSTALLER_MAVEN_URL = "https://maven.fabricmc.net/net/fabricmc/fabric-installer/maven-metadata.xml"


def get_all_minecraft_versions() -> list[FabricMinecraftVersion]:
    """Returns all available Minecraft Versions for Fabric."""
    return get_requests_response_cache(FABRIC_MINECRAFT_VERSIONS_URL).json()


def get_stable_minecraft_versions() -> list[str]:
    """Returns a list of stable Minecraft versions that support Fabric."""
    return [v["version"] for v in get_all_minecraft_versions() if v.get("stable")]


def get_latest_minecraft_version() -> str:
    """Returns the latest (possibly unstable) Minecraft version that supports Fabric."""
    versions = get_all_minecraft_versions()
    return versions[0]["version"] if versions else ""


def get_latest_stable_minecraft_version() -> str:
    """Returns the latest stable Minecraft version that supports Fabric."""
    stable_versions = get_stable_minecraft_versions()
    return stable_versions[0] if stable_versions else ""


def is_minecraft_version_supported(version: str) -> bool:
    """Checks if a Minecraft version is supported by Fabric."""
    return any(v["version"] == version for v in get_all_minecraft_versions())


def get_all_loader_versions() -> list[FabricLoader]:
    """Returns all Fabric loader versions."""
    return get_requests_response_cache(FABRIC_LOADER_VERSIONS_URL).json()


def get_latest_loader_version() -> str:
    """Returns the latest Fabric loader version."""
    versions = get_all_loader_versions()
    return versions[0]["version"] if versions else ""


def get_latest_installer_version() -> str:
    """Returns the latest Fabric installer version."""
    return parse_maven_metadata(FABRIC_INSTALLER_MAVEN_URL).get("latest", "")


def install_fabric(
    minecraft_version: str,
    minecraft_directory: str | os.PathLike,
    loader_version: str | None = None,
    callback: CallbackDict | None = None,
    java: str | os.PathLike | None = None,
) -> None:
    """
    Installs the Fabric modloader.
    :param minecraft_version: A vanilla version that is supported by Fabric
    :param minecraft_directory: The path to your Minecraft directory
    :param loader_version: The fabric loader version. If not given it will use the latest
    :param callback: The same dict as for :func:`~minecraft_launcher_lib.install.install_minecraft_version`
    :param java: A Path to a custom Java executable
    :raises VersionNotFound: The given Minecraft does not exist
    :raises UnsupportedVersion: The given Minecraft version is not supported by Fabric
    """
    path = str(minecraft_directory)
    callback = callback or {}

    # Check if the given version exists and is supported
    if not is_version_valid(minecraft_version, minecraft_directory):
        raise VersionNotFound(minecraft_version)
    if not is_minecraft_version_supported(minecraft_version):
        raise UnsupportedVersion(minecraft_version)

    # Get latest loader version if not given
    loader_version = loader_version or get_latest_loader_version()

    # Ensure the Minecraft version is installed
    install_minecraft_version(minecraft_version, path, callback=callback)

    # Prepare installer
    installer_version = get_latest_installer_version()
    installer_url = (
        f"https://maven.fabricmc.net/net/fabricmc/fabric-installer/"
        f"{installer_version}/fabric-installer-{installer_version}.jar"
    )

    with tempfile.TemporaryDirectory(prefix="minecraft-launcher-lib-fabric-install-") as tempdir:
        installer_path = os.path.join(tempdir, "fabric-installer.jar")
        download_file(installer_url, installer_path, callback=callback, overwrite=True)

        callback.get("setStatus", empty)("Встановлення Fabric...")

        version_json_path = os.path.join(path, "versions", minecraft_version, f"{minecraft_version}.json")
        with open(version_json_path, "r", encoding="utf-8") as f:
            versiondata: ClientJson = json.load(f)
        java_exec = java or get_executable_path(versiondata["javaVersion"]["component"], path)

        command = [
            java_exec,
            "-jar",
            installer_path,
            "client",
            "-dir",
            path,
            "-mcversion",
            minecraft_version,
            "-loader",
            loader_version,
            "-noprofile",
            "-snapshot",
        ]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            raise ExternalProgramError(command, result.stdout, result.stderr)

    # Install all Fabric libraries
    fabric_version = f"fabric-loader-{loader_version}-{minecraft_version}"
    install_minecraft_version(fabric_version, path, callback=callback)
