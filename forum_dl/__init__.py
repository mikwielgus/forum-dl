import logging
import sys

from .forumdl import ForumDl
from . import options
from .writers.common import WriteOptions


def main():
    parser = options.build_parser()
    args = parser.parse_args()

    logging.basicConfig()
    logging.getLogger().setLevel(args.loglevel)

    forumdl = ForumDl()

    if args.list_extractors:
        print("\n".join(forumdl.list_extractors()))
    elif not args.urls:
        parser.error(
            "The following arguments are required: URL\n"
            "Use 'forum-dl --help' to get a list of all options."
        )
    else:
        forumdl.download(
            urls=args.urls,
            output_format=args.output_format,
            path=args.output,
            write_options=WriteOptions(
                content_as_title=args.content_as_title,
                textify=True,
            ),
        )
