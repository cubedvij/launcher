import json
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

import httpx

from ._helper import (
    check_path_inside_minecraft_directory,
    download_file,
    empty,
    get_user_agent,
    parse_rule_list,
)
from ._internal_types.install_types import AssetsJson
from ._internal_types.shared_types import ClientJson, ClientJsonLibrary
from .exceptions import VersionNotFound
from .natives import extract_natives_file, get_natives
from .runtime import install_jvm_runtime
from .types import CallbackDict

__all__ = ["install_minecraft_version"]


def _set_callback(callback: CallbackDict, key: str, *args) -> None:
    callback.get(key, empty)(*args)


def _download_and_extract_native(
    lib_info: ClientJsonLibrary,
    libraries_path: Path,
    jar_filename_native: str,
    version_id: str,
    base_path: Path,
) -> None:
    classifiers = lib_info["downloads"].get("classifiers")
    if not classifiers:
        return
    native_key = get_natives(lib_info)
    native_info = classifiers.get(native_key)
    if not native_info:
        return
    download_file(
        native_info["url"],
        libraries_path / jar_filename_native,
        sha1=native_info.get("sha1"),
        minecraft_directory=str(base_path),
    )
    extract_natives_file(
        libraries_path / jar_filename_native,
        base_path / "versions" / version_id / "natives",
        lib_info.get("extract", {"exclude": []}),
    )


def install_libraries(
    version_id: str,
    libraries: list[ClientJsonLibrary],
    base_path: str,
    callback: CallbackDict,
    max_workers: Optional[int] = 8,
) -> None:
    """
    Install all libraries for a Minecraft version.
    """
    base_path = Path(base_path)
    filtered_libraries = [
        lib_info for lib_info in libraries
        if parse_rule_list(lib_info.get("rules", []), {})
    ]
    _set_callback(callback, "setStatus", "Завантаження бібліотек...")
    _set_callback(callback, "setMax", len(filtered_libraries))

    def download_library(lib_info: ClientJsonLibrary) -> None:
        # Download natives if present
        if "classifiers" in lib_info.get("downloads", {}):
            jar_filename_native = lib_info["downloads"]["artifact"]["path"]
            libraries_path = base_path / "libraries" / lib_info["path"]
            check_path_inside_minecraft_directory(str(base_path), str(libraries_path))
            _download_and_extract_native(
                lib_info, libraries_path, jar_filename_native, version_id, base_path
            )
            return
        # Download artifact
        artifact = lib_info["downloads"].get("artifact")
        if artifact and artifact.get("url") and artifact.get("path"):
            download_file(
                artifact["url"],
                base_path / "libraries" / artifact["path"],
                sha1=artifact.get("sha1"),
                minecraft_directory=str(base_path),
            )

    count = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(download_library, lib) for lib in filtered_libraries]
        for future in futures:
            future.result()
            count += 1
            _set_callback(callback, "setProgress", count)


def install_assets(
    data: ClientJson,
    base_path: str,
    callback: CallbackDict,
    max_workers: Optional[int] = 8,
) -> None:
    """
    Install all assets for a Minecraft version.
    """
    base_path = Path(base_path)
    if "assetIndex" not in data:
        return

    session = httpx.Client()
    asset_index_path = base_path / "assets" / "indexes" / f"{data['assets']}.json"
    download_file(
        data["assetIndex"]["url"],
        asset_index_path,
        sha1=data["assetIndex"]["sha1"],
        session=session,
    )

    with open(asset_index_path) as f:
        assets_data: AssetsJson = json.load(f)

    assets = set(val["hash"] for val in assets_data["objects"].values())
    _set_callback(callback, "setStatus", "Завантаження ресурсів...")
    _set_callback(callback, "setMax", len(assets))

    count = 0

    def download_asset(filehash: str) -> None:
        url = f"https://resources.download.minecraft.net/{filehash[:2]}/{filehash}"
        dest = base_path / "assets" / "objects" / filehash[:2] / filehash
        download_file(
            url,
            dest,
            sha1=filehash,
            session=session,
            minecraft_directory=str(base_path),
        )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(download_asset, filehash) for filehash in assets]
        for future in futures:
            future.result()
            count += 1
            _set_callback(callback, "setProgress", count)


