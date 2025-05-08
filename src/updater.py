import httpx
import logging
import subprocess

from .config import LATEST_LAUNCHER_RELEASE_URL, LAUNCHER_VERSION, _COMPILED, SYSTEM_OS


class Updater:
    def __init__(self):
        self.version = LAUNCHER_VERSION
        self.releases_url = LATEST_LAUNCHER_RELEASE_URL
        self.latest_download_url = ""
        self.latest_version = ""
        self.update_available = False

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
            self.latest_version = response.json()["tag_name"].lstrip("v")
            # set  latest_download_url to the first asset in the assets list by SYSTEM_OS
            for asset in response.json()["assets"]:
                if asset["name"] == "cube-launcher":
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
            with open(f"{self.executable}.TMP", "wb") as f:
                f.write(response.content)
        logging.info("Update downloaded successfully.")
        self.replace_current_version()

    def replace_current_version(self):
        if SYSTEM_OS == "Windows":
            subprocess.Popen(
                [
                    "cmd",
                    "/c",
                    f"timeout 3 && move /y {self.executable}.TMP {self.executable} && start {self.executable}",
                ],
            )
        elif SYSTEM_OS == "Linux":
            # make new subprocess to replace the current version with wait 5 seconds and open the launcher
            subprocess.Popen(
                [
                    "bash",
                    "-c",
                    f"sleep 3 && mv {self.executable}.TMP {self.executable} && chmod +x ./{self.executable} && ./{self.executable}",
                ],
            )


updater = Updater()
