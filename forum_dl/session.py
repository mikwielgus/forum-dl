# type: ignore
from __future__ import annotations
from typing import *  # type: ignore

from dataclasses import dataclass
from functools import lru_cache, wraps
from tenacity import (
    retry,
    wait_random_exponential,
    stop_after_attempt,
    before_sleep_log,
)
import requests
import time
import logging

from .exceptions import SearchError
from .version import __version__


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


@dataclass(kw_only=True)
class SessionOptions:
    user_agent: str
    get_urls: bool


class Session:
    def __init__(self, options: SessionOptions):
        self._session = requests.Session()
        self._options = options
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
        if self._options.get_urls:
            print(url)
        else:
            logging.info(f"GET {url}")

        if not headers:
            headers = {"User-Agent": self._options.user_agent}

        return self._get(url, params, headers, **kwargs)

    def uncached_get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
        **kwargs: Any,
    ):
        if self._options.get_urls:
            print(url)
        else:
            logging.info(f"GET (uncached) {url}")

        if not headers:
            headers = {"User-Agent": self._options.user_agent}

        return self._get(url, params, headers, **kwargs)

    def get_noretry(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
        **kwargs: Any,
    ):
        response = self._session.get(url, params=params, headers=headers, **kwargs)

        if response.status_code != 200:
            raise SearchError

        return response

    def try_get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
        **kwargs: Any,
    ):
        return self._session.get(url, params=params, headers=headers, **kwargs)

    def _after_retry(self):
        logging.warning(f"Waiting {self.delay} seconds.")

    @retry(
        reraise=True,
        wait=wait_random_exponential(multiplier=5),
        stop=stop_after_attempt(5),
        before_sleep=before_sleep_log(logging.getLogger(), logging.WARNING),
    )
    def _get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
        **kwargs: Any,
    ):
        response = self.try_get(url, params=params, headers=headers, **kwargs)

        if response.status_code != 200 and response.status_code != 403:
            raise RetryError

        return response
