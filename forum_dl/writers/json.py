# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

import os

from .common import Writer
from ..extractors.common import Board, Thread, Post


class JsonWriter(Writer):
    def write(self, url: str):
        base_node = self._extractor.node_from_url(url)

        if isinstance(base_node, Board):
            self.write_board(base_node)

    def write_board(self, board: Board):
        os.makedirs(
            os.path.join(self._path, *[str(id) for id in board.path]),
            exist_ok=True,
        )

        for thread in self._extractor.threads(board):
            with open(
                os.path.join(self._path, *[str(id) for id in thread.path]), "w"
            ) as file:
                self.write_thread(item, file)

        for _, subboard in self._extractor.subboards(board).items():
            self.write_board(subboard)

    def write_thread(self, thread: Thread, file: TextIO):
        for post in self._extractor.posts(thread):
            self.write_post(post, file)

    def write_post(self, post: Post, file: TextIO):
        file.write("{\n")
        file.write(f' "path": "{item.path}",\n')
        file.write(f' "url": "{item.url}",\n')
        file.write(f' "title": "{item.title}",\n')
        file.write(f' "content": "{item.content}",\n')

        file.write(f' "items": [\n')

        file.write(f" ],\n")
        file.write("},\n")
