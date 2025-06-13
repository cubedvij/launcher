import httpx

from config import STATS_URL, STATS_API_VERSION


class Stats:
    def __init__(self):
        self._api_url = f"{STATS_URL}/{STATS_API_VERSION}"
        self._client = httpx.AsyncClient(base_url=self._api_url)
        
    async def get_player_stats(self, uuid: str):
        """
        Fetch player stats by UUID.
        """
        response = await self._client.get(
            "/player",
            params={"player": uuid}
        )
        # Raise an error if the request was unsuccessful
        if response.status_code == 403:
            # rate limit exceeded
            return None
        return response.json()
    

stats = Stats()