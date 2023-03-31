# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

from . import extractors
from . import writers
import os.path
import os


class ForumDL:
    def download(self, urls: list[str], path: str, output_format: str):
        for url in urls:
            self.download_url(url, path, output_format)

    def download_url(self, url: str, path: str, output_format: str):
        extractor = extractors.find(url)

        if extractor:
            extractor.fetch()
            writer = writers.find(extractor, path, output_format)
            writer.write(url)

    def list_extractors(self) -> list[str]:
        return extractors.modules

    def list_classes(self) -> Iterable[Any]:
        return extractors.list_classes()
