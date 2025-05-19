import asyncio
import re
import os
import json
import httpx
import hashlib

from minepi import Player
from config import AUTH_URL, ACCOUNT_FILE, USER_FILE, SKINS_CACHE_FOLDER


class Auth:
    def __init__(self):
        self.base_url = AUTH_URL
        self.account = {}
        self.user = {}
        self.update_skin = False
        self.skin_hash = None
        self.yggdrasil_session = httpx.Client()
        self.api_session = httpx.Client()
        self.load_account()
        self.load_user()

    def load_account(self):
        if os.path.exists(ACCOUNT_FILE):
            with open(ACCOUNT_FILE, "r") as f:
                self.account = json.load(f)

    def save_account(self):
        with open(ACCOUNT_FILE, "w") as f:
            json.dump(self.account, f)

    def load_user(self):
        if os.path.exists(USER_FILE):
            with open(USER_FILE, "r") as f:
                self.user = json.load(f)
        token = self.user.get("apiToken")
        if token:
            self.api_session.headers["Authorization"] = f"Bearer {token}"
        self.calculate_skin_hash()

    def calculate_skin_hash(self):
        player = self.user.get("user", {}).get("players", [{}])[0]
        skin_hash = player.get("skinUrl", "").split("/")[-1].split(".")[0] if player.get("skinUrl") else "none"
        cape_hash = player.get("capeUrl", "").split("/")[-1].split(".")[0] if player.get("capeUrl") else "none"
        self.skin_hash = hashlib.md5(f"{skin_hash}{cape_hash}".encode()).hexdigest()

    def save_user(self):
        with open(USER_FILE, "w") as f:
            json.dump(self.user, f)

    def register(self, username: str, password: str):
        resp = self.api_session.post(
            f"{self.base_url}/web/register",
            params={
                "playerName": username,
                "password": password,
                "returnUrl": "/web/registration",
            },
        )
        if resp.cookies.get("__Host-browserToken"):
            return True
        err = resp.cookies.get("__Host-errorMessage")
        if err:
            return err.replace("+", " ")
        return "Помилка сервера або відсутній інтернет"

    def login(self, username: str, password: str):
        resp = self.yggdrasil_session.post(
            f"{self.base_url}/authenticate",
            json={
                "agent": {"name": "Minecraft", "version": 1},
                "username": username,
                "password": password,
                "requestUser": True,
            },
        )
        if resp.status_code != 200:
            return resp
        data = resp.json()
        self.account.update({
            "access_token": data["accessToken"],
            "client_token": data["clientToken"],
            "username": data["selectedProfile"]["name"],
        })
        self.save_account()
        api_resp = self.__login(username, password)
        if api_resp.status_code != 200:
            return api_resp
        return resp

    def refresh(self):
        resp = self.yggdrasil_session.post(
            f"{self.base_url}/refresh",
            json={
                "accessToken": self.account.get("access_token"),
                "clientToken": self.account.get("client_token"),
                "requestUser": True,
            },
        )
        if resp.status_code != 200:
            return "Помилка сервера або відсутній інтернет"
        data = resp.json()
        self.account.update({
            "access_token": data["accessToken"],
            "client_token": data["clientToken"],
        })
        self.save_account()
        return data

    async def avalidate(self):
        return await asyncio.to_thread(self.validate)

    def validate(self):
        token = self.account.get("access_token")
        if not token:
            return False
        resp = self.yggdrasil_session.post(
            f"{self.base_url}/validate",
            json={
                "accessToken": token,
                "clientToken": self.account.get("client_token"),
            },
        )
        return resp.status_code == 204

    def signout(self, password: str):
        resp = self.yggdrasil_session.post(
            f"{self.base_url}/signout",
            json={
                "username": self.account.get("username"),
                "password": password,
            },
        )
        return resp.status_code == 204

    def invalidate(self):
        resp = self.yggdrasil_session.post(
            f"{self.base_url}/invalidate",
            json={
                "accessToken": self.account.get("access_token"),
                "clientToken": self.account.get("client_token"),
            },
        )
        self.account["access_token"] = ""
        self.account["client_token"] = ""
        self.save_account()
        return resp.status_code == 204

    def logout(self):
        self.invalidate()
        self.account.clear()
        self.user.clear()
        old_skin_hash = self.skin_hash
        self.skin_hash = None
        self.update_skin = False
        self.save_account()
        self.save_user()
        if old_skin_hash:
            for suffix in ("-skin.png", "-back.png", "-face.png"):
                path = f"{SKINS_CACHE_FOLDER}/{old_skin_hash}{suffix}"
                if os.path.exists(path):
                    os.remove(path)

    def __login(self, username, password):
        resp = self.api_session.post(
            f"{self.base_url}/drasl/api/v2/login",
            json={"username": username, "password": password},
        )
        if resp.status_code != 200:
            return resp
        self.user.update(resp.json())
        self.update_skin = True
        self.save_user()
        self.api_session.headers["Authorization"] = f"Bearer {self.user.get('apiToken', '')}"
        self.calculate_skin_hash()
        return resp

    async def aget_user(self):
        return await asyncio.to_thread(self.get_user)

    def get_user(self):
        resp = self.api_session.get(f"{self.base_url}/drasl/api/v2/user")
        data = resp.json()
        player = self.user.get("user", {}).get("players", [{}])[0]
        new_player = data.get("players", [{}])[0]
        self.update_skin = (
            player.get("skinUrl") != new_player.get("skinUrl") or
            player.get("capeUrl") != new_player.get("capeUrl")
        )
        self.user.setdefault("user", {}).update(data)
        self.save_user()
        return True

    def update_user(self, data):
        return self.api_session.patch(
            f"{self.base_url}/drasl/api/v2/user", json=data
        )

    def update_player(self, data):
        uuid = self.user.get("user", {}).get("players", [{}])[0].get("uuid")
        resp = self.api_session.patch(
            f"{self.base_url}/drasl/api/v2/players/{uuid}",
            json=data,
        )
        if resp.status_code != 200:
            return resp
        self.user["user"]["players"][0].update(resp.json())
        self.save_user()
        self.calculate_skin_hash()
        return resp

    def delete_user(self):
        resp = self.api_session.delete(f"{self.base_url}/drasl/api/v2/user")
        return resp.text

    def is_valid_nickname(self, nickname):
        return bool(re.match(r"^[a-zA-Z0-9_]{4,16}$", nickname))

    async def render_skin(self):
        skin_files = [
            f"{SKINS_CACHE_FOLDER}/{self.skin_hash}-face.png",
            f"{SKINS_CACHE_FOLDER}/{self.skin_hash}-skin.png",
            f"{SKINS_CACHE_FOLDER}/{self.skin_hash}-back.png",
        ]
        if all(os.path.exists(f) for f in skin_files) and not self.update_skin:
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
        skin_face.save(skin_files[0])
        skin_full.thumbnail((216, 392))
        skin_full_back.thumbnail((216, 392))
        skin_full.save(skin_files[1])
        skin_full_back.save(skin_files[2])
        self.update_skin = False

account = Auth()
