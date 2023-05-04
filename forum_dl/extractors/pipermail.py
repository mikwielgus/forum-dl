# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse, urlunparse
from dataclasses import dataclass
import bs4
import re

from .common import normalize_url, regex_match
from .common import Extractor, ExtractorOptions, Board, Thread, Post, PageState
from ..exceptions import TagSearchError
from ..session import Session
from ..soup import Soup


@dataclass
class PipermailThread(Thread):
    page_url: str = ""

    def to_dict(self):
        return {k: v for k, v in super().to_dict().items() if k != "page_url"}


@dataclass(kw_only=True)
class PipermailPageState(PageState):
    relative_urls: list[str]


class PipermailExtractor(Extractor):
    tests = [
        {
            "url": "http://lists.opensource.org/mailman/listinfo",
            "test_base_url": "https://lists.opensource.org/",
            "test_boards": {
                ("license-discuss@lists.opensource.org",): {
                    "title": "License-discuss",
                },
                ("license-review@lists.opensource.org",): {
                    "title": "License-review",
                },
                ("publicpolicy@lists.opensource.org",): {
                    "title": "Publicpolicy",
                },
            },
        },
        {
            "url": "http://lists.opensource.org/pipermail/osideas_lists.opensource.org/2020-May/thread.html",
            "test_base_url": "http://lists.opensource.org/",
            # "test_contents_hash": "1489f923c4dca729178b3e3233458550d8dddf29",
            "test_item_count": 3,
        },
        {
            "url": "http://lists.opensource.org/pipermail/license-review_lists.opensource.org/2008-January/000031.html",
            "test_base_url": "http://lists.opensource.org/",
            "test_item_count": 22,
        },
    ]

    _listinfo_href_regex = re.compile(r"^listinfo/(.+)$")
    _listinfo_title_regex = re.compile(r"^(.+) Info Page$")
    _pipermail_page_href_regex = re.compile(
        r"^\d\d\d\d-(January|February|March|April|May|June|July|August|September|October|November|December)/thread.html$"
    )
    _post_href_regex = re.compile(r"^(\d+).html$")
    _root_post_comment_regex = re.compile(r"^0 ([^-]+)- $")
    _child_post_comment_regex = re.compile(r"^(1|2|3) ([^-]+)-.* $")

    @staticmethod
    def _detect(session: Session, url: str, options: ExtractorOptions):
        response = session.get(url)
        resolved_url = normalize_url(response.url)

        parsed_url = urlparse(resolved_url)
        path = PurePosixPath(parsed_url.path)

        if len(path.parts) >= 4 and path.parts[-4] == "pipermail":
            return PipermailExtractor(
                session,
                str(
                    urlunparse(
                        parsed_url._replace(path=str(PurePosixPath(*path.parts[:-4])))
                    )
                ),
                options,
            )
        elif len(path.parts) >= 3 and path.parts[-3] == "pipermail":
            return PipermailExtractor(
                session,
                str(
                    urlunparse(
                        parsed_url._replace(path=str(PurePosixPath(*path.parts[:-3])))
                    )
                ),
                options,
            )
        elif len(path.parts) >= 2 and (
            path.parts[-2] == "pipermail" or path.parts[-2] == "mailman"
        ):
            return PipermailExtractor(
                session,
                str(
                    urlunparse(
                        parsed_url._replace(path=str(PurePosixPath(*path.parts[:-2])))
                    )
                ),
                options,
            )
        elif len(path.parts) >= 1 and (
            path.parts[-1] == "pipermail" or path.parts[-1] == "mailman"
        ):
            return PipermailExtractor(
                session,
                str(
                    urlunparse(
                        parsed_url._replace(path=str(PurePosixPath(*path.parts[:-1])))
                    )
                ),
                options,
            )

    def _fetch_top_boards(self):
        pass

    def _fetch_subboards(self, board: Board):
        pass

    def _get_node_from_url(self, url: str):
        response = self._session.get(url)
        resolved_url = normalize_url(response.url)

        if resolved_url == self.base_url:
            return self.root

        parsed_url = urlparse(resolved_url)
        path = PurePosixPath(parsed_url.path)

        if len(path.parts) >= 4 and path.parts[-4] == "pipermail":
            if path.parts[-1] == "thread.html":
                return self.find_board([path.parts[-3]])

            id = path.parts[-1].removesuffix(".html")
            board_id = path.parts[-3]

            # TODO: Properly read board name instead.
            board_id.replace("_", "@")

            soup = Soup(response.content)
            title = soup.find("title").string

            return PipermailThread(
                path=[board_id] + [id],
                url=url,
                origin=resolved_url,
                data={},
                title=title,
                page_url=urljoin(url, "thread.html"),
            )
        elif len(path.parts) >= 3 and path.parts[-3] == "pipermail":
            return self.find_board([path.parts[-2]])
        elif (
            len(path.parts) >= 3
            and path.parts[-3] == "mailman"
            and path.parts[-2] == "listinfo"
        ):
            return self.find_board([path.parts[-1]])
        elif len(path.parts) >= 2:
            if path.parts[-2] == "pipermail":
                return self.find_board([path.parts[-1]])

            return self.root

        raise ValueError

    def _fetch_lazy_subboard(self, board: Board, id: str):
        nice_id = id.replace("@", "_")

        url = normalize_url(urljoin(self.base_url, f"mailman/listinfo/{nice_id}"))
        response = self._session.get(url)
        soup = Soup(response.content)

        title_title = soup.find("title")
        title = regex_match(self._listinfo_title_regex, title_title.string).group(1)

        body = str(soup.find_all("p")[2].contents[1])
        return self._set_board(
            path=[id],
            url=url,
            origin=response.url,
            data={"body": body},
            title=title,
        )

    def _fetch_lazy_subboards(self, board: Board):
        # TODO use a for loop over _fetch_lazy_subboard() instead
        url = normalize_url(urljoin(self.base_url, f"mailman/listinfo"))
        response = self._session.get(url)
        soup = Soup(response.content)

        listinfo_anchors = soup.find_all("a", attrs={"href": self._listinfo_href_regex})

        for listinfo_anchor in listinfo_anchors:
            href = listinfo_anchor.get("href")
            id = regex_match(self._listinfo_href_regex, href).group(1)
            yield self._fetch_lazy_subboard(board, id)

    def _fetch_board_page_threads(self, board: Board, state: PageState):
        if board == self.root:
            return None

        if state.url == board.url:
            id = board.path[0]
            pipermail_url = urljoin(self.base_url, f"pipermail/{id}")

            response = self._session.get(pipermail_url)
            soup = Soup(response.content)

            page_anchors = soup.find_all(
                "a", attrs={"href": self._pipermail_page_href_regex}
            )

            relative_urls = list(
                reversed([page_anchor.get("href") for page_anchor in page_anchors])
            )

            relative_url = relative_urls.pop()
            return PipermailPageState(
                url=urljoin(urljoin(self.base_url, f"pipermail/{id}/"), relative_url),
                relative_urls=relative_urls,
            )

        state = cast(PipermailPageState, state)

        response = self._session.get(state.url)
        soup = Soup(response.content)

        root_comments = soup.soup.find_all(
            string=lambda text: isinstance(text, bs4.element.Comment)
            and bool(self._root_post_comment_regex.match(text))
        )

        for root_comment in root_comments:
            thread_anchor = root_comment.find_next(
                "a", attrs={"href": self._post_href_regex}
            )
            href = thread_anchor.get("href")
            id = regex_match(self._post_href_regex, href).group(1)

            yield PipermailThread(
                path=board.path + [id],
                url=urljoin(state.url, href),
                origin=response.url,
                data={},
                title=thread_anchor.string,
                page_url=state.url,
            )

        if state.relative_urls:
            relative_url = state.relative_urls.pop()
            board_id = board.path[0]
            return PipermailPageState(
                url=urljoin(
                    urljoin(self.base_url, f"pipermail/{board_id}/"), relative_url
                ),
                relative_urls=state.relative_urls,
            )

    def _fetch_thread_page_posts(self, thread: Thread, state: PageState):
        if state.url == thread.url:
            state.url = cast(PipermailThread, thread).page_url

        response = self._session.get(state.url)
        soup = Soup(response.content)

        root_anchor = soup.find("a", attrs={"href": f"{thread.path[-1]}.html"})
        root_comment = root_anchor.tag.find_previous(
            string=lambda text: isinstance(text, bs4.element.Comment)
        )
        if not isinstance(root_comment, bs4.element.Comment):
            raise TagSearchError

        yield self._fetch_post(state, thread.path + [thread.path[-1]], thread.url)

        thread_long_id = regex_match(
            self._root_post_comment_regex, str(root_comment)
        ).group(1)

        child_comments = soup.soup.find_all(
            string=lambda text: isinstance(text, bs4.element.Comment)
            and bool(self._child_post_comment_regex.match(text))
            and (
                text.startswith(f"1 {thread_long_id}-")
                or text.startswith(f"2 {thread_long_id}-")
                or text.startswith(f"3 {thread_long_id}-")
            )
        )

        for child_comment in child_comments:
            child_anchor = child_comment.find_next(
                "a", attrs={"href": self._post_href_regex}
            )
            href = child_anchor.get("href")
            id = regex_match(self._post_href_regex, href).group(1)

            yield self._fetch_post(state, thread.path + [id], urljoin(state.url, href))

    def _fetch_post(self, state: PageState, path: list[str], url: str):
        response = self._session.get(url)
        soup = Soup(response.content)

        content_pre = soup.find("pre")
        username_b = soup.find("b")

        return Post(
            path=path,
            url=url,
            origin=response.url,
            data={},
            author=username_b.string,
            body=str(content_pre.tag),
        )
