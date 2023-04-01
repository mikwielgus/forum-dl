# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore


class ForumDlException(Exception):
    pass


class NoExtractorError(ForumDlException):
    pass


class TagSearchError(ForumDlException):
    pass


class AttributeSearchError(ForumDlException):
    pass


class PropertyError(ForumDlException):
    pass
