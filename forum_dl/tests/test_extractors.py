# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from .. import extractors
from ..extractors.common import ForumExtractor, Board
from ..cached_session import CachedSession

import itertools
import hashlib
import pytest


@pytest.mark.parametrize("cls", extractors.list_classes())
def test_extractors(cls: Type[ForumExtractor]):
    session = CachedSession()

    for test in cls.tests:
        url = test.pop("url")
        print(f"url: {url}")

        extractor = cls.detect(session, url)

        assert isinstance(extractor, cls)

        if test_base_url := test.pop("test_base_url", None):
            assert extractor._base_url == test_base_url

        extractor.fetch()

        base_node = extractor.node_from_url(url)

        if test_boards := test.pop("test_boards", None):
            assert isinstance(base_node, Board)

            boards = list(
                itertools.islice(
                    extractor.subboards(base_node), test.pop("board_count", None)
                )
            )
            print(f"boards: {boards}")

            for path, test_board in test_boards.items():
                board = extractor.find_board(path)
                assert list(path) == board.path

                if test_title := test_board.pop("title"):
                    assert board.title == test_title

                if test_content := test_board.pop("content", None):
                    assert board.content == test_content

                assert not test_board

        items = list(
            itertools.islice(extractor.items(base_node), test.pop("item_count", None))
        )
        print(f"items: {items}")

        if test_items := test.pop("test_items", None):
            for i, item in enumerate(items):
                if test_item := test_items.pop(i, None):
                    print(i, test_item)

                    if test_title := test_item.pop("title"):
                        assert item.title == test_title

                    if test_path := test_item.pop("path"):
                        assert item.path == test_path

                    assert not test_item

            assert not test_items

        if test_item_count := test.pop("test_item_count", None):
            assert len(items) == test_item_count

        if test_min_item_count := test.pop("test_min_item_count", None):
            assert len(items) >= test_min_item_count

        contents = [item.content for item in items]
        hash = hashlib.sha1("\0".join(contents).encode("utf-8")).hexdigest()
        print(f"hash: {hash}")

        if test_contents_hash := test.pop("test_contents_hash", None):
            assert hash == test_contents_hash

        assert not test
