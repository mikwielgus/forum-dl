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


class VbulletinForumExtractor(ForumExtractor):
    tests = []

    _forum_id_regex = re.compile(r"^forum(\d+)$")

    @staticmethod
    def detect(session: CachedSession, url: str):
        response = session.get(url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        if not (generator_meta := soup.find("meta", attrs={"name": "generator"})):
            return None

        if not generator_meta.get("content").startswith("vBulletin"):
            return None

        if not (base := soup.find("base")):
            return None

        return VbulletinForumExtractor(session, base.get("href"))

    def _fetch_top_boards(self):
        self.root.are_subboards_fetched = True

        response = self._session.get(self._base_url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        trs = soup.find_all("tr", class_=["category-header", "forum-item"])
        category_id = ""

        for tr in trs:
            if "category-header" in tr.get("class"):
                category_id = self._forum_id_regex.match(tr.get("id")).group(1)

                category_anchor = tr.find("a", class_="category")
                title = category_anchor.string

                self._set_board(
                    path=[category_id],
                    url=category_anchor.get("href"),
                    title=title,
                    are_subboards_fetched=True,
                )
            else:
                board_id = self._forum_id_regex.match(tr.get("id")).group(1)

                board_anchor = tr.find("a", class_="forum-title")
                title = board_anchor.string

                self._set_board(
                    path=[category_id, board_id],
                    url=board_anchor.get("href"),
                    title=title,
                    are_subboards_fetched=True,
                )

    def _fetch_subboards(self, board: Board):
        # Don't fetch top boards.
        if len(board.path) <= 1:
            return

        response = self._session.get(board.url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        trs = soup.find_all("tr", class_="forum-item")
        for tr in trs:
            subboard_id = self._forum_id_regex.match(tr.get("id")).group(1)

            subboard_anchor = tr.find("a", class_="forum-title")
            self._set_board(
                path=board.path + [subboard_id],
                url=subboard_anchor.get("href"),
                title=subboard_anchor.string.strip(),
                are_subboards_fetched=True,
            )

    def _get_node_from_url(self, url: str):
        response = self._session.get(url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        breadcrumb_anchors = soup.find_all("a", class_="crumb-link")

        if len(breadcrumb_anchors) <= 1:
            return self.root

        # Thread.
        if soup.find("h2", class_="b-post__title"):
            board_url = breadcrumb_anchors[-1].get("href")

            for cur_board in self._boards:
                if cur_board.url == board_url:
                    id = soup.find("input", attrs={"name": "nodeid"}).get("value")

                    return Thread(
                        path=cur_board.path + [id], url=urljoin(self._base_url, url)
                    )
        # Board.
        else:
            board_title = breadcrumb_anchors[-1].string

            for cur_board in self._boards:
                if cur_board.title == board_title:
                    return cur_board

    def _fetch_lazy_subboard(self, board: Board, id: str):
        pass

    def _fetch_lazy_subboards(self, board: Board):
        pass

    def _get_board_page_items(self, board: Board, page_url: str, cur_page: int = 1):
        if board == self.root:
            return None

        if not page_url:
            return None

        response = self._session.get(page_url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        thread_trs = soup.find_all("tr", class_="topic-item")
        for thread_tr in thread_trs:
            thread_id = thread_tr.get("data-node-id")
            thread_anchor = thread_tr.find("a", class_="topic-title")

            yield Thread(path=board.path + [thread_id], url=thread_anchor.get("href"))

        next_page_anchor = soup.find("a", class_="right-arrow")

        if next_page_anchor and next_page_anchor.get("href"):
            return (next_page_anchor.get("href"), cur_page + 1)

    def _get_thread_page_items(self, thread: Thread, page_url: str, cur_page: int = 1):
        response = self._session.get(page_url)
        soup = bs4.BeautifulSoup(response.content, "html.parser")

        post_divs = soup.find_all("div", class_="js-post__content-text")
        for post_div in post_divs:
            yield Post(path=thread.path, content=str(post_div.encode_contents()))

        next_page_anchor = soup.find("a", class_="right-arrow")

        if next_page_anchor and next_page_anchor.get("href"):
            return (next_page_anchor.get("href"), cur_page + 1)
