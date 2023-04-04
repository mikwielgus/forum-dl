# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from . import extractors
from . import writers
from .writers.common import WriteOptions


class ForumDl:
    def download(
        self,
        urls: list[str],
        output_format: str,
        path: str,
        write_options: WriteOptions,
    ):
        for url in urls:
            self.download_url(url, output_format, path, write_options)

    def download_url(
        self, url: str, output_format: str, path: str, write_options: WriteOptions
    ):
        extractor = extractors.find(url)

        if extractor:
            extractor.fetch()
            writer = writers.find(extractor, output_format, path)
            writer.write(url, write_options)

    def list_extractors(self) -> list[str]:
        return extractors.modules

    def list_classes(self) -> Iterable[Any]:
        return extractors.list_classes()
