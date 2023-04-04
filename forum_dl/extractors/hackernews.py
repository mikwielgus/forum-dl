# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from urllib.parse import urljoin, urlparse, parse_qs

from .common import Extractor, ExtractorNode, Board, Thread, Post
from ..session import Session
from ..soup import Soup


class HackernewsExtractor(Extractor):
    tests = []

    PAGE_SIZE = 1000

    @staticmethod
    def _detect(session: Session, url: str):
        parsed_url = urlparse(url)
        if parsed_url.netloc == "news.ycombinator.com":
            if parsed_url.path == "/news":
                return HackernewsFrontpageExtractor(session, urljoin(url, "/"))

            return HackernewsExtractor(session, urljoin(url, "/"))

    def _calc_first_item_id(self, page_id: int):
        return 1 + (page_id * self.PAGE_SIZE)

    def _calc_page_id(self, item_id: int):
        return (self.max_item_id - 1) // self.PAGE_SIZE

    def _fetch_top_boards(self):
        firebase_url = f"https://hacker-news.firebaseio.com/v0/maxitem.json"
        self.max_item_id = int(self._session.get(firebase_url).content)
        self.pages: list[list[int]] = [[]] * (1 + self._calc_page_id(self.max_item_id))

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
            id = str(parsed_query["id"][0])

            # For now, obtain the whole story thread.
            while True:
                json = self._session.get(
                    "https://hacker-news.firebaseio.com/v0/item/{id}.json"
                ).json()

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
        yield from ()

    def _get_is_fetchable(self, item_id: int):
        if item_id > self.max_item_id:
            return False

        page_id = self._calc_page_id(item_id)

        if item_id in self.pages[page_id]:
            return False

        return True

    def _register_item(self, item_id: int):
        page_id = self._calc_page_id(item_id)
        self.pages[page_id].append(item_id)

    def _fetch_item_thread(self, item_id: int):
        while True:
            firebase_url = f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
            json = self._session.get(firebase_url).json()

            if "parent" in json:
                item_id = json["parent"]
            else:
                page_id = self._calc_page_id(item_id)
                self.pages[page_id].append(item_id)

                self._register_item(item_id)
                return Thread(
                    path=[str(item_id)],
                    url=f"https://news.ycombinator.com/item?id={item_id}",
                    title=json.get("title"),
                )

    def _get_board_page_threads(self, board: Board, page_url: str, *args: Any):
        # FIXME: This is ineffective, as we connect twice for each non-top item.

        # We make artificial pages of 1000 items.

        page_id = len(self.pages) - 1

        for item_id in reversed(
            range(
                self._calc_first_item_id(page_id), self._calc_first_item_id(page_id + 1)
            )
        ):
            if not self._get_is_fetchable(item_id):
                continue

            yield self._fetch_item_thread(item_id)

        self.pages.pop()

        if page_id > 0:
            return ("https://news.ycombinator.com/item?id={page_url}", (page_id - 1,))

    def _get_thread_page_posts(self, thread: Thread, page_url: str, *args: Any):
        post_paths = [[thread.path[0]]]

        i = 0
        while True:
            post_path = post_paths[i]
            firebase_url = (
                f"https://hacker-news.firebaseio.com/v0/item/{post_path[-1]}.json"
            )
            json = self._session.get(firebase_url).json()

            self._register_item(int(post_path[-1]))
            yield Post(
                path=post_path,
                url=thread.url,
                content=json.get("text"),
                date=json.get("time"),
                username=json.get("by"),
            )

            for kid_id in json.get("kids", []):
                post_paths.append(post_path + [str(kid_id)])

            i += 1
            if i == len(post_paths):
                break


class HackernewsFrontpageExtractor(HackernewsExtractor):
    tests = []

    def _get_node_from_url(self, url: str):
        parsed_url = urlparse(url)

        if parsed_url.path == "/news":
            return self.root

        return HackernewsExtractor._get_node_from_url(self, url)

    def _get_board_page_threads(self, board: Board, page_url: str, *args: Any):
        firebase_url = f"https://hacker-news.firebaseio.com/v0/item/topstories"
        json = self._session.get(firebase_url).json()

        for story_id in json:
            yield Thread(
                path=[story_id],
                url=f"https://news.ycombinator.com/item?id={story_id}",
                # TODO title.
            )
