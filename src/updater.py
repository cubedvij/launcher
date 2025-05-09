import os
import sys
import shutil
import httpx
import logging
import subprocess
import multiprocessing



from .config import (
    LATEST_LAUNCHER_RELEASE_URL,
    LAUNCHER_VERSION,
    _COMPILED,
    SYSTEM_OS,
    LAUNCHER_DIRECTORY,
    APPDATA_FOLDER,
)


class Updater:
    def __init__(self):
        self.version = LAUNCHER_VERSION
        self.releases_url = LATEST_LAUNCHER_RELEASE_URL
        self.latest_download_url = ""
        self.latest_version = ""
        self.update_available = False
        self.temp_dir = APPDATA_FOLDER / "temp"
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
        self.latest_download_url = ""
        self.latest_version = ""
        
    async def check_for_update(self) -> bool:
        if "dev" in self.version or not _COMPILED:
            # Don't check for updates in dev build or if not compiled
            return False
        self.update_available = (
            await self.get_latest_version() != self.version
            and self.latest_version != ""
        )
        return self.update_available

    async def get_latest_version(self) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.get(self.releases_url)
            if response.status_code != 200:
                logging.error(f"Failed to check for updates: {response.status_code}")
                return ""
            self.latest_version = response.json()["tag_name"].replace("v", "")
            # set latest_download_url to the first asset in the assets list by SYSTEM_OS
            for asset in response.json()["assets"]:
                if asset["name"] == os.path.basename(sys.executable):
                    self.latest_download_url = asset["browser_download_url"]
                    self.executable = asset["name"]
                    break
            logging.info(f"Latest version found: {self.latest_version}")
            logging.info(f"Latest download URL: {self.latest_download_url}")

        return self.latest_version

    def download_update(self):
        with httpx.Client(follow_redirects=True) as client:
            response = client.get(self.latest_download_url)
            if response.status_code != 200:
                logging.error(f"Failed to download update: {response.status_code}")
                return
            with open(os.path.join(self.temp_dir, f"{self.executable}"), "wb") as f:
                f.write(response.content)
        logging.info("Update downloaded successfully.")
        # self.replace_current_version()
        multiprocessing.Process(
            target=self.replace_current_version,
            name="replace_current_version",
        ).start()

    def replace_current_version(self):
        # HACK: copy _MEIPASS to the temp directory
        MEIPASS_FOLDER_NAME = os.path.basename(sys._MEIPASS)
        shutil.copytree(
            sys._MEIPASS,
            os.path.join(self.temp_dir, MEIPASS_FOLDER_NAME),
            dirs_exist_ok=True,
        )
        logging.info(f"Copied _MEIPASS to temporary directory: {MEIPASS_FOLDER_NAME}")
        # make new subprocess to replace the current version with wait 5 seconds and open the launcher
        if SYSTEM_OS == "Windows":
            subprocess.Popen(
                [
                    "cmd",
                    "/c",
                    f'timeout 1 && move /y {os.path.join(self.temp_dir, self.executable)} {os.path.join(LAUNCHER_DIRECTORY, self.executable)} && move /y {os.path.join(self.temp_dir, MEIPASS_FOLDER_NAME)} {sys._MEIPASS} && start "" {os.path.join(LAUNCHER_DIRECTORY, self.executable)}',
                ],
            )
        elif SYSTEM_OS == "Linux":
            # make new subprocess to replace the current version with wait 5 seconds and open the launcher    
            os.chmod(
                os.path.join(self.temp_dir, f"{self.executable}"),
                0o755,
            )
            subprocess.Popen(
                [
                    "bash",
                    "-c",
                    f'sleep 1 && mv {os.path.join(self.temp_dir, f"{self.executable}")} {os.path.join(LAUNCHER_DIRECTORY, self.executable)} && mv {os.path.join(self.temp_dir, MEIPASS_FOLDER_NAME)} {sys._MEIPASS} && exec {os.path.join(LAUNCHER_DIRECTORY, self.executable)}',
                ],
                start_new_session=True,
            )
        os._exit(0)
        
    def clear_old_meipass(self):
        # HACK: remove old _MEIPASS folder
        meipass_parent = os.path.dirname(sys._MEIPASS)
        meipass_folder = os.path.basename(sys._MEIPASS)
        for folder in os.listdir(meipass_parent):
            if folder.startswith("_MEI") and folder != meipass_folder:
                shutil.rmtree(os.path.join(meipass_parent, folder))
                logging.info(f"Removed old _MEIPASS folder: {folder}")
        
        logging.info("Old MEIPASS folders cleared.")

updater = Updater()
