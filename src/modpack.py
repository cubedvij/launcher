import hashlib
import json
import logging
import os
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

import httpx

from config import APPDATA_FOLDER, MODPACK_REPO_URL, MODPACK_INDEX_URL
from settings import settings
from minecraft_launcher_lib._helper import (
    check_path_inside_minecraft_directory,
    download_file,
    empty,
)
from minecraft_launcher_lib.exceptions import VersionNotFound
from minecraft_launcher_lib.fabric import install_fabric
from minecraft_launcher_lib.forge import install_forge_version
from minecraft_launcher_lib.mrpack import (
    MrpackIndex,
    MrpackInstallOptions,
    _filter_mrpack_files,
)
from minecraft_launcher_lib.quilt import install_quilt
from minecraft_launcher_lib.types import CallbackDict


class Modpack:
    def __init__(self):
        self._index_url = MODPACK_INDEX_URL
        self._zip_url = f"{MODPACK_REPO_URL}/archive/refs/heads/main.zip"
        self._modpack_index_file = None
        self.name = "cubedvij"
        self.installed_version = None
        self.remote_version = None
        self._modpack_file = None
        self._modpack_path = None
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
        self.installed_version = self._version.get("installed_version", "unknown")
        self.minecraft_version = self._version.get("minecraft_version", "unknown")
        self.modloader = self._version.get("modloader", "unknown")
        self.modloader_version = self._version.get("modloader_version", "unknown")
        self.modloader_full = (
            f"{self.minecraft_version}-{self.modloader}-{self.modloader_version}"
        )
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

        if modpack_directory is None:
            modpack_directory = minecraft_directory
        else:
            modpack_directory = os.path.abspath(modpack_directory)

        if callback is None:
            callback = {}

        if mrpack_install_options is None:
            mrpack_install_options = {}

        with zipfile.ZipFile(path, "r") as zf:
            with zf.open("modpack-main/modrinth.index.json", "r") as f:
                index: MrpackIndex = json.load(f)

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
                not zip_name.startswith("modpack-main/overrides/")
                and not zip_name.startswith("modpack-main/client-overrides/")
            ) or zf.getinfo(zip_name).file_size == 0:
                continue

            # Remove the overrides at the start of the Name
            if zip_name.startswith("modpack-main/client-overrides/"):
                file_name = zip_name[len("modpack-main/client-overrides/") :]
            else:
                file_name = zip_name[len("modpack-main/overrides/") :]

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
            logging.info(f"Error installing modpack: {e}")
            return False

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

        self.modloader_full = (
            f"{self.minecraft_version}-{self.modloader}-{self.modloader_version}"
        )

        if not self._modpack_version_file.parent.exists():
            self._modpack_version_file.parent.mkdir(parents=True)

        with open(self._modpack_version_file, "w") as f:
            json.dump(
                {
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
            file_path = os.path.join(settings.minecraft_directory, file["path"])
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
