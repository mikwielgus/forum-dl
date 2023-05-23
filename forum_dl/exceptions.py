# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore


class ForumDlException(Exception):
    pass


class ExtractorNotFoundError(ForumDlException):
    pass


class WriterNotFoundError(ForumDlException):
    pass


class CrawlError(ForumDlException):
    pass


class SearchError(ForumDlException):
    pass


class TagSearchError(SearchError):
    pass


class AttributeSearchError(SearchError):
    pass


class PropertyError(SearchError):
    pass
