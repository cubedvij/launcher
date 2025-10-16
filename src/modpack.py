import hashlib
import json
import logging
import os
import shutil
import subprocess
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

import httpx

from config import (
    APPDATA_FOLDER,
    MODPACK_REPO_URL,
    MODPACK_INDEX_URL,
    MODPACK_BRANCH,
    SYSTEM_OS,
    LAUNCHER_NAME,
    LAUNCHER_VERSION,
    AUTHLIB_INJECTOR_URL,
)
from minecraft_launcher_lib.command import get_minecraft_command
from settings import settings
from minecraft_launcher_lib._helper import (
    check_path_inside_minecraft_directory,
    download_file,
    empty,
)
from minecraft_launcher_lib.exceptions import VersionNotFound
from minecraft_launcher_lib.fabric import install_fabric
from minecraft_launcher_lib.forge import install_forge_version
from minecraft_launcher_lib.install import install_minecraft_version
from minecraft_launcher_lib.mrpack import (
    MrpackIndex,
    MrpackInstallOptions,
    _filter_mrpack_files,
)
from minecraft_launcher_lib.quilt import install_quilt
from minecraft_launcher_lib.types import CallbackDict
from minecraft_launcher_lib.utils import get_installed_versions


class Modpack:
    def __init__(self):
        self._index_url = MODPACK_INDEX_URL
        self._zip_url = f"{MODPACK_REPO_URL}/archive/refs/heads/{MODPACK_BRANCH}.zip"
        self._modpack_index_file = None
        self.name = None
        self.installed_version = None
        self.remote_version = None
        self._modpack_file = None
        self._modpack_path = None
        self._minecraft_process = None
        self._setup_paths()
        self._load_modpack_info()

        # self._fetch_latest_index(force=True)
        # self._load_modpack_info()
        # self._ensure_modpack_exists()
        # run on thread - self._ensure_modpack_exists()
        # executor = ThreadPoolExecutor(max_workers=1)
        # executor.submit(self._on_load)

    def _on_load(self) -> None:
        # self._ensure_modpack_exists()
        self._load_modpack_info()

    def _setup_paths(self) -> None:
        """Initialize all required paths."""
        self._modpack_path = APPDATA_FOLDER / "mrpack"
        self._modpack_path.mkdir(parents=True, exist_ok=True)
        self._modpack_index_file = self._modpack_path / "modrinth.index.json"
        self._modpack_file = self._modpack_path / f"{self.name}.mrpack"
        self._modpack_version_file = APPDATA_FOLDER / ".version.json"

    def _ensure_modpack_exists(self) -> None:
        """Download the modpack if it doesn't exist."""
        if not self._modpack_file.exists():
            self._download_modpack()

    def _load_modpack_info(self) -> None:
        """Load and parse modpack information."""
        self._version = self._get_modpack_version()
        self.name = self._version.get("name", "unknown")
        self.installed_version = self._version.get("installed_version", "unknown")
        self.minecraft_version = self._version.get("minecraft_version", "unknown")
        self.modloader = self._version.get("modloader", "unknown")
        self.modloader_version = self._version.get("modloader_version", "unknown")
        self.modloader_full = self.minecraft_version
        if self.modloader != "unknown" and self.modloader_version != "unknown":
            self.modloader_full += f"-{self.modloader}-{self.modloader_version}"
        self._etag = self._version.get("etag")
        self.modpack_index = None

    def _fetch_index_etag(self) -> Optional[str]:
        """Fetch the latest index etag from GitHub."""
        try:
            response = httpx.head(self._index_url, follow_redirects=True)
            return response.headers.get("etag")
        except httpx.HTTPError as e:
            logging.info(f"Error fetching modpack index etag: {e}")
            return None

    def _save_index_etag(self) -> None:
        """Append the current index etag to a file."""
        ...

    def _get_saved_index_etag(self) -> Optional[str]:
        """Retrieve the saved index etag from a file."""
        ...

    def _fetch_latest_index(self, force: bool = False) -> None:
        """Fetch the latest index data from GitHub."""
        try:
            latest_etag = self._fetch_index_etag()
            if not force and self._etag and latest_etag == self._etag:
                return
            response = httpx.get(self._index_url, follow_redirects=True)
            # with open(self._modpack_index_file, "wb") as f:
            #     f.write(response.content)
            json_data = json.loads(response.text)
            self.modpack_index = json_data
            self.remote_version = json_data.get("versionId")
            self._modpack_file = (
                self._modpack_path / f"{self.name}-{self.remote_version}.mrpack"
            )
            self._etag = latest_etag
            self._save_index_etag()
            # logging.info(f"Fetched modpack index: {self.remote_version}")
        except httpx.HTTPError as e:
            logging.info(f"Error fetching modpack index: {e}")
            self.modpack_index = None

    def _get_modloader_info(self) -> Tuple[str, str]:
        """Extract modloader information from dependencies."""
        dependencies = self.modpack_index.get("dependencies", {})
        modloaders = [key for key in dependencies if key != "minecraft"]
        return (
            (modloaders[0], dependencies[modloaders[0]])
            if modloaders
            else ("unknown", "unknown")
        )

    def is_up_to_date(self) -> bool:
        """Check if the installed modpack is up to date."""
        # if not self.modpack_index:
        #     return False

        if not self.remote_version:
            return False

        if self.installed_version == self.remote_version:
            return True

        logging.info(
            f"Update available: {self.installed_version} -> {self.remote_version}"
        )
        return False

    def _download_file(self, url: str, dest_path: Path, timeout: int = 60) -> bool:
        """Download a file from a URL to a destination path with retries and chunked download."""

        max_retries = 3
        for attempt in range(max_retries):
            try:
                with httpx.stream(
                    "GET", url, follow_redirects=True, timeout=timeout
                ) as response:
                    response.raise_for_status()
                    with open(dest_path, "wb") as f:
                        for chunk in response.iter_bytes():
                            if chunk:
                                f.write(chunk)
                return True
            except (httpx.HTTPError, KeyError, httpx.IncompleteRead) as e:
                logging.info(f"Error downloading file (attempt {attempt + 1}): {e}")
        return False

    def _download_modpack(self) -> bool:
        """Download the modpack file from GitHub repo zip."""
        return self._download_file(self._zip_url, self._modpack_file)

    def _get_modpack_info(self) -> Dict:
        """Extract and parse modpack information from the .mrpack file."""
        try:
            with zipfile.ZipFile(self._modpack_file, "r") as zf:
                with zf.open("modpack-main/modrinth.index.json") as f:
                    return json.load(f)
        except (zipfile.BadZipFile, KeyError, json.JSONDecodeError) as e:
            raise RuntimeError(f"Error getting modpack info: {e}")

    def install_mrpack(
        self,
        path: str | os.PathLike,
        minecraft_directory: str | os.PathLike,
        modpack_directory: str | os.PathLike | None = None,
        callback: CallbackDict | None = None,
        mrpack_install_options: MrpackInstallOptions | None = None,
        max_workers: int | None = 8,
    ) -> None:
        # https://codeberg.org/JakobDev/minecraft-launcher-lib/src/branch/master/minecraft_launcher_lib/mrpack.py
        minecraft_directory = os.path.abspath(minecraft_directory)
        path = os.path.abspath(path)

        if callback is None:
            callback = {}

        if mrpack_install_options is None:
            mrpack_install_options = {}

        with zipfile.ZipFile(path, "r") as zf:
            with zf.open(f"modpack-{MODPACK_BRANCH}/modrinth.index.json", "r") as f:
                index: MrpackIndex = json.load(f)

            self.name = index["name"]
            minecraft_directory = os.path.join(minecraft_directory, self.name)
            if not os.path.exists(minecraft_directory):
                os.makedirs(minecraft_directory)

            if modpack_directory is None:
                modpack_directory = minecraft_directory
            else:
                modpack_directory = os.path.abspath(modpack_directory)

            # Download the files
            file_list = _filter_mrpack_files(index["files"], mrpack_install_options)

            callback.get("setStatus", empty)("Завантаження модів...")
            callback.get("setMax", empty)(len(file_list))

            mods = []
            for _, file in enumerate(file_list):
                full_path = os.path.abspath(
                    os.path.join(modpack_directory, file["path"])
                )

                mods.append(
                    {
                        "url": file["downloads"][0],
                        "path": full_path,
                        "sha1": file["hashes"]["sha1"],
                    }
                )

            # Clean old mods
            self._clean_old_mods()

            # Download the files in parallel
            self.download_mods(callback, max_workers, mods)

            # Extract the overrides
            self.extract_overrides(modpack_directory, zf)

            # apply resource packs from overrides to options.txt
            self.configure_resource_packs(minecraft_directory, zf)

            if mrpack_install_options.get("skipDependenciesInstall"):
                return

            self.setup_mod_loaders(minecraft_directory, callback, index)
            return

    def setup_mod_loaders(self, minecraft_directory, callback, index):
        if "forge" in index["dependencies"]:
            forge_version = None
            FORGE_DOWNLOAD_URL = "https://maven.minecraftforge.net/net/minecraftforge/forge/{version}/forge-{version}-installer.jar"
            for current_forge_version in (
                f"{index['dependencies']['minecraft']}-{index['dependencies']['forge']}",
                f"{index['dependencies']['minecraft']}-{index['dependencies']['forge']}-{index['dependencies']['minecraft']}",
            ):
                if (
                    httpx.head(
                        FORGE_DOWNLOAD_URL.replace("{version}", current_forge_version)
                    ).status_code
                    == 200
                ):
                    forge_version = current_forge_version
                    break
            else:
                raise VersionNotFound(index["dependencies"]["forge"])

                # callback.get("setStatus", empty)(f"Installing Forge {forge_version}")
            install_forge_version(forge_version, minecraft_directory, callback=callback)

        if "fabric-loader" in index["dependencies"]:
            # callback.get("setStatus", empty)(
            #     f"Встановлення Fabric {index['dependencies']['fabric-loader']}"
            # )
            install_fabric(
                index["dependencies"]["minecraft"],
                minecraft_directory,
                loader_version=index["dependencies"]["fabric-loader"],
                callback=callback,
            )

        if "quilt-loader" in index["dependencies"]:
            # callback.get("setStatus", empty)(
            #     f"Встановлення Quilt {index['dependencies']['quilt-loader']}"
            # )
            install_quilt(
                index["dependencies"]["minecraft"],
                minecraft_directory,
                loader_version=index["dependencies"]["quilt-loader"],
                callback=callback,
            )

        else:
            callback.get("setStatus", empty)(
                f"Installing Minecraft {index['dependencies']['minecraft']}"
            )
            install_minecraft_version(
                index["dependencies"]["minecraft"],
                minecraft_directory,
                callback=callback,
            )

    def download_mods(self, callback, max_workers, mods):
        count = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(
                    download_file, mod["url"], mod["path"], sha1=mod["sha1"]
                )
                for mod in mods
            ]
            for future in futures:
                future.result()
                count += 1
                callback.get("setProgress", empty)(count)

    def configure_resource_packs(
        self, minecraft_directory, zf: zipfile.ZipFile
    ) -> None:
        """Configure resource packs in options.txt."""
        resource_packs = []
        for zip_name in zf.namelist():
            if zip_name.startswith("modpack-main/overrides/resourcepacks/"):
                # Remove the prefix and get the pack name
                pack_name = zip_name[len("modpack-main/overrides/resourcepacks/") :]
                if pack_name.endswith(".zip"):
                    resource_packs.append(pack_name)
        if resource_packs:
            # append resource packs to options.txt (not override)
            options_txt_path = os.path.join(minecraft_directory, "options.txt")
            new_packs = ",".join(
                [
                    f'"file/{pack}"' if pack.endswith(".zip") else f'"{pack}"'
                    for pack in resource_packs
                ]
            )
            # clear empty resource packs
            if os.path.exists(options_txt_path):
                with open(options_txt_path, "r") as f:
                    options_txt = f.readlines()

                # Find the line that starts with resourcePacks
                for i, line in enumerate(options_txt):
                    if line.startswith("resourcePacks:"):
                        # Append the resource packs to the line
                        existing_packs = line.strip().split("resourcePacks:")[1].strip()
                        existing_packs = (
                            existing_packs.strip("[]")
                            .replace('"', "")
                            .replace(" ", "")
                            .split(",")
                        )

                        # Keep the first pack
                        if existing_packs:
                            resource_packs + existing_packs
                            # Remove duplicates
                            resource_packs = list(set(resource_packs))
                        # Join the packs into a single string
                        if resource_packs:
                            # Create the new line with the resource packs
                            packs = ",".join(
                                [
                                    f'"file/{pack}"'
                                    if pack.endswith(".zip")
                                    else f'"{pack}"'
                                    for pack in resource_packs
                                ]
                            )
                            options_txt[i] = f"resourcePacks:[{packs}]\n"
                        break
                else:
                    # If no such line exists, create it
                    options_txt.append(f"resourcePacks:[{new_packs}]\n")

                    # Write the modified options.txt back
                with open(options_txt_path, "w") as f:
                    f.writelines(options_txt)
            # If options.txt does not exist, create it with the resource packs
            else:
                with open(options_txt_path, "w") as f:
                    f.write(f"resourcePacks:[{new_packs}]\n")

    def extract_overrides(self, modpack_directory, zf: zipfile.ZipFile) -> None:
        for zip_name in zf.namelist():
            # Check if the entry is in the overrides and if it is a file
            if (
                not zip_name.startswith(f"modpack-{MODPACK_BRANCH}/overrides/")
                and not zip_name.startswith(
                    f"modpack-{MODPACK_BRANCH}/client-overrides/"
                )
            ) or zf.getinfo(zip_name).file_size == 0:
                continue

            # Remove the overrides at the start of the Name
            if zip_name.startswith(f"modpack-{MODPACK_BRANCH}/client-overrides/"):
                file_name = zip_name[
                    len(f"modpack-{MODPACK_BRANCH}/client-overrides/") :
                ]
            else:
                file_name = zip_name[len(f"modpack-{MODPACK_BRANCH}/overrides/") :]

            # Constructs the full Path
            full_path = os.path.abspath(os.path.join(modpack_directory, file_name))

            check_path_inside_minecraft_directory(modpack_directory, full_path)

            # Skip extracting options.txt if it already exists
            if os.path.basename(full_path) == "options.txt" and os.path.exists(
                full_path
            ):
                continue

            try:
                os.makedirs(os.path.dirname(full_path))
            except FileExistsError:
                pass

            with open(full_path, "wb") as f:
                f.write(zf.read(zip_name))

    def install(
        self, minecraft_path: Path, callback: Optional[Callable] = None
    ) -> bool:
        """Install the modpack to the specified Minecraft directory."""
        try:
            self._ensure_modpack_exists()

            # Install the modpack
            self.install_mrpack(
                self._modpack_file,
                minecraft_path,
                callback=callback,
            )
            # Verify the installation
            if not self.verify_installation():
                raise RuntimeError("Modpack installation verification failed")

            # Save the index file for version tracking
            self._save_modpack_version()
            self._save_index_etag()
            self._clear_modpack_file()
            logging.info(f"Modpack {self.name} installed successfully.")
            return True
        except Exception as e:
            logging.error(f"Error installing modpack: {e}", exc_info=True)
            return False

    def play(self, username: str, uuid: str, token: str) -> None:
        logging.info("Checking game...")
        # check if game is installed
        installed_versions = get_installed_versions(settings.minecraft_directory)
        installed_versions_list = []
        for version in installed_versions:
            installed_versions_list.append(version["id"])
        logging.info(f"Installed versions list: {installed_versions_list}")

        # check if game is installed
        if not all(
            (
                modpack.minecraft_version in installed_versions_list,
                modpack.modloader_full in installed_versions_list,
            )
        ):
            self._install_minecraft()
        # check if modpack version is latest
        # elif not modpack.is_up_to_date():
        #    self._update_modpack(event)
        # check if modpack installed correctly
        # elif not modpack.verify_installation():
        #    self._update_modpack(event)
        else:
            self._launch_minecraft(modpack.modloader_full, username, uuid, token)

    def _launch_minecraft(
        self, version: str, username: str, uuid: str, token: str
    ) -> None:
        options = {
            "username": username,
            "uuid": uuid,
            "token": token,
            "launcherName": LAUNCHER_NAME,
            "launcherVersion": LAUNCHER_VERSION,
            "customResolution": True,
            "resolutionWidth": str(settings.window_width),
            "resolutionHeight": str(settings.window_height),
        }
        options["jvmArguments"] = [
            f"-Xmx{settings.max_use_ram}M",
            f"-Xms{settings.min_use_ram}M",
        ]
        if self.minecraft_version == "b1.7.3":
            modded_jar = self.install_jarmods()
            options["jvmArguments"].append(
                f"-javaagent:{settings.minecraft_directory}/authlib-injector.jar={AUTHLIB_INJECTOR_URL}"
            )
            options["jvmArguments"].append(
                "-javaagent:agent/ears-vanilla-b1.7.3-1.4.7.jar"
            )
            options["jvmArguments"].append("-javaagent:legacyfix-2.0.jar")
            # options["jvmArguments"].append(*settings.java_args)
            options["jvmArguments"].append("-Dlf.profile.disable")
            options["jvmArguments"].append("-Dlf.keep-resources")

            minecraft_command = get_minecraft_command(
                version,
                os.path.join(settings.minecraft_directory, self.name),
                options,
            )
            # Rebuild the launch command manually for Beta 1.7.3
            natives_dir = os.path.join(
                settings.minecraft_directory, self.name, "versions", version, "natives"
            )

            classpath = [
                # "/home/hampta/.local/share/cubedvij/.minecraft/mangopack/libraries/org/lwjgl/lwjgl/lwjgl/2.9.0/lwjgl-2.9.0.jar",
                # "/home/hampta/.local/share/cubedvij/.minecraft/mangopack/libraries/org/lwjgl/lwjgl/lwjgl_util/2.9.0/lwjgl_util-2.9.0.jar",
                # "/home/hampta/.local/share/cubedvij/.minecraft/mangopack/libraries/org/lwjgl/lwjgl/lwjgl-platform/2.9.0/org/lwjgl/lwjgl/lwjgl-platform/2.9.0/lwjgl-platform-2.9.0-natives-linux.jar",
                modded_jar,
                "/home/hampta/.local/share/cubedvij/.minecraft/mangopack/agent/OnlineModeFix.jar",
            ]
            classpath_str = ":".join(classpath)

            # minecraft_command = [
            #     "/home/hampta/.local/share/cubedvij/.minecraft/mangopack/runtime/jre-legacy/bin/java",
            #     f"-Xmx{settings.max_use_ram}M",
            #     f"-Xms{settings.min_use_ram}M",
            #     "-javaagent:agent/ears-vanilla-b1.7.3-1.4.7.jar",
            #     "-javaagent:legacyfix-2.0.jar",
            #     f"-javaagent:{settings.minecraft_directory}/authlib-injector.jar={AUTHLIB_INJECTOR_URL}",
            #     "-Dminecraft.api.session.host=https://auth.cubedvij.pp.ua/session",
            #     "-Djava.protocol.handler.pkgs=gg.codie.mineonline.protocol",
            #     "-Dlf.profile.disable",
            #     "-Dlf.keep-resources",
            #     # "-Dfml.ignoreInvalidMinecraftCertificates=true",
            #     f"-Djava.library.path={natives_dir}",
            #     f"-Dorg.lwjgl.librarypath={natives_dir}",
            #     "-cp",
            #     classpath_str,
            #     "net.minecraft.client.Minecraft",
            #     username,
            #     token,
            # ]

            for arg in minecraft_command:
                if arg.startswith("-cp"):
                    classpaths = minecraft_command[minecraft_command.index(arg) + 1].split(":")
                    classpaths.pop(-1)  # remove original minecraft jar
                    classpaths.append(modded_jar)
                    classpath_str = ":".join(classpaths)
                    minecraft_command[minecraft_command.index(arg) + 1] = classpath_str
                if arg.startswith("net.minecraft.launchwrapper.Launch"):
                    minecraft_command[minecraft_command.index(arg)] = "net.minecraft.client.Minecraft"

        else:
            options["jvmArguments"].append(
                f"-javaagent:{settings.minecraft_directory}/authlib-injector.jar={AUTHLIB_INJECTOR_URL}"
            )
            options["jvmArguments"].append(*settings.java_args)
            minecraft_command = get_minecraft_command(
                version, os.path.join(settings.minecraft_directory, self.name), options
            )
        # save command to a file for debugging
        with open("last_launch_command.txt", "w") as f:
            f.write(" ".join(minecraft_command))
        # change working directory to .minecraft
        os.chdir(os.path.join(settings.minecraft_directory, self.name))
        if self._check_minecraft_running():
            logging.info("Minecraft is already running.")
            return
        print(" ".join(minecraft_command))
        logging.info("Launching Minecraft...")

        if SYSTEM_OS == "Windows":
            self._minecraft_process = subprocess.Popen(
                minecraft_command,
                creationflags=subprocess.CREATE_NO_WINDOW,
                start_new_session=True,
            )
        elif SYSTEM_OS == "Linux":
            self._minecraft_process = subprocess.Popen(
                minecraft_command,
                start_new_session=True,
            )
        # self.page.run_task(self._check_minecraft)
        # self._play_button_stop()
        # self._check_game_button_disable()
        # if settings.minimize_launcher:
        #     self.page.window.minimized = True
        # if settings.close_launcher:
        #     self.kill_app()
        # self.page.update()

    def install_jarmods(self) -> None:
        mmc_pack_path = os.path.join(
            settings.minecraft_directory, self.name, "mmc-pack.json"
        )
        mmc_pack = {}
        if os.path.exists(mmc_pack_path):
            with open(mmc_pack_path, "r") as f:
                mmc_pack = json.load(f)
        jarmods_path = os.path.join(settings.minecraft_directory, self.name, "jarmods")
        jarmods_list = []

        logging.info(f"Found {len(jarmods_list)} jarmods, installing...")
        jar_path = os.path.join(
            settings.minecraft_directory,
            self.name,
            "versions",
            self.modloader_full,
            f"{self.modloader_full}.jar",
        )
        output_path = os.path.join(
            settings.minecraft_directory, self.name, "bin", "minecraft.jar"
        )
        if not os.path.exists(jar_path):
            raise FileNotFoundError(f"Jar file not found: {jar_path}")
        if not os.path.exists(jarmods_path):
            os.makedirs(jarmods_path)
        if not os.path.exists(os.path.dirname(output_path)):
            os.makedirs(os.path.dirname(output_path))
        # Temporary folder for modification
        temp_dir = "temp_jar"
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir, exist_ok=True)

        # Unpack original jar
        with zipfile.ZipFile(jar_path, "r") as jar:
            jar.extractall(temp_dir)

        # Remove META-INF (prevents black screen)
        meta_inf = os.path.join(temp_dir, "META-INF")
        if os.path.exists(meta_inf):
            shutil.rmtree(meta_inf)

        mmc_components = mmc_pack.get("components", {}) if mmc_pack else {}
        for component in mmc_components:
            filename = component.get("uid", "").split("org.multimc.jarmod.")[-1]
            if component.get("uid", "").startswith("org.multimc.jarmod."):
                mod_path = os.path.join(jarmods_path, f"{filename}.jar")
                if os.path.exists(mod_path):
                    jarmods_list.append(mod_path)

        logging.info(f"Total jarmods to install: {len(jarmods_list)}")
        # Copy jarmods into the unpacked jar
        for jarmod in jarmods_list:
            with zipfile.ZipFile(jarmod, "r") as jar:
                jar.extractall(temp_dir)

        # Repack jar
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as newjar:
            for root, _, files in os.walk(temp_dir):
                for f in files:
                    path = os.path.join(root, f)
                    arcname = os.path.relpath(path, temp_dir)
                    newjar.write(path, arcname)

        shutil.rmtree(temp_dir)
        return output_path

    def _check_minecraft_running(self):
        return (
            self._minecraft_process is not None
            and self._minecraft_process.poll() is None
        )

    def _clear_modpack_file(self) -> None:
        """Clear the modpack file if it exists."""
        if self._modpack_file and self._modpack_file.exists():
            try:
                self._modpack_file.unlink()
            except Exception as e:
                logging.error(f"Error clearing modpack file: {e}")

    def _save_modpack_version(self) -> None:
        """Save the modpack version information."""

        self.installed_version = self.remote_version
        self.minecraft_version = self.modpack_index.get("dependencies", {}).get(
            "minecraft", "unknown"
        )
        self.modloader, self.modloader_version = self._get_modloader_info()

        self.modloader_full = self.minecraft_version

        if self.modloader != "unknown":
            self.modloader_full += f"-{self.modloader}-{self.modloader_version}"

        if not self._modpack_version_file.parent.exists():
            self._modpack_version_file.parent.mkdir(parents=True)

        with open(self._modpack_version_file, "w") as f:
            json.dump(
                {
                    "name": self.name,
                    "installed_version": self.installed_version,
                    "minecraft_version": self.minecraft_version,
                    "modloader": self.modloader,
                    "modloader_version": self.modloader_version,
                    "etag": self._etag,
                },
                f,
            )

    def _get_modpack_version(self) -> Dict:
        """Get the modpack version information."""
        if not self._modpack_version_file.exists():
            return {}

        with open(self._modpack_version_file, "r") as f:
            return json.load(f)

    def get_launch_version(self) -> Dict:
        """Get the launch version information for the modpack."""
        if not self._modpack_file.exists():
            raise FileNotFoundError("Modpack file does not exist")

    def update(self, callback: Optional[dict[Callable]] = None) -> None:
        """Update the modpack to the latest version."""

        # Update version information
        self._modpack_file = (
            self._modpack_path / f"{self.name}-{self.remote_version}.mrpack"
        )

        # Download and install the update
        if not self._download_modpack():
            raise RuntimeError("Failed to download modpack update")

        options = {
            "skipDependenciesInstall": True,
        }
        self.install_mrpack(
            self._modpack_file,
            settings.minecraft_directory,
            callback=callback,
            mrpack_install_options=options,
        )
        # Verify the installation
        if not self.verify_installation():
            callback.get("setStatus", empty)(
                "Модпак не вдалося оновити. Спробуйте ще раз."
            )
            raise RuntimeError("Modpack installation verification failed")

        # Update the installed version
        # self._save_modpack_index()
        # self._load_modpack_info()  # Refresh modpack info
        self._save_modpack_version()
        self._save_index_etag()
        self._clear_modpack_file()

        logging.info(f"Modpack {self.name} updated to version {self.remote_version}.")

    def _clean_old_mods(self) -> None:
        """Remove mods that are no longer needed."""
        mods_dir = os.path.join(settings.minecraft_directory, "mods")
        if os.path.exists(mods_dir):
            for mod in os.listdir(mods_dir):
                mod_path = os.path.join(mods_dir, mod)
                if os.path.isfile(mod_path) and mod.endswith(".jar"):
                    os.remove(mod_path)
            logging.info("Old mods cleaned up successfully.")
        else:
            logging.info("Mods directory does not exist, skipping cleanup.")

    def verify_installation(self) -> bool:
        """Verify that all modpack files are correctly installed."""
        for file in self.modpack_index.get("files", []):
            file_path = os.path.join(
                settings.minecraft_directory, self.name, file["path"]
            )
            # Check file existence
            if (
                "env" in file and file["env"].get("client") == "required"
            ) or "hashes" in file:
                if not os.path.exists(file_path):
                    logging.info(f"Missing required file: {file_path}")
                    return False

                # Verify file hash if available
                if "hashes" in file and "sha1" in file["hashes"]:
                    if not self._verify_file_hash(file_path, file["hashes"]["sha1"]):
                        logging.info(f"File hash mismatch: {file_path}")
                        return False

        return True

    def _verify_file_hash(self, file_path: Path, expected_hash: str) -> bool:
        """Verify the SHA1 hash of a file."""
        with open(file_path, "rb") as f:
            file_hash = hashlib.sha1(f.read()).hexdigest()
            return file_hash == expected_hash


# Global modpack instance
modpack = Modpack()
