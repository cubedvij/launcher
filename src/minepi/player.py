import asyncio
import base64
import json
from io import BytesIO
from typing import Optional

import httpx
from PIL import Image

from .skin import Skin
from .utils import (
    name_to_uuid,
    uuid_to_undashed,
)
from .errors import InvalidPlayer


class Player:
    """Class representing a minecraft player
    This has to be created before a skin can be rendered

    Parameters
    ----------
    uuid: str
        UUID of the player (Not needed if name is given
    name: str
        Username of the player (Not needed if UUID is given)
    raw_skin: PIL.Image.Image
        Raw skin image of the player (64x64px)
    raw_cape: PIL.Image.Image
        Raw cape image of the player (64x32px)
    session: httpx.AsyncClient
        AsyncClient to use for requests
    """

    def __init__(
        self,
        uuid: str = None,
        name: str = None,
        raw_skin: Image.Image = None,
        raw_cape: Image.Image = None,
        session: httpx.AsyncClient = None,
    ):
        if uuid is None and name is None:
            raise ValueError("Pass a username or UUID")

        self._uuid: Optional[str] = uuid
        self._username: Optional[str] = name

        self._skin: Optional[Skin] = None
        self._raw_skin: Optional[Image.Image] = raw_skin
        self._raw_capes: dict = {
            "default": raw_cape,
            "mojang": None,
        }

        self._session: Optional[httpx.AsyncClient] = session
        self._close_session: bool = False

        self._ready: asyncio.Event = asyncio.Event()
        if self._uuid:
            self._uuid = uuid_to_undashed(self._uuid)

            if len(self._uuid) != 32:
                raise ValueError("UUID seems to be invalid.")

    def __repr__(self):
        return f"<Player (UUID={self.uuid}) (name={self.name}) (skin={self._skin})>"

    @property
    def uuid(self):
        """The players UUID\n
        Either passed when creating this class or fetched from the MojangAPI"""
        return self._uuid

    @property
    def name(self):
        """The players name"""
        return self._username

    @property
    def skin(self):
        """The players :class:`Skin`"""
        return self._skin

    @property
    def capes(self):
        """A dict representing this player's capes"""
        return self._raw_capes

    @property
    def minecraftcapes_cape(self):
        """The player's MinecraftCapes cape"""
        return self._raw_capes["minecraftcapes"]

    def set_skin(self, skin: "Skin"):
        """Manually overwrite/set this players skin

        Parameters
        ----------
        skin: Skin
            The new skin
        """
        self._skin = skin

    async def initialize(self):
        """Initializes the player class

        This function is an initializer which helps to get various details about the player with just one method.
        Once this function has finished running, the corresponding :py:class:`Player` object is
        guaranteed to have a name, UUID and skin (includes the cape if available) associated to it
        (if the given username and/or UUID is valid of course).

        Warning
        -------
        This function does one to four API calls to the mojang API:
            -> (1.) Obtain the players UUID by name (Only if no UUID is given)\n
            -> 2. Get the players profile\n
            -> (3.) Get the players skin (Only if no skin is given)\n
            -> (4.) Get the players cape (Only if the player actually has a cape)\n
        Rate limits of the API are unknown but expected to be somewhere close to 6000 requests per 10 minutes.

        Raises
        ------
        errors.InvalidPlayer
            Player does not seem to be valid
        """
        if not self._session:
            self._session = httpx.AsyncClient()
            self._close_session = True

        if self._uuid is None:
            uuid = await name_to_uuid(self._username, self._session)
            if uuid:
                self._uuid = uuid_to_undashed(uuid)

        textures = None
        if self._uuid is not None and (
            self._raw_skin is None or self._raw_capes["default"] is None
        ):
            resp = await self._session.get(
                f"https://auth.cubedvij.pp.ua/session/minecraft/profile/{self._uuid}"
            )
            if resp.status_code == 200:
                resp_dict = resp.json()
                self._username = (
                    resp_dict["name"] if self._username is None else self._username
                )
                for p in resp_dict["properties"]:
                    if p["name"] == "textures":
                        textures = json.loads(base64.b64decode(p["value"]))["textures"]
                        break
                else:
                    raise InvalidPlayer()

        if textures is not None:
            _raw_skin_url = textures["SKIN"]["url"]
            _raw_cape_url = (
                textures["CAPE"]["url"] if "CAPE" in textures.keys() else None
            )

            if not self._raw_skin:
                # async with self._session.get(_raw_skin_url) as resp:
                #     self._raw_skin = Image.open(BytesIO(await resp.read()))
                resp = await self._session.get(_raw_skin_url)
                if resp.status_code == 200:
                    self._raw_skin = Image.open(BytesIO(resp.read()))
                else:
                    self._raw_skin = None
                

            if not self._raw_capes["default"]:
                if _raw_cape_url is not None:
                    # async with self._session.get(_raw_cape_url) as resp:
                    #     self._raw_capes["default"] = Image.open(
                    #         BytesIO(await resp.read())
                    #     )
                    #     self._raw_capes["mojang"] = self._raw_capes["default"]
                    resp = await self._session.get(_raw_cape_url)
                    if resp.status_code == 200:
                        self._raw_capes["default"] = Image.open(BytesIO(resp.read()))
                        self._raw_capes["mojang"] = self._raw_capes["default"]
                    else:
                        self._raw_capes["default"] = None
                else:
                    self._raw_capes["default"] = None

            self._skin = Skin(
                raw_skin=self._raw_skin,
                raw_skin_url=_raw_skin_url,
                raw_cape=self._raw_capes["default"],
                raw_cape_url=_raw_cape_url,
            )

        if self._close_session:
            await self._session.aclose()

        self._ready.set()

    async def wait_for_fully_constructed(self):
        """Returns as soon as the initialize function finished

        Waiting for this guarantees that the skin has been fetched from the api"""
        try:
            await asyncio.wait_for(self._ready.wait(), timeout=60)
        except asyncio.TimeoutError:
            raise asyncio.TimeoutError
