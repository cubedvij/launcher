import re
import os
import json
import httpx
import hashlib

from .minepi import Player
from .config import AUTH_URL, ACCOUNT_FILE, USER_FILE, APPDATA_FOLDER, SKINS_CACHE_FOLDER


class Auth:
    def __init__(self):
        self.base_url = AUTH_URL
        self.account = {}
        self.user = {}
        self.update_skin = None
        self.skin_hash = None
        self.yggdrasil_session = httpx.Client()
        self.api_session = httpx.Client()
        self.load_account()
        self.load_user()

    def load_account(self):
        try:
            with open(ACCOUNT_FILE, "r") as f:
                self.account = json.load(f)
        except FileNotFoundError:
            pass

    def save_account(self):
        with open(ACCOUNT_FILE, "w") as f:
            json.dump(self.account, f)

    def load_user(self):
        try:
            with open(USER_FILE, "r") as f:
                self.user = json.load(f)
        except FileNotFoundError:
            pass
        # set bearer token
        if self.user.get("apiToken"):
            self.api_session.headers["Authorization"] = f"Bearer {self.user["apiToken"]}"

        self.calculate_skin_hash()

    def calculate_skin_hash(self):
        user_data = self.user.get("user", {}).get("players", [{}])[0]
        skin_hash = user_data.get("skinUrl", "none").split("/")[-1].split(".")[0] if user_data.get("skinUrl") else "none"
        cape_hash = user_data.get("capeUrl", "none").split("/")[-1].split(".")[0] if user_data.get("capeUrl") else "none"
        self.skin_hash = hashlib.md5(f"{skin_hash}{cape_hash}".encode()).hexdigest()
            
    def save_user(self):
        with open(USER_FILE, "w") as f:
            json.dump(self.user, f)

    # /web/register
    def register(self, username: str, password: str):
        response = self.api_session.post(
            f"{self.base_url}/web/register",
            params={
                "playerName": username,
                "password": password,
                "returnUrl": "/web/registration",
            },
        )
        if response.cookies.get("__Host-browserToken"):
            # resp = self.__login(username, password)
            # if resp.status_code != 200:
            #     return resp.json()
            return True
            # return response.text.split('<p class="error-message">')[1].split("</p>")[0]
        elif response.cookies.get("__Host-errorMessage"):
            return response.cookies.get("__Host-errorMessage").replace("+", " ")
        else:
            return "Помилка сервера або відсутній інтернет"

    # /authenticate
    def login(self, username: str, password: str):
        response = self.yggdrasil_session.post(
            f"{self.base_url}/authenticate",
            json={
                "agent": {
                    "name": "Minecraft",
                    "version": 1,
                },
                "username": username,
                "password": password,
                "requestUser": True,
            },
        )
        if response.status_code != 200:
            return response
        response_json = response.json()

        self.account["access_token"] = response_json["accessToken"]
        self.account["client_token"] = response_json["clientToken"]
        self.account["username"] = response_json["selectedProfile"]["name"]
        
        self.save_account()

        resp = self.__login(username, password)
        if resp.status_code != 200:
            return resp
        return response

    # /refresh
    def refresh(self):
        response = self.yggdrasil_session.post(
            f"{self.base_url}/refresh",
            json={
                "accessToken": self.account["access_token"],
                "clientToken": self.account["client_token"],
                "requestUser": True,
            },
        )
        if response.status_code != 200:
            return "Помилка сервера або відсутній інтернет"
        response = response.json()

        self.account["access_token"] = response["accessToken"]
        self.account["client_token"] = response["clientToken"]
        self.save_account()

        return response

    # /validate
    def validate(self):
        if not self.account.get("access_token"):
            return False
        response = self.yggdrasil_session.post(
            f"{self.base_url}/validate",
            json={
                "accessToken": self.account["access_token"],
                "clientToken": self.account["client_token"],
            },
        )
        return response.status_code == 204

    # /signout
    def signout(self, password: str):
        response = self.yggdrasil_session.post(
            f"{self.base_url}/signout",
            json={
                "username": self.account["username"],
                "password": password,
            },
        )
        return response.status_code == 204

    # /invalidate
    def invalidate(self):
        response = self.yggdrasil_session.post(
            f"{self.base_url}/invalidate",
            json={
                "accessToken": self.account["access_token"],
                "clientToken": self.account["client_token"],
            },
        )
        self.account["access_token"] = ""
        self.account["client_token"] = ""
        self.save_account()
        return response.status_code == 204

    def logout(self):
        self.invalidate()
        self.account = {}
        self.user = {}
        self.skin_hash = None
        self.update_skin = None
        self.save_account()
        self.save_user()
        # remove skin file
        if os.path.exists(f"{SKINS_CACHE_FOLDER}/{self.skin_hash}-skin.png"):
            os.remove(f"{SKINS_CACHE_FOLDER}/{self.skin_hash}-skin.png")
        if os.path.exists(f"{SKINS_CACHE_FOLDER}/{self.skin_hash}-back.png"):
            os.remove(f"{SKINS_CACHE_FOLDER}/{self.skin_hash}-back.png")
        if os.path.exists(f"{SKINS_CACHE_FOLDER}/{self.skin_hash}-face.png"):
            os.remove(f"{SKINS_CACHE_FOLDER}/{self.skin_hash}-face.png")

    def __login(self, username, password):
        response = self.api_session.post(
            f"{self.base_url}/drasl/api/v2/login",
            json={
                "username": username,
                "password": password,
            },
        )
        if response.status_code != 200:
            return response
        self.user.update(response.json())
        self.update_skin = True
        self.save_user()
        self.api_session.headers["Authorization"] = f"Bearer {self.user["apiToken"]}"
        self.calculate_skin_hash()
        return response

    def get_user(self):
        response = self.api_session.get(f"{self.base_url}/drasl/api/v2/user")
        resp_json = response.json()
        if (
            self.user["user"]["players"][0]["skinUrl"] != resp_json["players"][0]["skinUrl"]
            or self.user["user"]["players"][0]["capeUrl"] != resp_json["players"][0]["capeUrl"]
        ):
            self.update_skin = True
        else:
            self.update_skin = False

        self.user["user"].update(resp_json)
        self.save_user()
        return True

    def update_user(self, data):
        response = self.api_session.patch(
            f"{self.base_url}/drasl/api/v2/user", json=data
        )
        return response

    def update_player(self, data):
        response = self.api_session.patch(
            f"{self.base_url}/drasl/api/v2/players/{self.user['user']['players'][0]['uuid']}",
            json=data,
        )
        if response.status_code != 200:
            return response
        response_json = response.json()
        self.user["user"]["players"][0].update(response_json)
        self.save_user()
        self.calculate_skin_hash()
        return response

    def delete_user(self):
        response = self.api_session.delete(f"{self.base_url}/drasl/api/v2/user")
        return response.text

    def is_valid_nickname(self, nickname):
        # only latin letters, numbers, and underscores, min 4, max 16
        return bool(re.match(r"^[a-zA-Z0-9_]{4,16}$", nickname))
    
    async def render_skin(self):
        if all(
            (
            os.path.exists(f"{SKINS_CACHE_FOLDER}/{self.skin_hash}-face.png"),
            os.path.exists(f"{SKINS_CACHE_FOLDER}/{self.skin_hash}-skin.png"),
            os.path.exists(f"{SKINS_CACHE_FOLDER}/{self.skin_hash}-back.png"),
            )
        ) and not self.update_skin:
            return

        player = Player(self.user["user"]["players"][0]["uuid"])
        await player.initialize()

        skin = player.skin
        skin_face = await skin.render_head(vr=0, hr=0)
        
        skin_full = await skin.render_skin(
            vr=-20, hr=30, vrll=30, vrrl=-30, vrla=-30, vrra=30, aa=True
        )
        skin_full_back = await skin.render_skin(
            vr=-20, hr=150, vrll=-30, vrrl=30, vrla=30, vrra=-30, aa=True
        )
        
        skin_face.save(f"{SKINS_CACHE_FOLDER}/{self.skin_hash}-face.png")
        skin_full.thumbnail((216, 392))
        skin_full_back.thumbnail((216, 392))
        skin_full.save(f"{SKINS_CACHE_FOLDER}/{self.skin_hash}-skin.png")
        skin_full_back.save(f"{SKINS_CACHE_FOLDER}/{self.skin_hash}-back.png")
        # skin_full.resize((216, 392)).save(f"{SKINS_CACHE_FOLDER}/{self.skin_hash}-skin.png")
        # skin_full_back.resize((216, 392)).save(f"{SKINS_CACHE_FOLDER}/{self.skin_hash}-back.png")
        
        # skin_face.save(f"{SKINS_CACHE_FOLDER}/{self.skin_hash}-face.png")
        # skin_full.save(f"{SKINS_CACHE_FOLDER}/{self.skin_hash}-skin.png")
        # skin_full_back.save(f"{SKINS_CACHE_FOLDER}/{self.skin_hash}-back.png")
        
        account.update_skin = False
        
account = Auth()
