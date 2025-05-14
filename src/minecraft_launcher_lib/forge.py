# This file is part of minecraft-launcher-lib (https://codeberg.org/JakobDev/minecraft-launcher-lib)
# SPDX-FileCopyrightText: Copyright (c) 2019-2025 JakobDev <jakobdev@gmx.de> and contributors
# SPDX-License-Identifier: BSD-2-Clause

"""
.. note::
    Before using this module, please read this comment from the forge developers:

    .. code:: text

        Please do not automate the download and installation of Forge.
        Our efforts are supported by ads from the download page.
        If you MUST automate this, please consider supporting the project through https://www.patreon.com/LexManos/

    It's your choice, if you want to respect that and support forge.

forge contains functions for dealing with the Forge modloader
"""

import json
import os
import subprocess
import tempfile
import zipfile
from typing import List, Optional, Union

from ._helper import (
    SUBPROCESS_STARTUP_INFO,
    download_file,
    empty,
    extract_file_from_zip,
    get_classpath_separator,
    get_jar_mainclass,
    get_library_path,
    parse_maven_metadata,
)
from ._internal_types.forge_types import ForgeInstallProfile
from ._internal_types.shared_types import ClientJson
from .exceptions import VersionNotFound
from .install import install_libraries, install_minecraft_version
from .runtime import get_executable_path
from .types import CallbackDict

__all__ = [
    "install_forge_version",
    "run_forge_installer",
    "list_forge_versions",
    "find_forge_version",
    "is_forge_version_valid",
    "supports_automatic_install",
    "forge_to_installed_version",
]

FORGE_DOWNLOAD_URL = "https://maven.minecraftforge.net/net/minecraftforge/forge/{version}/forge-{version}-installer.jar"
MAVEN_METADATA_URL = (
    "https://maven.minecraftforge.net/net/minecraftforge/forge/maven-metadata.xml"
)


def _extract_optional_files(
    zf: zipfile.ZipFile,
    versionid: str,
    forge_lib_path: str,
    minecraft_directory: Union[str, os.PathLike],
) -> None:
    """Extract optional Forge jars from the installer."""
    extract_targets = [
        (
            f"maven/net/minecraftforge/forge/{versionid}/forge-{versionid}-universal.jar",
            os.path.join(forge_lib_path, f"forge-{versionid}-universal.jar"),
        ),
        (
            f"forge-{versionid}-universal.jar",
            os.path.join(forge_lib_path, f"forge-{versionid}.jar"),
        ),
        (
            f"maven/net/minecraftforge/forge/{versionid}/forge-{versionid}.jar",
            os.path.join(forge_lib_path, f"forge-{versionid}.jar"),
        ),
    ]
    for src, dst in extract_targets:
        try:
            extract_file_from_zip(zf, src, dst, minecraft_directory=minecraft_directory)
        except KeyError:
            continue


def forge_processors(
    data: ForgeInstallProfile,
    minecraft_directory: Union[str, os.PathLike],
    lzma_path: str,
    installer_path: str,
    callback: CallbackDict,
    java: str,
) -> None:
    """
    Run the processors of the install_profile.json
    """
    mc_dir = str(minecraft_directory)
    argument_vars = {
        "{MINECRAFT_JAR}": os.path.join(
            mc_dir, "versions", data["minecraft"], f"{data['minecraft']}.jar"
        )
    }
    for key, value in data["data"].items():
        if value["client"].startswith("[") and value["client"].endswith("]"):
            argument_vars[f"{{{key}}}"] = get_library_path(
                value["client"][1:-1], mc_dir
            )
        else:
            argument_vars[f"{{{key}}}"] = value["client"]

    with tempfile.TemporaryDirectory() as root_path:
        argument_vars.update(
            {
                "{INSTALLER}": installer_path,
                "{BINPATCH}": lzma_path,
                "{ROOT}": root_path,
                "{SIDE}": "client",
            }
        )

        classpath_sep = get_classpath_separator()
        processors = data.get("processors", [])
        callback.get("setMax", empty)(len(processors))
        callback.get("setStatus", empty)(
            "Встановлення Forge..."
        )
        for count, proc in enumerate(processors):
            if "client" not in proc.get("sides", ["client"]):
                continue  # Skip server-side only processors

            classpath = (
                classpath_sep.join(
                    [get_library_path(c, mc_dir) for c in proc["classpath"]]
                )
                + classpath_sep
                + get_library_path(proc["jar"], mc_dir)
            )
            mainclass = get_jar_mainclass(get_library_path(proc["jar"], mc_dir))
            command = [java, "-cp", classpath, mainclass]

            for arg in proc["args"]:
                var = argument_vars.get(arg, arg)
                if var.startswith("[") and var.endswith("]"):
                    command.append(get_library_path(var[1:-1], mc_dir))
                else:
                    command.append(var)

            # Replace argument variables in command
            for key, val in argument_vars.items():
                command = [c.replace(key, val) for c in command]

            subprocess.run(command, startupinfo=SUBPROCESS_STARTUP_INFO)
            callback.get("setProgress", empty)(count)


