import time
import hashlib
import json
import logging
import os
import zipfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional

import httpx
import minecraft_launcher_lib as mcl

from config import (
    APPDATA_FOLDER,
    AUTHLIB_INJECTOR_URL,
    LAUNCHER_NAME,
    LAUNCHER_VERSION,
    MODPACK_REPO,
    MODPACK_REPO_URL,
)
from minecraft_launcher_lib._helper import (
    check_path_inside_minecraft_directory,
    download_file,
    empty,
)
from settings import settings


@dataclass
class ModpackInfo:
    name: str
    installed_version: str
    remote_version: str
    minecraft_version: str
    modloader: str
    modloader_version: str
    etag: Optional[str] = None

    @property
    def modloader_full(self) -> str:
        return f"{self.minecraft_version}-{self.modloader}-{self.modloader_version}".lower()

    @classmethod
    def from_dict(cls, data: Dict) -> "ModpackInfo":
        return cls(
            name=data.get("name", "Unknown"),
            installed_version=data.get("installed_version", "0.0.0"),
            remote_version=data.get("remote_version", "0.0.0"),
            minecraft_version=data.get("minecraft_version", "unknown"),
            modloader=data.get("modloader", "unknown"),
            modloader_version=data.get("modloader_version", "unknown"),
            etag=data.get("etag"),
        )


@dataclass
class ModpacksInfo:
    modpacks: Dict[str, ModpackInfo]
    selected: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict) -> "ModpacksInfo":
        modpacks = {
            name: ModpackInfo.from_dict(info)
            for name, info in data.get("modpacks", {}).items()
        }
        selected = data.get("selected")
        return cls(modpacks=modpacks, selected=selected)


