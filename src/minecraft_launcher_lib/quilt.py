# This file is part of minecraft-launcher-lib (https://codeberg.org/JakobDev/minecraft-launcher-lib)
# SPDX-FileCopyrightText: Copyright (c) 2019-2025 JakobDev <jakobdev@gmx.de> and contributors
# SPDX-License-Identifier: BSD-2-Clause
"""
quilt contains functions for dealing with the `Quilt modloader <https://quiltmc.org>`_.

You may have noticed, that the Functions are the same as in the :doc:`fabric` module.
That's because Quilt is a Fork of Fabric. This module behaves exactly the same as the fabric module.
"""
import json
import os
import subprocess
import tempfile

from ._helper import (
    SUBPROCESS_STARTUP_INFO,
    download_file,
    empty,
    get_requests_response_cache,
    parse_maven_metadata,
)
from ._internal_types.shared_types import ClientJson
from .exceptions import ExternalProgramError, UnsupportedVersion, VersionNotFound
from .install import install_minecraft_version
from .runtime import get_executable_path
from .types import CallbackDict, QuiltLoader, QuiltMinecraftVersion
from .utils import is_version_valid

QUILT_MINECRAFT_VERSIONS_URL = "https://meta.quiltmc.org/v3/versions/game"
QUILT_LOADER_VERSIONS_URL = "https://meta.quiltmc.org/v3/versions/loader"
QUILT_INSTALLER_MAVEN_URL = (
    "https://maven.quiltmc.org/repository/release/org/quiltmc/quilt-installer/maven-metadata.xml"
)


def get_all_minecraft_versions() -> list[QuiltMinecraftVersion]:
    """Returns all available Minecraft Versions for Quilt."""
    return get_requests_response_cache(QUILT_MINECRAFT_VERSIONS_URL).json()


def get_stable_minecraft_versions() -> list[str]:
    """Returns a list of stable Minecraft versions that support Quilt."""
    return [v["version"] for v in get_all_minecraft_versions() if v.get("stable")]


def get_latest_minecraft_version() -> str:
    """Returns the latest (possibly unstable) Minecraft version that supports Quilt."""
    versions = get_all_minecraft_versions()
    return versions[0]["version"] if versions else ""


def get_latest_stable_minecraft_version() -> str:
    """Returns the latest stable Minecraft version that supports Quilt."""
    stable_versions = get_stable_minecraft_versions()
    return stable_versions[0] if stable_versions else ""


def is_minecraft_version_supported(version: str) -> bool:
    """Checks if a Minecraft version is supported by Quilt."""
    return any(v["version"] == version for v in get_all_minecraft_versions())


def get_all_loader_versions() -> list[QuiltLoader]:
    """Returns all loader versions."""
    return get_requests_response_cache(QUILT_LOADER_VERSIONS_URL).json()


def get_latest_loader_version() -> str:
    """Returns the latest loader version."""
    loader_versions = get_all_loader_versions()
    return loader_versions[0]["version"] if loader_versions else ""


def get_latest_installer_version() -> str:
    """Returns the latest installer version."""
    return parse_maven_metadata(QUILT_INSTALLER_MAVEN_URL).get("latest", "")


def install_quilt(
    minecraft_version: str,
    minecraft_directory: str | os.PathLike,
    loader_version: str | None = None,
    callback: CallbackDict | None = None,
    java: str | os.PathLike | None = None,
) -> None:
    """
    Installs the Quilt modloader.

    :param minecraft_version: A vanilla version that is supported by Quilt
    :param minecraft_directory: The path to your Minecraft directory
    :param loader_version: The Quilt loader version. If not given it will use the latest
    :param callback: The same dict as for :func:`~minecraft_launcher_lib.install.install_minecraft_version`
    :param java: A Path to a custom Java executable
    :raises VersionNotFound: The given Minecraft does not exist
    :raises UnsupportedVersion: The given Minecraft version is not supported by Quilt
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

    # Make sure the Minecraft version is installed
    install_minecraft_version(minecraft_version, path, callback=callback)

    # Get installer version and download installer
    installer_version = get_latest_installer_version()
    installer_download_url = (
        f"https://maven.quiltmc.org/repository/release/org/quiltmc/quilt-installer/"
        f"{installer_version}/quilt-installer-{installer_version}.jar"
    )

    with tempfile.TemporaryDirectory(prefix="minecraft-launcher-lib-quilt-install-") as tempdir:
        installer_path = os.path.join(tempdir, "quilt-installer.jar")
        download_file(installer_download_url, installer_path, callback=callback, overwrite=True)

        # Run the installer
        callback.get("setStatus", empty)("Встановлення Quilt...")
        version_json_path = os.path.join(path, "versions", minecraft_version, f"{minecraft_version}.json")
        with open(version_json_path, "r", encoding="utf-8") as f:
            versiondata: ClientJson = json.load(f)
        java_exec = java or get_executable_path(versiondata["javaVersion"]["component"], path)
        command = [
            java_exec,
            "-jar",
            installer_path,
            "install",
            "client",
            minecraft_version,
            loader_version,
            f"--install-dir={path}",
            "--no-profile",
        ]
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=SUBPROCESS_STARTUP_INFO,
        )
        if result.returncode != 0:
            raise ExternalProgramError(command, result.stdout, result.stderr)

    # Install all libs of quilt
    quilt_minecraft_version = f"quilt-loader-{loader_version}-{minecraft_version}"
    install_minecraft_version(quilt_minecraft_version, path, callback=callback)