def do_version_install(
    version_id: str,
    base_path: str,
    callback: CallbackDict,
    url: Optional[str] = None,
    sha1: Optional[str] = None,
    max_workers: Optional[int] = 8,
) -> None:
    """
    Installs the given Minecraft version.
    """
    base_path = Path(base_path)
    version_json_path = base_path / "versions" / version_id / f"{version_id}.json"
    if url:
        download_file(
            url,
            version_json_path,
            sha1=sha1,
            minecraft_directory=str(base_path),
        )

    with open(version_json_path, "r", encoding="utf-8") as f:
        versiondata: ClientJson = json.load(f)

    install_libraries(
        versiondata["id"], versiondata["libraries"], str(base_path), callback
    )
    install_assets(versiondata, str(base_path), callback)

    jobs = []

    # Download logging config
    logging_info = versiondata.get("logging", {}).get("client", {}).get("file")
    if logging_info:
        logger_file = base_path / "assets" / "log_configs" / logging_info["id"]
        jobs.append(
            {
                "url": logging_info["url"],
                "path": logger_file,
                "sha1": logging_info["sha1"],
                "minecraft_directory": str(base_path),
            }
        )

    # Download minecraft.jar
    if "downloads" in versiondata:
        client_info = versiondata["downloads"]["client"]
        jobs.append(
            {
                "url": client_info["url"],
                "path": base_path / "versions" / versiondata["id"] / f"{versiondata['id']}.jar",
                "sha1": client_info["sha1"],
                "minecraft_directory": str(base_path),
            }
        )

    # Copy jar for old forge versions if needed
    jar_path = base_path / "versions" / versiondata["id"] / f"{versiondata['id']}.jar"
    if not jar_path.is_file() and "inheritsFrom" in versiondata:
        inherits_from = versiondata["inheritsFrom"]
        inherit_path = base_path / "versions" / inherits_from / f"{inherits_from}.jar"
        check_path_inside_minecraft_directory(str(base_path), str(inherit_path))
        shutil.copyfile(inherit_path, jar_path)

    # Download all jobs
    _set_callback(callback, "setStatus", "Завантаження файлів...")
    _set_callback(callback, "setMax", len(jobs))

    count = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                download_file,
                job["url"],
                job["path"],
                sha1=job["sha1"],
                minecraft_directory=job["minecraft_directory"],
            )
            for job in jobs
        ]
        for future in futures:
            future.result()
            count += 1
            _set_callback(callback, "setProgress", count)

    # Install java runtime if needed
    if "javaVersion" in versiondata:
        _set_callback(callback, "setStatus", "Завантаження Java...")
        install_jvm_runtime(
            versiondata["javaVersion"]["majorVersion"],
            versiondata["javaVersion"]["component"],
            str(base_path),
            callback=callback,
        )


def install_minecraft_version(
    version_id: str,
    minecraft_directory: str | os.PathLike,
    callback: Optional[CallbackDict] = None,
) -> None:
    """
    Installs a Minecraft version into the given path.
    """
    base_path = Path(minecraft_directory)
    callback = callback or {}
    version_json_path = base_path / "versions" / version_id / f"{version_id}.json"
    if version_json_path.is_file():
        do_version_install(version_id, str(base_path), callback)
        return

    resp = httpx.get(
        "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json",
        headers={"user-agent": get_user_agent()},
    )
    version_list = resp.json()
    for version in version_list["versions"]:
        if version["id"] == version_id:
            do_version_install(
                version_id,
                str(base_path),
                callback,
                url=version["url"],
                sha1=version.get("sha1"),
            )
            return
    raise VersionNotFound(version_id)