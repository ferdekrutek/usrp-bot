"""
firebase_client.py

Cienka warstwa nad REST API Firebase Realtime Database.
Dzięki temu wszystkie dane bota (obywatele, podania, ustawienia wyborów)
żyją poza serwerem Render i przetrwają każdy redeploy / restart.
"""

import aiohttp

import config


def _url(path: str) -> str:
    suffix = f"?auth={config.FIREBASE_SECRET}" if config.FIREBASE_SECRET else ""
    return f"{config.FIREBASE_URL}/{path}.json{suffix}"


async def get(path: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(_url(path)) as resp:
            if resp.status != 200:
                return None
            return await resp.json()


async def put(path: str, value) -> bool:
    async with aiohttp.ClientSession() as session:
        async with session.put(_url(path), json=value) as resp:
            return resp.status == 200


async def patch(path: str, value) -> bool:
    async with aiohttp.ClientSession() as session:
        async with session.patch(_url(path), json=value) as resp:
            return resp.status == 200


async def delete(path: str) -> bool:
    async with aiohttp.ClientSession() as session:
        async with session.delete(_url(path)) as resp:
            return resp.status == 200


async def push(path: str, value) -> str | None:
    """Odpowiednik Firebase `push()` — generuje unikalny klucz i zwraca go."""
    async with aiohttp.ClientSession() as session:
        async with session.post(_url(path), json=value) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            return data.get("name") if data else None
