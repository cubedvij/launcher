# This file is part of minecraft-launcher-lib (https://codeberg.org/JakobDev/minecraft-launcher-lib)
# SPDX-FileCopyrightText: Copyright (c) 2019-2025 JakobDev <jakobdev@gmx.de> and contributors
# SPDX-License-Identifier: BSD-2-Clause

import copy
import json
import os
from typing import List, Union

from ._helper import (
    get_classpath_separator,
    get_library_path,
    inherit_json,
    parse_rule_list,
)
from ._internal_types.shared_types import ClientJson, ClientJsonArgumentRule
from .exceptions import VersionNotFound
from .natives import get_natives
from .runtime import get_executable_path
from .types import MinecraftOptions
from .utils import get_library_version

__all__ = ["get_minecraft_command"]


def get_libraries(data: ClientJson, path: str) -> str:
    """
    Returns the argument with all libs that come after -cp
    """
    sep = get_classpath_separator()
    libs: list[str] = []

    for lib in data["libraries"]:
        if "rules" in lib and not parse_rule_list(lib["rules"], {}):
            continue

        libs.append(get_library_path(lib["name"], path))
        native = get_natives(lib)
        if native:
            classifiers = lib.get("downloads", {}).get("classifiers", {})
            native_info = classifiers.get(native, {})
            native_path = native_info.get("path")
            if native_path:
                libs.append(os.path.join(path, "libraries", native_path))
            else:
                libs.append(get_library_path(f"{lib['name']}-{native}", path))

    jar_name = data.get("jar", data["id"])
    libs.append(os.path.join(path, "versions", jar_name, f"{jar_name}.jar"))

    return sep.join(libs)


def replace_arguments(
    argstr: str,
    version_data: ClientJson,
    path: str,
    options: MinecraftOptions,
    classpath: str
) -> str:
    """
    Replace all placeholder in arguments with the needed value
    """
    replacements = {
        "${natives_directory}": options.get("nativesDirectory", ""),
        "${launcher_name}": options.get("launcherName", "minecraft-launcher-lib"),
        "${launcher_version}": options.get("launcherVersion", get_library_version()),
        "${classpath}": classpath,
        "${auth_player_name}": options.get("username", "{username}"),
        "${version_name}": version_data["id"],
        "${game_directory}": options.get("gameDirectory", path),
        "${assets_root}": os.path.join(path, "assets"),
        "${assets_index_name}": version_data.get("assets", version_data["id"]),
        "${auth_uuid}": options.get("uuid", "{uuid}"),
        "${auth_access_token}": options.get("token", "{token}"),
        "${user_type}": "msa",
        "${version_type}": version_data["type"],
        "${user_properties}": "{}",
        "${resolution_width}": options.get("resolutionWidth", "854"),
        "${resolution_height}": options.get("resolutionHeight", "480"),
        "${game_assets}": os.path.join(path, "assets", "virtual", "legacy"),
        "${auth_session}": options.get("token", "{token}"),
        "${library_directory}": os.path.join(path, "libraries"),
        "${classpath_separator}": get_classpath_separator(),
        "${quickPlayPath}": options.get("quickPlayPath") or "{quickPlayPath}",
        "${quickPlaySingleplayer}": options.get("quickPlaySingleplayer") or "{quickPlaySingleplayer}",
        "${quickPlayMultiplayer}": options.get("quickPlayMultiplayer") or "{quickPlayMultiplayer}",
        "${quickPlayRealms}": options.get("quickPlayRealms") or "{quickPlayRealms}",
    }
    for key, value in replacements.items():
        argstr = argstr.replace(key, value)
    return argstr


def get_arguments_string(
    version_data: ClientJson,
    path: str,
    options: MinecraftOptions,
    classpath: str
) -> List[str]:
    """
    Turns the argument string from the client.json into a list
    """
    args = [
        replace_arguments(arg, version_data, path, options, classpath)
        for arg in version_data["minecraftArguments"].split()
    ]

    if options.get("customResolution", False):
        args += [
            "--width", options.get("resolutionWidth", "854"),
            "--height", options.get("resolutionHeight", "480")
        ]

    if options.get("demo", False):
        args.append("--demo")

    return args


def get_arguments(
    data: List[Union[str, ClientJsonArgumentRule]],
    version_data: ClientJson,
    path: str,
    options: MinecraftOptions,
    classpath: str
) -> List[str]:
    """
    Returns all arguments from the client.json
    """
    args: List[str] = []
    for item in data:
        if isinstance(item, str):
            args.append(replace_arguments(item, version_data, path, options, classpath))
            continue

        # Handle rules
        if (
            ("compatibilityRules" in item and not parse_rule_list(item["compatibilityRules"], options))
            or ("rules" in item and not parse_rule_list(item["rules"], options))
        ):
            continue

        value = item["value"]
        if isinstance(value, str):
            args.append(replace_arguments(value, version_data, path, options, classpath))
        else:
            args.extend(
                replace_arguments(v, version_data, path, options, classpath)
                for v in value
            )
    return args


def get_minecraft_command(
    version: str,
    minecraft_directory: Union[str, os.PathLike],
    options: MinecraftOptions
) -> List[str]:
    """
    Returns the command for running minecraft as list.
    """
    path = str(minecraft_directory)
    version_dir = os.path.join(path, "versions", version)
    if not os.path.isdir(version_dir):
        raise VersionNotFound(version)

    options = copy.deepcopy(options)
    json_path = os.path.join(version_dir, f"{version}.json")
    with open(json_path, "r", encoding="utf-8") as f:
        data: ClientJson = json.load(f)

    if "inheritsFrom" in data:
        data = inherit_json(data, path)

    options.setdefault(
        "nativesDirectory",
        os.path.join(path, "versions", data["id"], "natives")
    )
    classpath = get_libraries(data, path)

    # Java executable
    if "executablePath" in options:
        java_exec = options["executablePath"]
    elif "javaVersion" in data:
        java_exec = get_executable_path(data["javaVersion"]["component"], path) or "java"
    else:
        java_exec = options.get("defaultExecutablePath", "java")

    command: List[str] = [java_exec]

    # JVM arguments
    if "jvmArguments" in options:
        command += options["jvmArguments"]

    # JVM arguments from client.json
    arguments = data.get("arguments")
    if isinstance(arguments, dict) and "jvm" in arguments:
        command += get_arguments(arguments["jvm"], data, path, options, classpath)
    else:
        command += [
            f"-Djava.library.path={options['nativesDirectory']}",
            "-cp", classpath
        ]

    # Logging config
    if options.get("enableLoggingConfig", False):
        logging_data = data.get("logging", {}).get("client")
        if logging_data:
            logger_file = os.path.join(
                path, "assets", "log_configs", logging_data["file"]["id"]
            )
            command.append(logging_data["argument"].replace("${path}", logger_file))

    # Main class
    command.append(data["mainClass"])

    # Game arguments
    if "minecraftArguments" in data:
        command += get_arguments_string(data, path, options, classpath)
    else:
        command += get_arguments(arguments["game"], data, path, options, classpath)

    # Server options
    if "server" in options:
        command += ["--server", options["server"]]
        if "port" in options:
            command += ["--port", options["port"]]

    # Multiplayer/chat options
    if options.get("disableMultiplayer", False):
        command.append("--disableMultiplayer")
    if options.get("disableChat", False):
        command.append("--disableChat")

    return command
