# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

import bs4

from .common import Extractor, Board, Thread, Post
from ..cached_session import CachedSession
from ..soup import Soup


class InvisionExtractor(Extractor):
    tests = [
        {
            "url": "https://invisioncommunity.com/forums",
            "test_base_url": "https://invisioncommunity.com/forums/",
            "test_boards": {
                ("180", "528"): {
                    "title": "Invision Community Insider",
                },
                ("180", "528", "529"): {
                    "title": "Cloud Discussion",
                },
                ("180", "499"): {
                    "title": "Feedback",
                },
                ("180", "320"): {
                    "title": "Community Manager Chat",
                },
                ("492", "505"): {
                    "title": "General Questions",
                },
                ("492", "497"): {
                    "title": "Technical Problems",
                },
                ("492", "497", "524"): {
                    "title": "Classic self-hosted technical help",
                },
                ("492", "500"): {
                    "title": "Design and Customization",
                },
                ("492", "477"): {
                    "title": "Community Manager Idea Sharing",
                },
                ("307", "504"): {
                    "title": "Developer Connection",
                },
                ("307", "521"): {
                    "title": "Marketplace",
                },
            },
        },
        {
            "url": "https://invisioncommunity.com/forums/topic/367687-important-seo-step-that-is-often-overlooked/",
            "test_base_url": "https://invisioncommunity.com/forums/",
            "test_contents_hash": "13e6adfdafad99791253e61a1bccf3e63d55fe9b",
            "test_item_count": 65,
        },
        {
            "url": "https://invisioncommunity.com/forums/topic/447328-guide-joels-guide-to-subscriptions/",
            "test_base_url": "https://invisioncommunity.com/forums/",
            "test_contents_hash": "4c3866dcab326ed8c9c1d62d66b3f9cf788fd785",
            "test_item_count": 52,
        },
    ]

    @staticmethod
    def _detect(session: CachedSession, url: str):
        response = session.get(url)
        soup = Soup(response.content)

        breadcrumbs_ul = soup.find("ul", attrs={"data-role": "breadcrumbList"})
        breadcrumb_lis = breadcrumbs_ul.find_all("li")
        base_url = url

        if len(breadcrumb_lis) >= 2:
            base_url = breadcrumb_lis[1].find("a").get("href")

        if soup.find("a", attrs={"title": "Invision Community"}):
            return InvisionExtractor(session, base_url)

    def _fetch_top_boards(self):
        self.root.are_subboards_fetched = True

        response = self._session.get(self._base_url)
        soup = Soup(response.content)

        category_lis = soup.find_all("li", class_="cForumRow")
        for category_li in category_lis:
            category_id = category_li.get("data-categoryid")
            category_anchor = category_li.find("h2").find_all("a")[1]

            self._set_board(
                path=[category_id],
                url=category_anchor.get("href"),
                title=category_anchor.string,
                are_subboards_fetched=True,
            )

            board_divs = category_li.find_all("div", class_="cForumGrid")
            for board_div in board_divs:
                board_id = board_div.get("data-forumid")
                board_h3 = board_div.find("h3", class_="cForumGrid__title")
                board_anchor = board_h3.find("a")

                self._set_board(
                    path=[category_id, board_id],
                    url=board_anchor.get("href"),
                    title=board_anchor.string,
                    are_subboards_fetched=True,
                )

    def _fetch_subboards(self, board: Board):
        if board is self.root:
            return

        response = self._session.get(board.url)
        soup = Soup(response.content)

        subboard_divs = soup.find_all("div", class_="cForumGrid")
        for subboard_div in subboard_divs:
            subboard_id = subboard_div.get("data-forumid")
            subboard_h3 = subboard_div.find("h3")
            subboard_anchor = subboard_h3.find("a")

            self._set_board(
                path=board.path + [subboard_id],
                url=subboard_anchor.get("href"),
                title=subboard_anchor.string,
                are_subboards_fetched=True,
            )

    def _get_node_from_url(self, url: str):
        response = self._session.get(url)
        soup = Soup(response.content)

        breadcrumbs_ul = soup.find("ul", attrs={"data-role": "breadcrumbList"})
        breadcrumb_lis = breadcrumbs_ul.find_all("li")

        if len(breadcrumb_lis) <= 2:
            return self.root

        # Thread.
        if soup.try_find("article"):
            board_href = breadcrumb_lis[-2].find("a").get("href")
            thread_id = soup.find("body").get("data-pageid")

            for cur_board in self._boards:
                if cur_board.url == board_href:
                    return Thread(path=cur_board.path + [thread_id], url=url)
        # Board.
        else:
            for cur_board in self._boards:
                if cur_board.url == url:
                    return cur_board

        raise ValueError

    def _fetch_lazy_subboard(self, board: Board, id: str):
        pass

    def _fetch_lazy_subboards(self, board: Board):
        yield from ()

    def _get_board_page_threads(self, board: Board, page_url: str, *args: Any):
        cur_page = args[0] if len(args) >= 1 else 1

        if board is self.root:
            return None

        response = self._session.get(page_url)
        soup = Soup(response.content)

        thread_lis = soup.find_all(
            "li", attrs={"data-controller": "forums.front.forum.topicRow"}
        )
        for thread_li in thread_lis:
            thread_id = thread_li.get("data-rowid")
            thread_span = thread_li.find("span", class_="cTopicTitle")
            thread_anchor = thread_span.find("a")

            yield Thread(path=board.path + [thread_id], url=thread_anchor.get("href"))

        next_page_link = soup.try_find("link", attrs={"rel": "next"})
        if next_page_link:
            return (next_page_link.get("href"), (cur_page + 1,))

    def _get_thread_page_posts(self, thread: Thread, page_url: str, *args: Any):
        cur_page = args[0] if len(args) >= 1 else 1

        response = self._session.get(page_url)
        soup = Soup(response.content)

        content_divs = soup.find_all("div", attrs={"data-role": "commentContent"})
        for content_div in content_divs:
            yield Post(path=thread.path, content=str(content_div.encode_contents()))

        next_page_link = soup.try_find("link", attrs={"rel": "next"})
        if next_page_link:
            return (next_page_link.get("href"), (cur_page + 1,))
