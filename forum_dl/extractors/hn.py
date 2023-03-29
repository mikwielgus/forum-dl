# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse, urlunparse, parse_qs
import bs4
import re

from .common import normalize_url
from .common import ForumExtractor, Board, Thread, Post
from ..cached_session import CachedSession


class HnForumExtractor(ForumExtractor):
    tests = []

    @staticmethod
    def detect(session: CachedSession, url: str):
        parsed_url = urlparse(url)
        if parsed_url.netloc.endswith("news.ycombinator.com"):
            return HnForumExtractor(session, urljoin(url, "/"))

    def _fetch_top_boards(self):
        pass

    def _fetch_subboards(self, board: Board):
        pass

    def _get_node_from_url(self, url: str):
        parsed_url = urlparse(url)

        # The whole site.
        if parsed_url.path == "":
            return self.root
        # Thread.
        elif parsed_url.path == "item":
            parsed_query = parse_qs(parsed_url.query)
            id = parsed_query["id"][0]

            # For now, obtain the whole story thread.
            while True:
                json = self._session.get(
                    "https://hacker-news.firebaseio.com/v0/item/{id}.json"
                )

                if json["type"] == "story":
                    break

                id = str(json["parent"])

            return Thread(
                path=[id],
                url="https://news.ycombinator.com/item?id={id}",
                title=json["title"],
            )

        raise ValueError

    def _fetch_lazy_subboard(self, board: Board, id: str):
        pass

    def _fetch_lazy_subboards(self, board: Board):
        pass

    def _get_board_page_items(self, board: Board, page_url: str, id: int = 1):
        if page_url == "https://news.ycombinator.com/":
            page_url = "https://news.ycombinator.com/item?id=1"

        firebase_url = f"https://hacker-news.firebaseio.com/v0/item/{id}.json"
        json = self._session.get(firebase_url).json()

        if json["type"] == "story":
            yield Thread(
                path=[id],
                url=page_url,
                title=json.get("title"),
                content=json.get("text"),
            )

        return (f"https://news.ycombinator.com/item?id={id + 1}", id + 1)

    def _get_thread_page_items(self, thread: Thread, page_url: str):
        parsed_url = urlparse(page_url)
        parsed_query = parse_qs(parsed_url.query)
        post_paths = [[parsed_query["id"][0]]]

        i = 0
        while True:
            post_path = post_paths[i]
            firebase_url = (
                f"https://hacker-news.firebaseio.com/v0/item/{post_path[-1]}.json"
            )
            json = self._session.get(firebase_url).json()

            yield Post(
                path=post_path,
                url=thread.url,
            )

            for kid_id in json.get("kids", []):
                post_paths.append(post_path + [str(kid_id)])

            i += 1

            if i == len(post_paths):
                break
