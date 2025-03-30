import os
import json
import zipfile
import httpx
import hashlib
from pathlib import Path
from typing import Optional, Dict, Tuple, Callable, override
from minecraft_launcher_lib.mrpack import (
    install_minecraft_version,
    install_forge_version,
    install_fabric,
    install_quilt,
    download_file,
    check_path_inside_minecraft_directory,
    empty,
    CallbackDict,
    MrpackInstallOptions,
    MrpackIndex,
    _filter_mrpack_files,   
    VersionNotFound,
)
from .config import APPDATA_FOLDER, MINECRAFT_FOLDER


class Modpack:
    def __init__(self):
        self._repo_url = "https://github.com/cubedvij/modpack"
        self._index_url = f"{self._repo_url}/raw/refs/heads/main/modrinth.index.json"
        self._zip_url = f"{self._repo_url}/archive/refs/heads/main.zip"
        self.name = "cubedvij"
        self._setup_paths()

        self.installed_version = self._get_installed_modpack_version()
        self.modpack_index = self._fetch_latest_index()
        self.remote_version = self.modpack_index.get("versionId")
        self._modpack_file = (
            self._modpack_path / f"{self.name}-{self.remote_version}.mrpack"
        )

        self._ensure_modpack_exists()
        self._load_modpack_info()

    def _setup_paths(self) -> None:
        """Initialize all required paths."""
        self._modpack_path = APPDATA_FOLDER / "mrpack"
        self._modpack_path.mkdir(parents=True, exist_ok=True)
        self._modpack_index_file = self._modpack_path / "modrinth.index.json"

    def _ensure_modpack_exists(self) -> None:
        """Download the modpack if it doesn't exist."""
        if not self._modpack_file.exists():
            self._download_modpack()

    def _load_modpack_info(self) -> None:
        """Load and parse modpack information."""
        self._modpack_info = self._get_modpack_info()
        self.minecraft_version = self._modpack_info["dependencies"].get(
            "minecraft", "unknown"
        )
        self.modloader, self.modloader_version = self._get_modloader_info()
        self.modloader_full = (
            f"{self.minecraft_version}-{self.modloader}-{self.modloader_version}"
        )
        

    def _fetch_latest_index(self) -> Optional[Dict]:
        """Fetch the latest index data from GitHub."""
        try:
            response = httpx.get(self._index_url, follow_redirects=True)
            response.raise_for_status()
            with open(self._modpack_index_file, "wb") as f:
                f.write(response.content)
            return json.loads(response.text)
        except httpx.HTTPError as e:
            print(f"Error fetching modpack index: {e}")
            return None

    def _get_installed_modpack_version(self) -> Optional[str]:
        """Get the currently installed modpack version."""
        if self._modpack_index_file.exists():
            with open(self._modpack_index_file, "r") as f:
                return json.load(f).get("versionId")
        return None

    def _get_modloader_info(self) -> Tuple[str, str]:
        """Extract modloader information from dependencies."""
        dependencies = self._modpack_info.get("dependencies", {})
        modloaders = [key for key in dependencies if key != "minecraft"]
        return (
            (modloaders[0], dependencies[modloaders[0]])
            if modloaders
            else ("unknown", "unknown")
        )

    def is_up_to_date(self) -> bool:
        """Check if the installed modpack is up to date."""
        if not self.modpack_index:
            print("No modpack index available")
            return False

        if not self.remote_version:
            print("Modpack version not found")
            return False

        if self.installed_version == self.remote_version:
            print(f"Modpack is up to date: {self.installed_version}")
            return True

        print(f"Update available: {self.installed_version} -> {self.remote_version}")
        return False

    def _download_modpack(self) -> bool:
        """Download the modpack file from GitHub repo zip."""
        try:
            response = httpx.get(self._zip_url, follow_redirects=True)
            response.raise_for_status()

            with open(self._modpack_file, "wb") as f:
                f.write(response.content)
            return True
        except (httpx.HTTPError, KeyError) as e:
            print(f"Error downloading modpack: {e}")
            return False

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
            callback.get("setStatus", empty)("Download mrpack files")
            file_list = _filter_mrpack_files(index["files"], mrpack_install_options)
            callback.get("setMax", empty)(len(file_list))
            for count, file in enumerate(file_list):
                full_path = os.path.abspath(
                    os.path.join(modpack_directory, file["path"])
                )

                check_path_inside_minecraft_directory(modpack_directory, full_path)

                download_file(
                    file["downloads"][0],
                    full_path,
                    sha1=file["hashes"]["sha1"],
                    callback=callback,
                )

                callback.get("setProgress", empty)(count + 1)

            # Extract the overrides
            callback.get("setStatus", empty)("Extract overrides")
            for zip_name in zf.namelist():
                # Check if the entry is in the overrides and if it is a file
                if (
                    not zip_name.startswith("modpack-main/overrides/")
                    and not zip_name.startswith("modpack-main/client-overrides/")
                ) or zf.getinfo(zip_name).file_size == 0:
                    continue

                # Remove the overrides at the start of the Name
                # We don't have removeprefix() in Python 3.8
                if zip_name.startswith("modpack-main/client-overrides/"):
                    file_name = zip_name[len("modpack-main/client-overrides/") :]
                else:
                    file_name = zip_name[len("modpack-main/overrides/") :]

                # Constructs the full Path
                full_path = os.path.abspath(os.path.join(modpack_directory, file_name))

                check_path_inside_minecraft_directory(modpack_directory, full_path)

                callback.get("setStatus", empty)(f"Extract {zip_name}]")

                try:
                    os.makedirs(os.path.dirname(full_path))
                except FileExistsError:
                    pass

                with open(full_path, "wb") as f:
                    f.write(zf.read(zip_name))

            if mrpack_install_options.get("skipDependenciesInstall"):
                return

            # Install dependencies
            callback.get("setStatus", empty)(
                "Installing Minecraft " + index["dependencies"]["minecraft"]
            )
            install_minecraft_version(
                index["dependencies"]["minecraft"],
                minecraft_directory,
                callback=callback,
            )

            if "forge" in index["dependencies"]:
                forge_version = None
                FORGE_DOWNLOAD_URL = "https://maven.minecraftforge.net/net/minecraftforge/forge/{version}/forge-{version}-installer.jar"
                for current_forge_version in (
                    index["dependencies"]["minecraft"]
                    + "-"
                    + index["dependencies"]["forge"],
                    index["dependencies"]["minecraft"]
                    + "-"
                    + index["dependencies"]["forge"]
                    + "-"
                    + index["dependencies"]["minecraft"],
                ):
                    if (
                        httpx.head(
                            FORGE_DOWNLOAD_URL.replace(
                                "{version}", current_forge_version
                            )
                        ).status_code
                        == 200
                    ):
                        forge_version = current_forge_version
                        break
                else:
                    raise VersionNotFound(index["dependencies"]["forge"])

                callback.get("setStatus", empty)(f"Installing Forge {forge_version}")
                install_forge_version(
                    forge_version, minecraft_directory, callback=callback
                )

            if "fabric-loader" in index["dependencies"]:
                callback.get("setStatus", empty)(
                    "Installing Fabric "
                    + index["dependencies"]["fabric-loader"]
                    + " for Minecraft "
                    + index["dependencies"]["minecraft"]
                )
                install_fabric(
                    index["dependencies"]["minecraft"],
                    minecraft_directory,
                    loader_version=index["dependencies"]["fabric-loader"],
                    callback=callback,
                )

            if "quilt-loader" in index["dependencies"]:
                callback.get("setStatus", empty)(
                    "Installing Quilt "
                    + index["dependencies"]["quilt-loader"]
                    + " for Minecraft "
                    + index["dependencies"]["minecraft"]
                )
                install_quilt(
                    index["dependencies"]["minecraft"],
                    minecraft_directory,
                    loader_version=index["dependencies"]["quilt-loader"],
                    callback=callback,
                )

    def install(
        self, minecraft_path: Path, callback: Optional[Callable] = None
    ) -> bool:
        """Install the modpack to the specified Minecraft directory."""
        try:
            if not self._modpack_file.exists():
                raise FileNotFoundError("Modpack file does not exist")

            # Install the modpack
            self.install_mrpack(
                self._modpack_file,
                minecraft_path,
                callback=callback,
            )
            # Verify the installation
            if not self.verify_installation():
                raise RuntimeError("Modpack installation verification failed")
            
            # Update the installed version
            self.installed_version = self.remote_version
            # Save the index file for version tracking
            self._save_modpack_index()
            return True
        except Exception as e:
            print(f"Error installing modpack: {e}")
            return False

    def _save_modpack_index(self) -> None:
        """Save the modpack index file for version tracking."""
        with zipfile.ZipFile(self._modpack_file, "r") as zf:
            with zf.open("modpack-main/modrinth.index.json", "r") as f:
                index = json.load(f)
            with open(self._modpack_index_file, "w") as f:
                json.dump(index, f)

    def get_launch_version(self) -> Dict:
        """Get the launch version information for the modpack."""
        if not self._modpack_file.exists():
            raise FileNotFoundError("Modpack file does not exist")

    def update(self, callback: Optional[Callable] = None) -> None:
        """Update the modpack to the latest version."""

        # Update version information
        self._modpack_file = (
            self._modpack_path / f"{self.name}-{self.remote_version}.mrpack"
        )

        # Download and install the update
        if not self._download_modpack():
            raise RuntimeError("Failed to download modpack update")

        # Clean old mods
        self._clean_old_mods()

        options = {
            "skipDependenciesInstall": True,
        }
        self.install_mrpack(
            self._modpack_file,
            MINECRAFT_FOLDER,
            callback=callback,
            mrpack_install_options=options,
        )
        # Verify the installation
        if not self.verify_installation():
            raise RuntimeError("Modpack installation verification failed")

        # Update the installed version
        self.installed_version = self.remote_version

        self._save_modpack_index()
        self._load_modpack_info()  # Refresh modpack info


    def _clean_old_mods(self) -> None:
        """Remove mods that are no longer needed."""
        mods_dir = MINECRAFT_FOLDER / "mods"
        if mods_dir.exists():
            for mod in mods_dir.iterdir():
                if mod.is_file() and mod.suffix == ".jar":
                    mod.unlink()
                    print(f"Removed old mod: {mod}")
        else:
            print("Mods directory does not exist, skipping cleanup.")

    def verify_installation(self) -> bool:
        """Verify that all modpack files are correctly installed."""
        for file in self._modpack_info.get("files", []):
            file_path = MINECRAFT_FOLDER / file["path"]

            # Check file existence
            if (
                "env" in file and file["env"].get("client") == "required"
            ) or "hashes" in file:
                if not file_path.exists():
                    print(f"Missing required file: {file_path}")
                    return False

                # Verify file hash if available
                if "hashes" in file and "sha1" in file["hashes"]:
                    if not self._verify_file_hash(file_path, file["hashes"]["sha1"]):
                        print(f"File hash mismatch: {file_path}")
                        return False

        return True

    def _verify_file_hash(self, file_path: Path, expected_hash: str) -> bool:
        """Verify the SHA1 hash of a file."""
        with open(file_path, "rb") as f:
            file_hash = hashlib.sha1(f.read()).hexdigest()
            return file_hash == expected_hash


# Global modpack instance
modpack = Modpack()
