# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from urllib.parse import urljoin
from datetime import datetime

import zstandard
import json
import io

from .common import (
    Extractor,
    ExtractorOptions,
    Board,
    Thread,
    NullThread,
    Post,
    PageState,
)
from ..session import Session


class PushshiftExtractor(Extractor):
    @staticmethod
    def _detect(session: Session, url: str, options: ExtractorOptions):
        # with open(url, "rb") as file:
        # decompressor = zstandard.ZstdDecompressor(max_window_size=2147483648)
        # stream_reader = decompressor.stream_reader(file)
        # stream = io.TextIOWrapper(stream_reader, encoding="utf-8")

        # line = stream.readline()
        # data = json.loads(line)

        paths = url.split(",")
        return PushshiftExtractor(session, url, options, paths[0], paths[1])

    def __init__(
        self,
        session: Session,
        base_url: str,
        options: ExtractorOptions,
        submissions_path: str,
        comments_path: str,
    ):
        super().__init__(session, base_url, options)
        self._submissions_path = submissions_path
        self._comments_path = comments_path
        self._post_subpaths: list[tuple[str, ...]] = []

    def _fetch_top_boards(self):
        pass

    def _do_fetch_subboards(self, board: Board):
        pass

    def _get_node_from_url(self, url: str):
        return self.root

    def _fetch_lazy_subboard(self, board: Board, subboard_id: str):
        pass

    def _fetch_lazy_subboards(self, board: Board):
        yield from ()

    def _fetch_board_page_threads(self, board: Board, state: PageState):
        with open(self._submissions_path, "rb") as submissions_file:
            decompressor = zstandard.ZstdDecompressor(max_window_size=2147483648)
            stream_reader = decompressor.stream_reader(submissions_file)
            submissions_stream = io.TextIOWrapper(stream_reader, encoding="utf-8")

            for line in submissions_stream:
                data = json.loads(line)
                assert "num_comments" in data

                yield Thread(
                    path=(data["id"],),
                    url=data["permalink"],
                    origin=self.base_url,
                    data=data,
                    title=data["title"],
                )

        yield NullThread(path=(), url="", origin="", data={}, title="")

    def _fetch_thread_page_posts(self, thread: Thread, state: PageState):
        if isinstance(thread, NullThread):
            with open(self._comments_path, "rb") as comments_file:
                decompressor = zstandard.ZstdDecompressor(max_window_size=2147483648)
                stream_reader = decompressor.stream_reader(comments_file)
                comments_stream = io.TextIOWrapper(stream_reader, encoding="utf-8")

                for line in comments_stream:
                    data = json.loads(line)

                    for parent_subpath in self._post_subpaths:
                        if parent_subpath[-1] == data["parent_id"][3:]:
                            break
                    else:
                        continue

                    subpath = parent_subpath + (str(data["id"]),)
                    self._post_subpaths.append(subpath)

                    if "permalink" in data:
                        url = urljoin("https://old.reddit.com/", data["permalink"])
                    else:
                        url = ""

                    yield Post(
                        path=thread.path,
                        subpath=subpath,
                        url=url,
                        origin=self.base_url,
                        data=data,
                        author=data["author"],
                        creation_time=datetime.utcfromtimestamp(
                            float(data["created_utc"]),
                        ),
                        content=data["body"],
                    )

        else:
            subpath = (thread.data["id"],)
            self._post_subpaths.append(subpath)
            yield Post(
                path=thread.path,
                subpath=subpath,
                url=thread.data["permalink"],
                origin=self.base_url,
                data=thread.data,
                author=thread.data["author"],
                creation_time=datetime.utcfromtimestamp(
                    float(thread.data["created_utc"])
                ),
                content="\n\n".join(
                    filter(None, [thread.data.get("url"), thread.data.get("selftext")])
                ),
            )
