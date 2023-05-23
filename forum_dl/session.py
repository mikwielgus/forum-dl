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
import time
import logging

from .exceptions import SearchError
from .version import __version__

if TYPE_CHECKING:
    from requests import Response


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


@dataclass  # (kw_only=True)
class SessionOptions:
    warc_output: str
    user_agent: str
    get_urls: bool


class Session:
    def __init__(self, options: SessionOptions):
        self._warc_file = None

        if options.warc_output:
            from warcio.warcwriter import WARCWriter
            from warcio.capture_http import capture_http

            self._capture_http = capture_http
            self._warc_file = open(options.warc_output, "wb")
            self._warc_writer = WARCWriter(self._warc_file)

        # For the `warcio` recording to work, `requests` must be imported only after `capture_http`.
        import requests

        self._session = requests.Session()
        self._options = options
        self._cache: dict[tuple[str, dict[str, Any]], requests.Response] = {}

        self.delay = 1
        self.attempts = 0

    def __del__(self):
        if self._warc_file:
            self._warc_file.close()

    def get(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
        should_cache: bool = False,
        should_retry: bool = True,
        **kwargs: Any,
    ):
        response = self.try_get(
            url,
            params=params,
            headers=headers,
            should_cache=should_cache,
            should_retry=should_retry,
            **kwargs,
        )
        response.raise_for_status()

        return response

    def try_get(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
        should_cache: bool = False,
        should_retry: bool = True,
        **kwargs: Any,
    ) -> Response:
        frozen_params = frozenset(params.items()) if params else frozenset()

        if (url, frozen_params) in self._cache:
            cached_response = self._cache[(url, frozen_params)]

            if not should_cache:
                del self._cache[(url, params)]

            return cached_response

        if should_retry:
            response = self._retrying_get(url, params=params, headers=headers, **kwargs)
        else:
            response = self._do_get(url, params=params, headers=headers, **kwargs)

        if should_cache:
            self._cache[(url, frozen_params)] = response

        return response

    def _after_retry(self):
        logging.warning(f"Waiting {self.delay} seconds.")

    @retry(
        reraise=True,
        wait=wait_random_exponential(multiplier=5),
        stop=stop_after_attempt(5),
        before_sleep=before_sleep_log(logging.getLogger(), logging.WARNING),
    )
    def _retrying_get(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
        **kwargs: Any,
    ):
        return self._do_get(url, params=params, headers=headers, **kwargs)

    def _do_get(
        self,
        url: str,
        *,
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

        if self._warc_file:
            with self._capture_http(self._warc_writer):
                return self._session.get(url, params=params, headers=headers, **kwargs)
        else:
            return self._session.get(url, params=params, headers=headers, **kwargs)
