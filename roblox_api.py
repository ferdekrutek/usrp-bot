"""
roblox_api.py

Sprawdza, czy podana nazwa użytkownika istnieje na Robloxie, korzystając
z publicznego, oficjalnego endpointu Roblox (nie wymaga klucza API).
"""

import aiohttp

ROBLOX_USERNAMES_ENDPOINT = "https://users.roblox.com/v1/usernames/users"


async def lookup_roblox_user(username: str):
    """
    Zwraca dict {"id": int, "name": str} jeśli użytkownik istnieje,
    w przeciwnym razie None.
    """
    payload = {"usernames": [username], "excludeBannedUsers": True}

    async with aiohttp.ClientSession() as session:
        async with session.post(ROBLOX_USERNAMES_ENDPOINT, json=payload) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            results = data.get("data") or []
            if not results:
                return None
            return {"id": results[0]["id"], "name": results[0]["name"]}
