import sys

from .forumdl import ForumDL


def main():
    urls = sys.argv[1:]

    # with ForumDL() as forumdl:
    forumdl = ForumDL()
    # for cls in forumdl.list_classes():
    # print(cls)
    forumdl.download(urls)
