"""
firebase_client.py

Cienka warstwa nad REST API Firebase Realtime Database.
Dzieki temu wszystkie dane bota (obywatele, podania, ustawienia wyborow)
zyja poza serwerem Render i przetrwaja kazdy redeploy / restart.

Kazdy nieudany zapis/odczyt jest logowany razem z kodem HTTP i trescia
odpowiedzi Firebase, zeby od razu bylo widac prawdziwa przyczyne
(np. zle skonfigurowany FIREBASE_URL albo reguly bazy blokujace zapis).
"""

import logging

import aiohttp

import config

log = logging.getLogger("obywatel-bot.firebase")


def _url(path: str) -> str:
    suffix = f"?auth={config.FIREBASE_SECRET}" if config.FIREBASE_SECRET else ""
    return f"{config.FIREBASE_URL}/{path}.json{suffix}"


async def _log_error(method: str, path: str, resp: aiohttp.ClientResponse) -> None:
    body = await resp.text()
    log.error(
        "Firebase %s %s zwrocilo status %s. Odpowiedz: %s",
        method, path, resp.status, body[:500],
    )


async def get(path: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(_url(path)) as resp:
            if resp.status != 200:
                await _log_error("GET", path, resp)
                return None
            return await resp.json()


async def put(path: str, value) -> bool:
    async with aiohttp.ClientSession() as session:
        async with session.put(_url(path), json=value) as resp:
            if resp.status != 200:
                await _log_error("PUT", path, resp)
                return False
            return True


async def patch(path: str, value) -> bool:
    async with aiohttp.ClientSession() as session:
        async with session.patch(_url(path), json=value) as resp:
            if resp.status != 200:
                await _log_error("PATCH", path, resp)
                return False
            return True


async def delete(path: str) -> bool:
    async with aiohttp.ClientSession() as session:
        async with session.delete(_url(path)) as resp:
            if resp.status != 200:
                await _log_error("DELETE", path, resp)
                return False
            return True


async def push(path: str, value) -> str | None:
    """Odpowiednik Firebase `push()` - generuje unikalny klucz i zwraca go."""
    async with aiohttp.ClientSession() as session:
        async with session.post(_url(path), json=value) as resp:
            if resp.status != 200:
                await _log_error("POST", path, resp)
                return None
            data = await resp.json()
            return data.get("name") if data else None