def install_forge_version(
    versionid: str,
    path: Union[str, os.PathLike],
    callback: Optional[CallbackDict] = None,
) -> None:
    """
    Installs the given Forge version

    :param versionid: A Forge Version. You can get a List of Forge versions using :func:`list_forge_versions`
    :param path: The path to your Minecraft directory
    :param callback: The same dict as for :func:`~minecraft_launcher_lib.install.install_minecraft_version`

    Raises a :class:`~minecraft_launcher_lib.exceptions.VersionNotFound` exception when the given forge version is not found
    """
    callback = callback or {}

    with tempfile.TemporaryDirectory(
        prefix="minecraft-launcher-lib-forge-install-"
    ) as tempdir:
        installer_path = os.path.join(tempdir, "installer.jar")

        if not download_file(
            FORGE_DOWNLOAD_URL.format(version=versionid), installer_path
        ):
            raise VersionNotFound(versionid)

        with zipfile.ZipFile(installer_path, "r") as zf:
            # Read the install_profile.json
            with zf.open("install_profile.json", "r") as f:
                version_data: ForgeInstallProfile = json.load(f)

            forge_version_id = version_data.get(
                "version", version_data["version"]
            )
            minecraft_version = version_data.get(
                "minecraft", version_data["minecraft"]
            )

            # Ensure base version is installed
            install_minecraft_version(minecraft_version, path, callback=callback)

            # Install libraries
            if "libraries" in version_data:
                install_libraries(
                    minecraft_version, version_data["libraries"], str(path), callback
                )

            # Extract the client.json
            version_json_path = os.path.join(
                path, "versions", forge_version_id, f"{forge_version_id}.json"
            )
            try:
                extract_file_from_zip(
                    zf, "version.json", version_json_path, minecraft_directory=path
                )
            except KeyError:
                if "versionInfo" in version_data:
                    with open(version_json_path, "w", encoding="utf-8") as f:
                        json.dump(
                            version_data["versionInfo"], f, ensure_ascii=False, indent=4
                        )

            # Extract forge jars
            forge_lib_path = os.path.join(
                path, "libraries", "net", "minecraftforge", "forge", versionid
            )
            _extract_optional_files(zf, versionid, forge_lib_path, path)

            # Extract the client.lzma
            lzma_path = os.path.join(tempdir, "client.lzma")
            try:
                extract_file_from_zip(zf, "data/client.lzma", lzma_path)
            except KeyError:
                pass

        # Install the rest with the vanilla function
        install_minecraft_version(forge_version_id, path, callback=callback)

        # Run the processors
        if "processors" in version_data:
            with open(
                os.path.join(
                    path, "versions", minecraft_version, f"{minecraft_version}.json"
                ),
                "r",
                encoding="utf-8",
            ) as f:
                versiondata: ClientJson = json.load(f)
            java_path = get_executable_path(
                versiondata["javaVersion"]["component"], path
            )
            forge_processors(
                version_data, path, lzma_path, installer_path, callback, java_path
            )


def run_forge_installer(
    version: str, java: Optional[Union[str, os.PathLike]] = None
) -> None:
    """
    Run the forge installer of the given forge version

    :param version: A Forge Version. You can get a List of Forge versions using :func:`list_forge_versions`
    :param java: A Path to a custom Java executable
    """
    with tempfile.TemporaryDirectory(
        prefix="minecraft-launcher-lib-forge-installer-"
    ) as tempdir:
        installer_path = os.path.join(tempdir, "installer.jar")

        if not download_file(
            FORGE_DOWNLOAD_URL.format(version=version),
            installer_path,
            {},
            overwrite=True,
        ):
            raise VersionNotFound(version)

        subprocess.run(
            [str(java) if java else "java", "-jar", installer_path],
            check=True,
            cwd=tempdir,
            startupinfo=SUBPROCESS_STARTUP_INFO,
        )


def list_forge_versions() -> List[str]:
    """
    Returns a list of all forge versions
    """
    return parse_maven_metadata(MAVEN_METADATA_URL)["versions"]


def find_forge_version(vanilla_version: str) -> Optional[str]:
    """
    Find the latest forge version that is compatible to the given vanilla version

    :param vanilla_version: A vanilla Minecraft version
    """
    for version in list_forge_versions():
        if version.split("-")[0] == vanilla_version:
            return version
    return None


def is_forge_version_valid(forge_version: str) -> bool:
    """
    Checks if a forge version is valid

    :param forge_version: A Forge Version
    """
    return forge_version in list_forge_versions()


def supports_automatic_install(forge_version: str) -> bool:
    """
    Checks if install_forge_version() supports the given forge version

    :param forge_version: A Forge Version
    """
    try:
        vanilla_version, _ = forge_version.split("-")
        version_number = int(vanilla_version.split(".")[1])
        return version_number >= 13
    except Exception:
        return False


def forge_to_installed_version(forge_version: str) -> str:
    """
    Returns the Version under which Forge will be installed from the given Forge version.

    :param forge_version: A Forge Version

    Raises a ValueError if the Version is invalid.
    """
    try:
        vanilla_part, forge_part = forge_version.split("-")
        return f"{vanilla_part}-forge-{forge_part}"
    except ValueError:
        raise ValueError(f"{forge_version} is not a valid forge version") from None
