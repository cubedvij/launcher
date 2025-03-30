import httpx
import hashlib

# GITHUB = https://github.com/yushijinhun/authlib-injector/releases

class Authlib:
    def __init__(self):
        self.base_url = "https://api.github.com/repos/yushijinhun/authlib-injector/releases"
        self.realeases = []
    
    def get_releases(self):
        response = httpx.get(self.base_url)
        if response.status_code != 200:
            return "Помилка сервера або відсутній інтернет"
        self.realeases = response.json()
        return self.realeases
    
    def get_latest_release(self):
        if not self.realeases:
            self.get_releases()
        return self.realeases[0]
    
    def download_latest_release(self, path, set_progress=None, set_size=None):
        if not self.realeases:
            self.get_releases()
        latest = self.get_latest_release()
        asset = latest["assets"][0]
        with open(path, "wb") as f:
            with httpx.stream("GET", asset["browser_download_url"], follow_redirects=True) as response:
                if response.status_code == 200:
                    if set_size:
                        set_size(int(response.headers["Content-Length"]))
                    downloaded = 0
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if set_progress:
                            set_progress(downloaded)
                return True
        return False
    
    def get_latest_release_hash(self):
        if not self.realeases:
            self.get_releases()
        return self.get_latest_release()["tag_name"]
    
    def check_authlib(self, path):
        with open(path, "rb") as f:
            content = f.read()
            installed_hash = hashlib.sha256(content).hexdigest()
        latest_hash = self.get_latest_release_hash()
        return installed_hash == latest_hash

        
authlib = Authlib()