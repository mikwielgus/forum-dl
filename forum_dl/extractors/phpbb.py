# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse, parse_qs
import re

from .common import get_relative_url, normalize_url, regex_match
from .common import Extractor, ExtractorOptions, Board, Thread, Post, PageState
from ..session import Session
from ..soup import Soup


class PhpbbExtractor(Extractor):
    tests = [
        {
            "url": "https://phpbb.com/community",
            "test_base_url": "https://www.phpbb.com/community/",
            "test_boards": {
                ("47",): {
                    "title": "General",
                },
                ("551",): {
                    "title": "Support Forums",
                },
                ("451",): {
                    "title": "Extensions Forums",
                },
                ("471",): {
                    "title": "Styles Forums",
                },
                ("52",): {
                    "title": "Non-support Specific",
                },
                ("48",): {
                    "title": "phpBB Archives",
                },
            },
        },
        {
            "url": "https://phpbb.com/community/viewforum.php?f=556",
            "item_count": 0,
            "test_base_url": "https://www.phpbb.com/community/",
            "test_boards": {
                ("551", "556", "561"): {
                    "title": "[3.2.x] Convertors",
                },
                ("551", "556", "566"): {
                    "title": "[3.2.x] Translations",
                },
            },
        },
        {
            "url": "https://www.phpbb.com/community/viewtopic.php?t=2377611",
            "test_base_url": "https://www.phpbb.com/community/",
            "test_contents_hash": "d98797411be739205db624165f24fc248c93157b",
            "test_item_count": 7,
        },
        {
            "url": "https://www.phpbb.com/community/viewtopic.php?t=2534156",
            "test_base_url": "https://www.phpbb.com/community/",
            "test_contents_hash": "d88e2da2e01e843f71c70f62a874542a416efc5d",
            "test_item_count": 1,
        },
    ]

    @staticmethod
    def _detect(session: Session, url: str, options: ExtractorOptions):
        # Check for the existence of "viewforum.php".
        response = session.try_get(
            urljoin(
                normalize_url(url, remove_suffixes=["viewforum.php", "viewtopic.php"]),
                "viewforum.php",
            ),
            should_cache=True,
            should_retry=False,
        )

        # A rather crude way to detect: we look for a <html> tag with "dir" attribute.
        soup = Soup(response.text)
        soup.find("html", attrs={"dir": True})

        return PhpbbExtractor(
            session,
            normalize_url(
                response.url, remove_suffixes=["viewforum.php", "viewtopic.php"]
            ),
            options,
        )

    def _is_viewforum_url(self, url: str):
        parsed_url = urlparse(url)
        path = PurePosixPath(str(parsed_url.path))

        if len(path.parts) != 1:
            try:
                get_relative_url(url, self.base_url)
            except ValueError:
                return False

        if path.parts[-1] != "viewforum.php":
            return False

        parsed_query = parse_qs(parsed_url.query)

        if "f" not in parsed_query:
            return False

        return True

    def _is_viewforum_pagination_url(self, url: str):
        if not self._is_viewforum_url(url):
            return False

        parsed_url = urlparse(url)
        parsed_query = parse_qs(parsed_url.query)

        if not {"f", "start"} <= parsed_query.keys():
            return False

        return True

    def _is_viewtopic_url(self, url: str, thread_id: int | None = None):
        parsed_url = urlparse(url)
        path = PurePosixPath(str(parsed_url.path))

        if len(path.parts) != 1:
            try:
                get_relative_url(url, self.base_url)
            except ValueError:
                return False

        if path.parts[-1] != "viewtopic.php":
            return False

        parsed_query = parse_qs(parsed_url.query)

        if "t" not in parsed_query:
            return False

        return True

    def _is_viewtopic_pagination_url(self, url: str, thread_id: int | None = None):
        if not self._is_viewtopic_url(url, thread_id):
            return False

        parsed_url = urlparse(url)
        parsed_query = parse_qs(parsed_url.query)

        if not {"t", "start"} <= parsed_query.keys():
            return False

        return True

    def _fetch_top_boards(self):
        self._are_subboards_fetched[self.root.path] = True

        response = self._session.get(self.base_url, should_cache=True)
        soup = Soup(response.content)

        board_lis = soup.find_all("div", class_="forabg")

        for board_li in board_lis:
            header_li = board_li.find("li", class_="header")
            board_anchor = header_li.find("a")

            parsed_href = urlparse(board_anchor.get("href"))
            parsed_query = parse_qs(parsed_href.query)

            try:
                board_id = parsed_query["f"][0]
            except KeyError:
                continue

            board_title = board_anchor.string
            board_url = urljoin(self.base_url, f"viewforum.php?f={board_id}")

            self._set_board(
                path=(board_id,),
                url=board_url,
                origin=response.url,
                data={},
                title=board_title,
                are_subboards_fetched=True,
            )

            subboard_anchors = board_li.find_all("a", class_="forumtitle")

            for subboard_anchor in subboard_anchors:
                parsed_href = urlparse(subboard_anchor.get("href"))
                parsed_query = parse_qs(parsed_href.query)
                subboard_id = parsed_query["f"][0]
                subboard_title = subboard_anchor.string
                subboard_url = urljoin(self.base_url, f"viewforum.php?f={subboard_id}")

                self._set_board(
                    path=(
                        board_id,
                        subboard_id,
                    ),
                    url=subboard_url,
                    origin=response.url,
                    data={},
                    title=subboard_title,
                )

    def _do_fetch_subboards(self, board: Board):
        if board is self.root:
            return

        response = self._session.get(board.url, should_cache=True)

        try:
            get_relative_url(response.url, self.base_url)
        except ValueError:
            return

        soup = Soup(response.content)

        subboard_anchors = soup.find_all("a", class_="forumtitle")

        for subboard_anchor in subboard_anchors:
            parsed_href = urlparse(subboard_anchor.get("href"))
            parsed_query = parse_qs(parsed_href.query)

            try:
                subboard_id = parsed_query["f"][0]
            except KeyError:
                continue

            subboard_title = subboard_anchor.string
            subboard_url = urljoin(self.base_url, f"viewforum.php?f={subboard_id}")

            self._set_board(
                path=board.path + (subboard_id,),
                url=subboard_url,
                origin=response.url,
                data={},
                title=subboard_title,
                are_subboards_fetched=True,
            )

    def _resolve_url(self, url: str):
        return normalize_url(
            self._session.get(url, should_cache=True).url, keep_queries=["f", "t"]
        )

    def _get_node_from_url(self, url: str):
        response = self._session.get(url, should_cache=True)
        resolved_url = normalize_url(response.url, keep_queries=["f", "t"])

        parsed_url = urlparse(resolved_url)
        parts = PurePosixPath(parsed_url.path).parts

        if parts[-1] == "viewforum.php":
            self._fetch_lower_boards(self.root)

            parsed_query = parse_qs(parsed_url.query)

            if "f" not in parsed_query:
                return self.root

            board_id = parsed_query["f"][0]

            for board in self._boards:
                if board is not self.root and board.path[-1] == board_id:
                    return board

            raise ValueError
        elif parts[-1] == "viewtopic.php":
            topic_id = parse_qs(parsed_url.query)["t"][0]
            soup = Soup(response.content)
            breadcrumbs = soup.find(class_="breadcrumbs")

            breadcrumb_anchors = breadcrumbs.find_all("a", attrs={"itemprop": "item"})

            breadcrumb_urls = [
                self._resolve_url(urljoin(url, anchor.get("href")))
                for anchor in breadcrumb_anchors
            ]
            board = self.find_board_from_urls(tuple(breadcrumb_urls[1:]))

            title_h2 = soup.find("h2", class_="topic-title")
            title = title_h2.find("a").string

            return Thread(
                path=board.path + (topic_id,),
                url=resolved_url,
                origin=resolved_url,
                data={},
                title=title,
            )
        elif normalize_url(resolved_url) == self.base_url:
            return self.root

        raise ValueError

    def _fetch_lazy_subboard(self, board: Board, subboard_id: str):
        pass

    def _fetch_lazy_subboards(self, board: Board):
        yield from ()

    def _fetch_board_page_threads(self, board: Board, state: PageState):
        if board == self.root:
            return None

        parsed_url = urlparse(state.url)
        board_id = parse_qs(parsed_url.query)["f"][0]

        parsed_query = parse_qs(parsed_url.query)
        if "start" in parsed_query:
            cur_start = int(parsed_query["start"][0])
        else:
            cur_start = 0

        response = self._session.get(state.url)
        soup = Soup(response.content)
        topic_anchors = soup.find_all(
            "a", class_="topictitle", attrs={"href": self._is_viewtopic_url}
        )

        if not topic_anchors:
            topic_anchors = soup.find_all("a", attrs={"href": self._is_viewtopic_url})

        for topic_anchor in topic_anchors:
            href = urljoin(self.base_url, topic_anchor.get("href"))
            parsed_href = urlparse(href)
            parsed_query = parse_qs(parsed_href.query)
            thread_id = parsed_query["t"][0]

            yield Thread(
                path=board.path + (thread_id,),
                url=href,
                origin=response.url,
                data={},
                title=topic_anchor.string,
            )

        pagination_anchors = soup.find_all(
            "a", attrs={"href": self._is_viewforum_pagination_url}
        )

        # Look for pagination links. Always choose the one with the smallest increment.
        min_start = None

        for pagination_anchor in pagination_anchors:
            parsed_href = urlparse(pagination_anchor.get("href"))
            parsed_query = parse_qs(parsed_href.query)
            start = int(parsed_query["start"][0])

            if start > cur_start and (not min_start or start < min_start):
                min_start = start

        if min_start:
            return PageState(
                url=urljoin(
                    self.base_url, f"viewforum.php?f={board_id}&start={min_start}"
                )
            )

    def _fetch_thread_page_posts(self, thread: Thread, state: PageState):
        parsed_url = urlparse(state.url)
        thread_id = parse_qs(parsed_url.query)["t"][0]

        parsed_query = parse_qs(parsed_url.query)
        if "start" in parsed_query:
            cur_start = int(parsed_query["start"][0])
        else:
            cur_start = 0

        response = self._session.get(state.url)
        soup = Soup(response.content)
        post_divs = soup.find_all("div", class_="post")

        for post_div in post_divs:
            id_div_regex = re.compile(r"^post_content(\d+)$")
            id_div = post_div.find("div", id=id_div_regex)
            content_div = post_div.find("div", class_="content")

            author_p = post_div.find("p", class_="author")

            username_tag = author_p.find(
                {"a", "span"}, class_={"username", "username-coloured"}
            )
            time_tag = author_p.find("time")

            url_h3 = post_div.find("h3")
            url_anchor = url_h3.find("a")

            yield Post(
                path=thread.path,
                subpath=(regex_match(id_div_regex, id_div.get("id")).group(1),),
                url=urljoin(response.url, url_anchor.get("href")),
                origin=response.url,
                data={},
                author=username_tag.string,
                creation_time=time_tag.get("datetime"),
                content=str("".join(str(v) for v in content_div.contents)),
            )

        pagination_anchors = soup.find_all(
            "a",
            attrs={"href": self._is_viewtopic_pagination_url},
        )

        # Look for pagination links. Always choose the one with the smallest increment.
        min_start = None

        for pagination_anchor in pagination_anchors:
            parsed_href = urlparse(pagination_anchor.get("href"))
            parsed_query = parse_qs(parsed_href.query)
            start = int(parsed_query["start"][0])

            if start > cur_start and (not min_start or start < min_start):
                min_start = start

        if min_start:
            return PageState(
                url=urljoin(
                    self.base_url, f"viewtopic.php?t={thread_id}&start={min_start}"
                )
            )
