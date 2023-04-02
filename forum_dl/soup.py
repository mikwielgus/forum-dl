# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from .exceptions import TagSearchError, AttributeSearchError, PropertyError
import bs4

SoupInput = Callable[[Any], bool] | Pattern[str] | str | None


class Soup:
    def __init__(self, markup: str | bytes):
        self._soup = bs4.BeautifulSoup(markup, "html.parser")

    def try_find(
        self,
        name: SoupInput | None = None,
        attrs: dict[str, Any] = {},
        recursive: bool = True,
        string: SoupInput | None = None,
        **kwargs: Any,
    ) -> SoupTag | None:
        result = self._soup.find(name, attrs, recursive, string, **kwargs)

        if result is not None and not isinstance(result, bs4.element.Tag):
            raise TagSearchError

        if result:
            return SoupTag(result)

    def find(
        self,
        name: SoupInput | None = None,
        attrs: dict[str, Any] = {},
        recursive: bool = True,
        string: SoupInput | None = None,
        **kwargs: Any,
    ) -> SoupTag:
        result = self.try_find(name, attrs, recursive, string, **kwargs)

        if not result:
            raise TagSearchError

        return result

    def find_all(
        self,
        name: SoupInput | None = None,
        attrs: dict[str, Any] = {},
        recursive: bool = True,
        string: SoupInput | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> list[SoupTag]:
        result = self._soup.find_all(name, attrs, recursive, string, limit, **kwargs)

        return [SoupTag(tag) for tag in result]


class SoupTag:
    def __init__(self, tag: bs4.element.Tag):
        self._tag = tag

    def try_find(
        self,
        name: SoupInput | None = None,
        attrs: dict[str, Any] = {},
        recursive: bool = True,
        string: SoupInput | None = None,
        **kwargs: Any,
    ) -> SoupTag | None:
        result = self._tag.find(name, attrs, recursive, string, **kwargs)

        if result is not None and not isinstance(result, bs4.element.Tag):
            raise TagSearchError

        if result:
            return SoupTag(result)

    def find(
        self,
        name: SoupInput | None = None,
        attrs: dict[str, Any] = {},
        recursive: bool = True,
        string: SoupInput | None = None,
        **kwargs: Any,
    ):
        result = self.try_find(name, attrs, recursive, string, **kwargs)

        if not result:
            raise TagSearchError

        return result

    def find_all(
        self,
        name: SoupInput | None = None,
        attrs: dict[str, Any] = {},
        recursive: bool = True,
        string: SoupInput | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ):
        result = self._tag.find_all(name, attrs, recursive, string, limit, **kwargs)

        return [SoupTag(tag) for tag in result]

    def find_next(
        self,
        name: SoupInput | None = None,
        attrs: dict[str, Any] = {},
        string: SoupInput | None = None,
        **kwargs: Any,
    ):
        result = self._tag.find_next(name, attrs, string, **kwargs)

        if not isinstance(result, bs4.element.Tag):
            raise TagSearchError

        return SoupTag(result)

    def find_previous(
        self,
        name: SoupInput | None = None,
        attrs: dict[str, Any] = {},
        string: SoupInput | None = None,
        **kwargs: Any,
    ):
        result = self._tag.find_previous(name, attrs, string, **kwargs)

        if not isinstance(result, bs4.element.Tag):
            raise TagSearchError

        return SoupTag(result)

    def get(self, key: str, default: SoupInput | None = None) -> str:
        result = self._tag.get(key, default)

        if not isinstance(result, str):
            raise AttributeSearchError

        return result

    def get_list(self, key: str, default: SoupInput | None = None) -> list[str]:
        result = self._tag.get(key, default)

        if not isinstance(result, list):
            raise AttributeSearchError

        return result

    def encode_contents(self):
        # TODO: Error handling?
        return self._tag.encode_contents()

    @property
    def string(self):
        if not self._tag.string:
            raise PropertyError

        return self._tag.string

    @property
    def contents(self):
        if not self._tag.contents:
            raise PropertyError

        return self._tag.contents

    @property
    def parents(self):
        return self._tag.parents

    @property
    def next_sibling(self):
        return self._tag.next_sibling

    @property
    def previous_sibling(self):
        return self._tag.previous_sibling
