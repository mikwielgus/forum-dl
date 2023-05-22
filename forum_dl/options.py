# pyright: strict
from __future__ import annotations
from typing import *  # type: ignore

import argparse
import logging

from .version import __version__


def build_parser():
    parser = argparse.ArgumentParser(
        add_help=False,
    )

    general = parser.add_argument_group("General Options")
    general.add_argument(
        "--help",
        action="help",
        help="Show this help message and exit",
    )
    general.add_argument(
        "--version",
        action="version",
        version=__version__,
        help="Print program version and exit",
    )
    general.add_argument(
        "--list-extractors",
        dest="list_extractors",
        action="store_true",
        help="List all supported extractors and exit",
    )
    general.add_argument(
        "--list-output-formats",
        dest="list_output_formats",
        action="store_true",
        help="List all supported output formats and exit",
    )

    general.add_argument(
        "--user-agent",
        dest="user_agent",
        default=f"Forum-dl {__version__}",
        help="User-Agent request header",
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
        metavar="FILE",
        dest="output",
        help="Output all results concatenated to FILE, or stdout if FILE is -",
    )
    output.add_argument(
        "-f",
        "--output-format",
        metavar="FORMAT",
        dest="output_format",
        default="jsonl",
        help="Output format. Use --list-output-formats for a list of possible arguments",
    )
    output.add_argument(
        "--warc-output",
        metavar="FILE",
        dest="warc_output",
        default="",
        help="Record HTTP requests, store them in FILE in WARC format",
    )
    output.add_argument(
        "--no-boards",
        dest="boards",
        action="store_false",
        help="Do not write board objects",
    )
    output.add_argument(
        "--no-threads",
        dest="threads",
        action="store_false",
        help="Do not write thread objects",
    )
    output.add_argument(
        "--no-posts",
        dest="posts",
        action="store_false",
        help="Do not write post objects",
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
    output.add_argument(
        "--author-as-addr-spec",
        dest="author_as_addr_spec",
        action="store_true",
        help="Append author and domain as an addr-spec in the From header",
    )

    parser.add_argument(
        "urls",
        metavar="URL",
        nargs="*",
        help=argparse.SUPPRESS,
    )

    return parser
