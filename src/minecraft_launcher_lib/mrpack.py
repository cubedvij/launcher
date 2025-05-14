# This file is part of minecraft-launcher-lib (https://codeberg.org/JakobDev/minecraft-launcher-lib)
# SPDX-FileCopyrightText: Copyright (c) 2019-2025 JakobDev <jakobdev@gmx.de> and contributors
# SPDX-License-Identifier: BSD-2-Clause
"""
mrpack allows you to install Modpacks from the `Mrpack Format <https://support.modrinth.com/en/articles/8802351-modrinth-modpack-format-mrpack>`_.
You should also take a look at the :doc:`complete example </examples/Mrpack>`.
"""
import json
import os
import zipfile

import httpx

from ._helper import check_path_inside_minecraft_directory, download_file, empty
from ._internal_types.mrpack_types import MrpackFile, MrpackIndex
from .exceptions import VersionNotFound
from .fabric import install_fabric
from .forge import install_forge_version
from .install import install_minecraft_version
from .quilt import install_quilt
from .types import CallbackDict, MrpackInformation, MrpackInstallOptions


def _filter_mrpack_files(file_list: list[MrpackFile], options: MrpackInstallOptions) -> list[MrpackFile]:
    """
    Gets all Mrpack Files that should be installed.
    """
    filtered = []
    optional_files = options.get("optionalFiles", [])
    for file in file_list:
        env = file.get("env")
        if not env:
            filtered.append(file)
            continue
        client_env = env.get("client")
        if client_env == "required":
            filtered.append(file)
        elif client_env == "optional" and file["path"] in optional_files:
            filtered.append(file)
    return filtered


def get_mrpack_information(path: str | os.PathLike) -> MrpackInformation:
    """
    Gets some Information from a .mrpack file.
    """
    with zipfile.ZipFile(path, "r") as zf, zf.open("modrinth.index.json", "r") as f:
        index: MrpackIndex = json.load(f)
        info: MrpackInformation = {
            "name": index["name"],
            "summary": index.get("summary", ""),
            "versionId": index["versionId"],
            "formatVersion": index["formatVersion"],
            "minecraftVersion": index["dependencies"]["minecraft"],
            "optionalFiles": [
                file["path"]
                for file in index["files"]
                if file.get("env", {}).get("client") == "optional"
            ],
        }
        return info


def install_mrpack(
    path: str | os.PathLike,
    minecraft_directory: str | os.PathLike,
    modpack_directory: str | os.PathLike | None = None,
    callback: CallbackDict | None = None,
    mrpack_install_options: MrpackInstallOptions | None = None,
) -> None:
    """
    Installs a .mrpack file.
    """
    minecraft_directory = os.path.abspath(minecraft_directory)
    path = os.path.abspath(path)
    modpack_directory = os.path.abspath(modpack_directory) if modpack_directory else minecraft_directory
    callback = callback or {}
    mrpack_install_options = mrpack_install_options or {}

    with zipfile.ZipFile(path, "r") as zf, zf.open("modrinth.index.json", "r") as f:
        index: MrpackIndex = json.load(f)

        # Download the files
        callback.get("setStatus", empty)("Download mrpack files")
        file_list = _filter_mrpack_files(index["files"], mrpack_install_options)
        callback.get("setMax", empty)(len(file_list))
        for count, file in enumerate(file_list):
            full_path = os.path.abspath(os.path.join(modpack_directory, file["path"]))
            check_path_inside_minecraft_directory(modpack_directory, full_path)
            download_file(file["downloads"][0], full_path, sha1=file["hashes"]["sha1"], callback=callback)
            callback.get("setProgress", empty)(count + 1)

        # Extract the overrides
        callback.get("setStatus", empty)("Extract overrides")
        for zip_name in zf.namelist():
            if (
                not (zip_name.startswith("overrides/") or zip_name.startswith("client-overrides/"))
                or zf.getinfo(zip_name).file_size == 0
            ):
                continue

            prefix = "client-overrides/" if zip_name.startswith("client-overrides/") else "overrides/"
            file_name = zip_name[len(prefix):]
            full_path = os.path.abspath(os.path.join(modpack_directory, file_name))
            check_path_inside_minecraft_directory(modpack_directory, full_path)
            callback.get("setStatus", empty)(f"Extract {zip_name}]")
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "wb") as f_out:
                f_out.write(zf.read(zip_name))

        if mrpack_install_options.get("skipDependenciesInstall"):
            return

        # Install dependencies
        mc_version = index["dependencies"]["minecraft"]
        callback.get("setStatus", empty)(f"Installing Minecraft {mc_version}")
        install_minecraft_version(mc_version, minecraft_directory, callback=callback)

        # Forge
        if "forge" in index["dependencies"]:
            forge_version = None
            forge_base = index["dependencies"]["forge"]
            forge_candidates = [
                f"{mc_version}-{forge_base}",
                f"{mc_version}-{forge_base}-{mc_version}",
            ]
            FORGE_URL = "https://maven.minecraftforge.net/net/minecraftforge/forge/{version}/forge-{version}-installer.jar"
            for candidate in forge_candidates:
                url = FORGE_URL.format(version=candidate)
                if httpx.head(url).status_code == 200:
                    forge_version = candidate
                    break
            if not forge_version:
                raise VersionNotFound(forge_base)
            callback.get("setStatus", empty)(f"Installing Forge {forge_version}")
            install_forge_version(forge_version, minecraft_directory, callback=callback)

        # Fabric
        if "fabric-loader" in index["dependencies"]:
            fabric_loader = index["dependencies"]["fabric-loader"]
            callback.get("setStatus", empty)(
                f"Installing Fabric {fabric_loader} for Minecraft {mc_version}"
            )
            install_fabric(mc_version, minecraft_directory, loader_version=fabric_loader, callback=callback)

        # Quilt
        if "quilt-loader" in index["dependencies"]:
            quilt_loader = index["dependencies"]["quilt-loader"]
            callback.get("setStatus", empty)(
                f"Installing Quilt {quilt_loader} for Minecraft {mc_version}"
            )
            install_quilt(mc_version, minecraft_directory, loader_version=quilt_loader, callback=callback)


def get_mrpack_launch_version(path: str | os.PathLike) -> str:
    """
    Returns the version that needs to be used with :func:`~minecraft_launcher_lib.command.get_minecraft_command`.
    """
    with zipfile.ZipFile(path, "r") as zf, zf.open("modrinth.index.json", "r") as f:
        index: MrpackIndex = json.load(f)
        deps = index["dependencies"]
        mc_version = deps["minecraft"]
        if "forge" in deps:
            return f"{mc_version}-forge-{deps['forge']}"
        if "fabric-loader" in deps:
            return f"fabric-loader-{deps['fabric-loader']}-{mc_version}"
        if "quilt-loader" in deps:
            return f"quilt-loader-{deps['quilt-loader']}-{mc_version}"
        return mc_version
