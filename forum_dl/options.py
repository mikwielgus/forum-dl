# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

import argparse
import logging

from . import version


def build_parser():
    parser = argparse.ArgumentParser(
        add_help=True,
    )

    general = parser.add_argument_group("General Options")
    general.add_argument(
        "--version",
        action="version",
        version=version.__version__,
        help="Print program version and quit",
    )
    general.add_argument(
        "--list-extractors",
        dest="list_extractors",
        action="store_true",
        help="List all supported extractors and exit",
    )

    output = parser.add_argument_group("Output Options")
    output.add_argument(
        "-q",
        "--quiet",
        dest="loglevel",
        default=logging.INFO,
        action="store_const",
        const=logging.ERROR,
        help="Activate quiet mode",
    )
    output.add_argument(
        "-v",
        "--verbose",
        dest="loglevel",
        action="store_const",
        const=logging.DEBUG,
        help="Print various debugging information",
    )
    output.add_argument(
        "-g",
        "--get-urls",
        dest="get_urls",
        action="store_true",
        help="Print URLs instead of downloading",
    )
    output.add_argument(
        "-o",
        "--output",
        dest="output",
        help="Output file",
    )
    output.add_argument(
        "-T",
        "--output-format",
        dest="output_format",
        help="Output format",
        default="json",
    )
    output.add_argument(
        "--textify",
        dest="textify",
        action="store_true",
        help="Lossily convert HTML content to plaintext",
    )
    output.add_argument(
        "--content-as-title",
        dest="content_as_title",
        action="store_true",
        help="Write 98 initial characters of content in title field of each post",
    )

    parser.add_argument(
        "urls",
        metavar="URL",
        nargs="*",
        help=argparse.SUPPRESS,
    )

    return parser
