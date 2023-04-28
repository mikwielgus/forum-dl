# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

import dataclasses
import json

from ..extractors.common import Board, Thread, Post
from .common import FileWriter


class JsonlWriter(FileWriter):
    def _serialize_board(self, board: Board):
        return json.dumps(dataclasses.asdict(board))

    def _serialize_thread(self, thread: Thread):
        return json.dumps(dataclasses.asdict(thread))

    def _serialize_post(self, post: Post):
        return json.dumps(dataclasses.asdict(post))
