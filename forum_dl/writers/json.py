# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

import os

from .common import Writer
from ..extractors.common import ForumExtractor, Board, ExtractorNode


class JsonWriter(Writer):
    def write(self, url: str):
        base_node = self._extractor.node_from_url(url)

        if isinstance(base_node, Board):
            self.write_board(base_node)
        else:
            os.makedirs(
                os.path.join(self._directory, *[str(id) for id in base_node.path[:-1]]),
                exist_ok=True,
            )

            with open(
                os.path.join(self._directory, *[str(id) for id in base_node.path]), "w"
            ) as file:
                self.write_item(base_node, file)

    def write_item(self, item: ExtractorNode, file: TextIO, indent: int = 0):
        file.write(indent * " " + "{\n")
        file.write(indent * " " + f' "path": "{item.path}",\n')
        file.write(indent * " " + f' "url": "{item.url}",\n')
        file.write(indent * " " + f' "title": "{item.title}",\n')
        file.write(indent * " " + f' "content": "{item.content}",\n')

        file.write(indent * " " + f' "items": [\n')

        for item in self._extractor.items(item):
            self.write_item(item, file, indent + 1)

        file.write(f" ],\n")
        file.write("},\n")

    def write_board(self, board: Board):
        os.makedirs(
            os.path.join(self._directory, *[str(id) for id in board.path]),
            exist_ok=True,
        )

        for item in self._extractor.items(board):
            with open(
                os.path.join(self._directory, *[str(id) for id in item.path]), "w"
            ) as file:
                self.write_item(item, file)

        for _, subboard in self._extractor.subboards(board).items():
            self.write_board(subboard)
