# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

import dataclasses
import json

from ..extractors.common import Post
from .common import FilesystemWriter


class JsonlWriter(FilesystemWriter):
    def _serialize_post(self, post: Post):
        return json.dumps(dataclasses.asdict(post))
