# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from urllib.parse import urljoin, urlparse, parse_qs
from dataclasses import dataclass

from .common import Extractor, Board, Thread, Post
from ..session import Session
from ..soup import Soup


@dataclass
class HackernewsThread(Thread):
    content: str = ""


class HackernewsExtractor(Extractor):
    tests = [
        {
            "url": "https://news.ycombinator.com",
            "test_base_url": "https://news.ycombinator.com/",
            "test_min_item_count": 1000,
        },
    ]

    @staticmethod
    def _detect(session: Session, url: str):
        parsed_url = urlparse(url)
        if parsed_url.netloc == "news.ycombinator.com":
            if parsed_url.path == "/news":
                return HackernewsFrontpageExtractor(session, urljoin(url, "/"))

            return HackernewsExtractor(session, urljoin(url, "/"))

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
            id = str(parsed_query["id"][0])

            # For now, obtain the whole story thread.
            while True:
                json = self._session.get(
                    "https://hacker-news.firebaseio.com/v0/item/{id}.json"
                ).json()

                if json["type"] == "story":
                    break

                id = str(json["parent"])

            return HackernewsThread(
                path=[id],
                url="https://news.ycombinator.com/item?id={id}",
                title=json["title"],
            )

        raise ValueError

    def _fetch_lazy_subboard(self, board: Board, id: str):
        pass

    def _fetch_lazy_subboards(self, board: Board):
        yield from ()

    def _get_board_page_threads(self, board: Board, page_url: str, *args: Any):
        if board.url == page_url:
            page_url = "https://news.ycombinator.com/newest"

        response = self._session.get(page_url)
        soup = Soup(response.content)

        for thread_tr in soup.find_all("tr", class_="athing"):
            titleline_span = thread_tr.find("span", class_="titleline")

            yield HackernewsThread(
                path=[thread_tr.get("id")],
                url=f"https://news.ycombinator.com/item?id={thread_tr.get('id')}",
                title=titleline_span.find("a").string,
                content=titleline_span.find("a").get("href"),
            )

        next_page_anchor = soup.try_find("a", class_="morelink")
        if next_page_anchor:
            return urljoin(self.base_url, next_page_anchor.get("href"))

    def _get_thread_page_posts(self, thread: Thread, page_url: str, *args: Any):
        post_paths = [[thread.path[0]]]

        i = 0
        while True:
            post_path = post_paths[i]
            firebase_url = (
                f"https://hacker-news.firebaseio.com/v0/item/{post_path[-1]}.json"
            )
            json = self._session.get(firebase_url).json()
            hn_thread = cast(HackernewsThread, thread)

            yield Post(
                path=post_path,
                url=thread.url,
                content=hn_thread.content if i == 0 else json.get("text"),
                date=json.get("time"),
                username=json.get("by"),
            )

            for kid_id in json.get("kids", []):
                post_paths.append(post_path + [str(kid_id)])

            i += 1
            if i == len(post_paths):
                break


class HackernewsFrontpageExtractor(HackernewsExtractor):
    def _get_node_from_url(self, url: str):
        parsed_url = urlparse(url)

        if parsed_url.path == "/news":
            return self.root

        return HackernewsExtractor._get_node_from_url(self, url)

    def _get_board_page_threads(self, board: Board, page_url: str, *args: Any):
        if board.url == page_url:
            page_url = "https://news.ycombinator.com/news"

        return HackernewsExtractor._get_board_page_threads(self, board, page_url)
