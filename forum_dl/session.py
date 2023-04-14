# type: ignore
from __future__ import annotations
from typing import *  # type: ignore

from functools import lru_cache, wraps
import requests
import time


def hash_dict(func):
    class hashdict(dict):
        def __hash__(self):
            return hash(frozenset(self.items()))

    @wraps(func)
    def wrapped(*args, **kwargs):
        args = tuple([hashdict(arg) if isinstance(arg, dict) else arg for arg in args])
        kwargs = {
            k: hashdict(v) if isinstance(v, dict) else v for k, v in kwargs.items()
        }
        return func(*args, **kwargs)

    return wrapped


class Session:
    def __init__(self):
        self._session = requests.Session()
        self.delay = 1
        self.attempts = 0

    @hash_dict
    @lru_cache(maxsize=1024)
    def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
        **kwargs: Any,
    ):
        print(url)
        if not headers:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.85 Safari/537.36"
            }

        return self._get(url, params, headers, **kwargs)

    def uncached_get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
        **kwargs: Any,
    ):
        print(url)
        if not headers:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.85 Safari/537.36"
            }

        return self._get(url, params, headers, **kwargs)

    def _get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
        **kwargs: Any,
    ):
        while True:
            response = self._session.get(url, params=params, headers=headers, **kwargs)

            if response.status_code != 200 and response.status_code != 403:
                # FIXME.
                print(f"Waiting {self.delay} seconds.")
                time.sleep(self.delay)

                self.attempts += 1

                if self.attempts >= 3:
                    self.delay *= 2
                    self.attempts = 0
            else:
                self.attempts = 0
                return response