class Modpack:
    def __init__(self):
        self._modpack_index_file = None
        self._installed_modpacks: Dict[str, ModpackInfo] = []
        self._remote_modpacks: list[str] = []
        self._selected: Optional[str] = None
        self._mrpack_path = None
        self.fetch_modpacks()
        self._setup_paths()
        self._load_modpack_info()

        # self._fetch_latest_index(force=True)
        # self._load_modpack_info()
        # self._ensure_modpack_exists()
        # run on thread - self._ensure_modpack_exists()

    @property
    def _index_url(self) -> str:
        return f"https://raw.githubusercontent.com/{MODPACK_REPO}/refs/heads/{self._selected}/modrinth.index.json"

    @property
    def _zip_url(self) -> str:
        return f"{MODPACK_REPO_URL}/archive/refs/heads/{self._selected}.zip"

    def fetch_modpacks(self) -> None:
        # Check cache first
        cache_file = APPDATA_FOLDER / "modpacks_cache.json"
        cache_duration = 300  # 5 minutes in seconds

        if cache_file.exists():
            try:
                with open(cache_file, "r") as f:
                    cache_data = json.load(f)

                # Check if cache is still valid (5 minutes)
                if time.time() - cache_data.get("timestamp", 0) < cache_duration:
                    self._remote_modpacks = cache_data.get("modpacks", [])
                    return
            except (json.JSONDecodeError, KeyError):
                pass

        # Fetch from API if cache is invalid or doesn't exist
        try:
            resp = httpx.get(
                f"https://api.github.com/repos/{MODPACK_REPO}/branches",
                follow_redirects=True,
                timeout=30,
            )
            if resp.status_code == 200:
                branches = resp.json()
                modpacks = []
                for branch in branches:
                    name = branch.get("name")
                    if not name:
                        continue
                    modpacks.append(name)

                self._remote_modpacks = modpacks

                # Save to cache
                cache_data = {"modpacks": modpacks, "timestamp": time.time()}
                with open(cache_file, "w") as f:
                    json.dump(cache_data, f)
            else:
                logging.info(f"Error fetching modpacks: {resp.status_code}")
                # apply installed modpsacks as remote
                self._remote_modpacks = list(self._installed_modpacks.keys())
        except Exception as e:
            logging.info(f"Error fetching modpacks: {e}")
            self._remote_modpacks = []

    def _on_load(self) -> None:
        self._load_modpack_info()

    def migrate_modpacks_info(self) -> None:
        """Migrate existing modpack info to the new format."""
        if self._modpacks_info_file.exists():
            return
        existing_version_info = self._get_modpack_version()
        if not existing_version_info:
            return

        modpack_info = ModpackInfo(
            name="main",
            installed_version=existing_version_info.get("installed_version", "0.0.0"),
            remote_version=existing_version_info.get("installed_version", "0.0.0"),
            minecraft_version=existing_version_info.get("minecraft_version", "unknown"),
            modloader=existing_version_info.get("modloader", "unknown"),
            modloader_version=existing_version_info.get("modloader_version", "unknown"),
            etag=existing_version_info.get("etag"),
        )

        data = {
            "modpacks": {
                "main": {
                    "name": modpack_info.name,
                    "installed_version": modpack_info.installed_version,
                    "remote_version": modpack_info.remote_version,
                    "minecraft_version": modpack_info.minecraft_version,
                    "modloader": modpack_info.modloader,
                    "modloader_version": modpack_info.modloader_version,
                    "etag": modpack_info.etag,
                }
            },
            "selected": "main",
        }

        with open(self._modpacks_info_file, "w") as f:
            json.dump(data, f)

        logging.info("Migrated existing modpack info to new format.")

    def _setup_paths(self) -> None:
        """Initialize all required paths."""
        self._mrpack_path = APPDATA_FOLDER / "mrpack"
        self._mrpack_path.mkdir(parents=True, exist_ok=True)
        self._modpack_index_file = self._mrpack_path / "modrinth.index.json"
        # self._modpack_file = self._modpack_path / f"{self.name}.mrpack"
        self._modpack_version_file = APPDATA_FOLDER / ".version.json"  # OBSOLETE
        self._modpacks_info_file = APPDATA_FOLDER / "modpacks.json"
        if not self._modpacks_info_file.exists():
            self.migrate_modpacks_info()

    def _ensure_modpack_exists(self) -> None:
        """Download the modpack if it doesn't exist."""
        if not self.modpack_file.exists():
            self._download_modpack()

    def _load_modpack_info(self) -> None:
        """Load and parse modpack information."""
        if not self._modpacks_info_file.exists():
            self._installed_modpacks = {}
            self._selected = None
            return
        with open(self._modpacks_info_file, "r") as f:
            data = json.load(f)
        temp = ModpacksInfo.from_dict(data)
        self._installed_modpacks = temp.modpacks
        self._selected = temp.selected

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
            # Create modpack entry if it doesn't exist
            if self._selected not in self._installed_modpacks:
                modloader = json_data.get("dependencies", {}).get(
                    "modloader", "unknown"
                )
                modloader_version = json_data.get("dependencies", {}).get(
                    modloader, "unknown"
                )
                remote_version = json_data.get("versionId", "0.0.0")
                minecraft_version = json_data.get("dependencies", {}).get(
                    "minecraft", "unknown"
                )
                self._installed_modpacks[self._selected] = ModpackInfo(
                    name=self._selected,
                    installed_version="0.0.0",
                    remote_version=remote_version,
                    minecraft_version=minecraft_version,
                    modloader=modloader,
                    modloader_version=modloader_version,
                    etag=None,
                )
            self.modpack_index = json_data
            self.remote_version = json_data.get("versionId")
            self._etag = latest_etag
            self._save_index_etag()
            # logging.info(f"Fetched modpack index: {self.remote_version}")
        except httpx.HTTPError as e:
            logging.info(f"Error fetching modpack index: {e}")
            self.modpack_index = None
            self.remote_version = None
            self._etag = latest_etag
            self._save_index_etag()
            # logging.info(f"Fetched modpack index: {self.remote_version}")
        except httpx.HTTPError as e:
            logging.info(f"Error fetching modpack index: {e}")
            self.modpack_index = None

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
            except (httpx.HTTPError, KeyError) as e:
                logging.info(f"Error downloading file (attempt {attempt + 1}): {e}")
        return False

    def _download_modpack(self) -> bool:
        """Download the modpack file from GitHub repo zip."""
        return self._download_file(self._zip_url, self.modpack_file)

    def _get_modpack_info(self) -> Dict:
        """Extract and parse modpack information from the .mrpack file."""
        try:
            with zipfile.ZipFile(self.modpack_file, "r") as zf:
                with zf.open(f"modpack-{self._selected}/modrinth.index.json") as f:
                    return json.load(f)
        except (zipfile.BadZipFile, KeyError, json.JSONDecodeError) as e:
            raise RuntimeError(f"Error getting modpack info: {e}")

    def install_mrpack(
        self,
        path: str | os.PathLike,
        modpack_directory: str | os.PathLike | None = None,
        callback: mcl.types.CallbackDict | None = None,
        mrpack_install_options: mcl.mrpack.MrpackInstallOptions | None = None,
        max_workers: int | None = 8,
    ) -> None:
        # https://codeberg.org/JakobDev/minecraft-launcher-lib/src/branch/master/minecraft_launcher_lib/mrpack.py
        path = os.path.abspath(path)

        minecraft_directory = os.path.abspath(settings.minecraft_directory)
        modpack_directory = Path(minecraft_directory) / "modpacks" / self._selected

        if callback is None:
            callback = {}

        if mrpack_install_options is None:
            mrpack_install_options = {}

        with zipfile.ZipFile(path, "r") as zf:
            with zf.open(f"modpack-{self._selected}/modrinth.index.json", "r") as f:
                index: mcl.mrpack.MrpackIndex = json.load(f)

            # Download the files
            file_list = mcl.mrpack._filter_mrpack_files(
                index["files"], mrpack_install_options
            )

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
            self.extract_overrides(zf)

            # apply resource packs from overrides to options.txt
            self.configure_resource_packs(zf)

            if mrpack_install_options.get("skipDependenciesInstall"):
                return

            self.setup_mod_loaders(modpack_directory, callback, index)

    def setup_mod_loaders(self, modpack_directory, callback, index):
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
                raise mcl.exceptions.VersionNotFound(
                    f"Forge version {index['dependencies']['forge']} for Minecraft {index['dependencies']['minecraft']} not found."
                )

                # callback.get("setStatus", empty)(f"Installing Forge {forge_version}")
            mcl.forge.install_forge_version(
                forge_version, modpack_directory, callback=callback
            )

        if "fabric-loader" in index["dependencies"]:
            # callback.get("setStatus", empty)(
            #     f"Встановлення Fabric {index['dependencies']['fabric-loader']}"
            # )
            mcl.fabric.install_fabric(
                index["dependencies"]["minecraft"],
                modpack_directory,
                loader_version=index["dependencies"]["fabric-loader"],
                callback=callback,
            )

        if "quilt-loader" in index["dependencies"]:
            # callback.get("setStatus", empty)(
            #     f"Встановлення Quilt {index['dependencies']['quilt-loader']}"
            # )
            mcl.quilt.install_quilt(
                index["dependencies"]["minecraft"],
                modpack_directory,
                loader_version=index["dependencies"]["quilt-loader"],
                callback=callback,
            )

        else:
            # install vanilla
            mcl.install.install_minecraft_version(
                index["dependencies"]["minecraft"], modpack_directory, callback=callback
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

    def configure_resource_packs(self, zf: zipfile.ZipFile) -> None:
        """Configure resource packs in options.txt."""
        resource_packs = []
        for zip_name in zf.namelist():
            if zip_name.startswith(
                f"modpack-{self._selected}/overrides/resourcepacks/"
            ):
                # Remove the prefix and get the pack name
                pack_name = zip_name[
                    len(f"modpack-{self._selected}/overrides/resourcepacks/") :
                ]
                if pack_name.endswith(".zip"):
                    resource_packs.append(pack_name)
        if resource_packs:
            # append resource packs to options.txt (not override)
            options_txt_path = self.modpack_path / "options.txt"
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

    def extract_overrides(self, zf: zipfile.ZipFile) -> None:
        for zip_name in zf.namelist():
            # Check if the entry is in the overrides and if it is a file
            if (
                not zip_name.startswith(f"modpack-{self._selected}/overrides/")
                and not zip_name.startswith(
                    f"modpack-{self._selected}/client-overrides/"
                )
            ) or zf.getinfo(zip_name).file_size == 0:
                continue

            # Remove the overrides at the start of the Name
            if zip_name.startswith(f"modpack-{self._selected}/client-overrides/"):
                file_name = zip_name[
                    len(f"modpack-{self._selected}/client-overrides/") :
                ]
            else:
                file_name = zip_name[len(f"modpack-{self._selected}/overrides/") :]

            # Constructs the full Path
            full_path = os.path.abspath(self.modpack_path / file_name)

            check_path_inside_minecraft_directory(self.modpack_path, full_path)

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

    def install(self, callback: Optional[Callable] = None) -> bool:
        """Install the modpack to the specified Minecraft directory."""
        try:
            self._ensure_modpack_exists()
            # self._fetch_latest_index(force=True)

            # Install the modpack
            self.install_mrpack(
                self.modpack_file,
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

    def _clear_modpack_file(self) -> None:
        """Clear the modpack file if it exists."""
        if self.modpack_file and self.modpack_file.exists():
            try:
                self.modpack_file.unlink()
            except Exception as e:
                logging.error(f"Error clearing modpack file: {e}")

    def _save_modpack_version(self) -> None:
        """Save the modpack version information."""
        # save to self._modpacks_info_file
        if not self._selected:
            return

        self._installed_modpacks[self._selected].installed_version = self.remote_version
        self._installed_modpacks[self._selected].etag = self._etag
        data = {
            "modpacks": {
                name: {
                    "name": info.name,
                    "installed_version": info.installed_version,
                    "remote_version": info.remote_version,
                    "minecraft_version": info.minecraft_version,
                    "modloader": info.modloader,
                    "modloader_version": info.modloader_version,
                    "etag": info.etag,
                }
                for name, info in self._installed_modpacks.items()
            },
            "selected": self._selected,
        }
        with open(self._modpacks_info_file, "w") as f:
            json.dump(data, f)

    def _get_modpack_version(self) -> Dict:
        """Get the modpack version information."""
        if not self._modpack_version_file.exists():
            return {}

        with open(self._modpack_version_file, "r") as f:
            return json.load(f)

    def get_launch_version(self) -> Dict:
        """Get the launch version information for the modpack."""
        if not self.modpack_file.exists():
            raise FileNotFoundError("Modpack file does not exist")

    def update(self, callback: Optional[dict[Callable]] = None) -> None:
        """Update the modpack to the latest version."""
        self._fetch_latest_index(force=True)

        # Download and install the update
        if not self._download_modpack():
            raise RuntimeError("Failed to download modpack update")

        options = {
            "skipDependenciesInstall": True,
        }
        self.install_mrpack(
            self.modpack_file,
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
        mods_dir = self.modpack_path / "mods"
        if mods_dir.exists():
            for mod in mods_dir.iterdir():
                if mod.is_file() and mod.name.endswith(".jar"):
                    mod.unlink()
            logging.info("Old mods cleaned up successfully.")
        else:
            logging.info("Mods directory does not exist, skipping cleanup.")

    def verify_installation(self) -> bool:
        """Verify that all modpack files are correctly installed."""
        for file in self.modpack_index.get("files", []):
            # file_path = os.path.join(
            #     settings.minecraft_directory, "modpacks", self.name, file["path"]
            # )
            file_path = self.modpack_path / file["path"]
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

    def get_installed_versions(self) -> Dict[str, str]:
        return mcl.utils.get_installed_versions(self.modpack_path)

    def get_minecraft_command(self, username, uuid, access_token) -> list[str]:
        options = {
            "username": username,
            "uuid": uuid,
            "token": access_token,
            "launcherName": LAUNCHER_NAME,
            "launcherVersion": LAUNCHER_VERSION,
            "customResolution": True,
            "resolutionWidth": str(settings.window_width),
            "resolutionHeight": str(settings.window_height),
        }
        options["jvmArguments"] = [
            f"-javaagent:{settings.minecraft_directory}/authlib-injector.jar={AUTHLIB_INJECTOR_URL}",
            f"-Xmx{settings.max_use_ram}M",
            f"-Xms{settings.min_use_ram}M",
        ]
        if settings.java_args:
            options["jvmArguments"].extend(*settings.java_args)

        if not self._selected or self._selected not in self._installed_modpacks:
            raise RuntimeError("No modpack selected or modpack not installed")

        return mcl.command.get_minecraft_command(
            self.modloader_full,
            self.modpack_path,
            options,
        )

    def set_modpack(self, modpack_name: Optional[str]) -> None:
        """Set the current modpack."""
        if modpack_name and modpack_name not in self._installed_modpacks:
            logging.info(f"Modpack {modpack_name} is not installed.")
        self._selected = modpack_name
        self._fetch_latest_index(force=True)
        self._save_modpack_version()

    @property
    def name(self) -> str:
        return self._selected if self._selected else "main"

    @property
    def installed_version(self) -> str:
        if self._selected and self._selected in self._installed_modpacks:
            return self._installed_modpacks[self._selected].installed_version
        return "0.0.0"

    @property
    def remote_version(self) -> str:
        return (
            self._installed_modpacks[self._selected].remote_version
            if self._selected and self._selected in self._installed_modpacks
            else "0.0.0"
        )

    @remote_version.setter
    def remote_version(self, value: str) -> None:
        if self._selected and self._selected in self._installed_modpacks:
            self._installed_modpacks[self._selected].remote_version = value

    @property
    def etag(self) -> Optional[str]:
        if self._selected and self._selected in self._installed_modpacks:
            return self._installed_modpacks[self._selected].etag
        return None

    @etag.setter
    def etag(self, value: Optional[str]) -> None:
        if self._selected and self._selected in self._installed_modpacks:
            self._installed_modpacks[self._selected].etag = value

    @property
    def modpack_index(self) -> Dict:
        if self._selected and self._selected in self._installed_modpacks:
            return self._installed_modpacks[self._selected].modpack_index
        return {}

    @modpack_index.setter
    def modpack_index(self, value: Dict) -> None:
        if self._selected and self._selected in self._installed_modpacks:
            self._installed_modpacks[self._selected].modpack_index = value

    @property
    def minecraft_version(self) -> str:
        if self._selected and self._selected in self._installed_modpacks:
            return self._installed_modpacks[self._selected].minecraft_version
        return "unknown"

    @property
    def modloader_full(self) -> str:
        if self._selected and self._selected in self._installed_modpacks:
            if self._installed_modpacks[self._selected].modloader == "unknown":
                return self.minecraft_version
            return self._installed_modpacks[self._selected].modloader_full
        return "unknown-unknown"

    @property
    def modpack_path(self) -> Optional[Path]:
        return (
            Path(settings.minecraft_directory) / "modpacks" / self.name
            if self._selected
            else None
        )

    @property
    def modpack_file(self) -> Optional[Path]:
        if self._selected and self._selected in self._installed_modpacks:
            return self._mrpack_path / f"{self.name}-{self.remote_version}.mrpack"
        return None


# Global modpack instance
modpack = Modpack()
