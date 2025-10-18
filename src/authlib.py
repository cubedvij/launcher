import os
import httpx
import hashlib
import logging
from zipfile import ZipFile

from minecraft_launcher_lib._helper import empty

# GITHUB = https://github.com/yushijinhun/authlib-injector/releases

class Authlib:
    def __init__(self):
        self.base_url = "https://api.github.com/repos/yushijinhun/authlib-injector/releases"
        self.releases = self.get_releases()
    
    def get_releases(self):
        response = httpx.get(self.base_url)
        if response.status_code != 200:
            return "Помилка сервера або відсутній інтернет"
        self.releases = response.json()
        return self.releases

    def download_latest_release(self, path, callback: dict) -> bool:
        """Download the latest release asset from GitHub with retries and chunked download."""

        max_retries = 3
        current_version = self.get_authlib_version(path) if os.path.exists(path) else None
        if current_version == self.get_latest_release_version():
            logging.info("Authlib-injector is already up to date.")
            return True
        for attempt in range(max_retries):
            try:
                latest = self.releases[0]
                asset = latest["assets"][0]
                url = asset["browser_download_url"]
                with httpx.stream("GET", url, follow_redirects=True, timeout=60) as response:
                    response.raise_for_status()
                    total = int(response.headers.get("Content-Length", 0))
                    callback.get("setStatus", empty)("Завантаження authlib-injector...")
                    callback.get("setMax", empty)(total)
                    downloaded = 0
                    with open(path, "wb") as f:
                        for chunk in response.iter_bytes(chunk_size=1024):
                            f.write(chunk)
                            downloaded += len(chunk)
                            callback.get("setProgress", empty)(downloaded)
                    if downloaded != total:
                        logging.error("Downloaded file size does not match expected size.")
                        return False
                return True
            except (httpx.HTTPError, KeyError, IndexError) as e:
                logging.info(f"Error downloading release (attempt {attempt+1}): {e}")
        return False
    
    def get_latest_release_hash(self):
        return self.releases[0]["assets"][0]["digest"]
    
    def get_latest_release_version(self):
        return self.releases[0]["tag_name"].replace("v", "")
    
    def check_authlib(self, path):
        with open(path, "rb") as f:
            content = f.read()
            installed_hash = hashlib.sha256(content).hexdigest()
        latest_hash = self.get_latest_release_hash()
        return installed_hash == latest_hash

    def get_authlib_version(self, path):
        with ZipFile(path, 'r') as zip_ref:
            with zip_ref.open("META-INF/MANIFEST.MF") as manifest_file:
                for line in manifest_file:
                    decoded_line = line.decode('utf-8').strip()
                    if decoded_line.startswith("Implementation-Version:"):
                        return decoded_line.split(":", 1)[1].strip()
        return None

authlib = Authlib()