# pyright: ignore
from __future__ import annotations
from typing import *  # type: ignore

from functools import lru_cache, wraps
import requests


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


class CachedSession:
    def __init__(self):
        self._session = requests.Session()

    @hash_dict
    @lru_cache(maxsize=1024)
    def get(
        self,
        url,
        params: dict[str, Any] = None,
        headers: dict[str, Any] = None,
        **kwargs,
    ):
        print(url)
        if not headers:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.85 Safari/537.36"
            }

        return self._session.get(url, params=params, headers=headers, **kwargs)
