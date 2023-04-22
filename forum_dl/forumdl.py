# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from urllib.parse import quote_plus

from . import extractors
from . import writers
from .session import SessionOptions
from .writers.common import WriterOptions


class ForumDl:
    def download(
        self,
        urls: list[str],
        output_format: str,
        path: str | None,
        session_options: SessionOptions,
        writer_options: WriterOptions,
    ):
        for url in urls:
            self.download_url(url, output_format, path, session_options, writer_options)

    def download_url(
        self,
        url: str,
        output_format: str,
        path: str | None,
        session_options: SessionOptions,
        writer_options: WriterOptions,
    ):
        extractor = extractors.find(url, session_options)

        if extractor:
            extractor.fetch()
            path = path or quote_plus(extractor.base_url)
            writer = writers.find(
                extractor, output_format, path, session_options, writer_options
            )
            writer.write(url)

    def list_extractors(self) -> list[str]:
        return extractors.modules

    def list_classes(self) -> Iterable[Any]:
        return extractors.list_classes()
