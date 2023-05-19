# forum-dl

Forum-dl is a downloader (scraper) for forums, mailing lists, and news aggregators. It can be used to crawl, extract, and archive individual threads and entire boards into a variety of output formats.

# Installation

## PIP

```
pip install forum-dl
```

## Repository 

Clone the repository:

```
git clone https://github.com/mikwielgus/forum-dl
```

Then, in the same directory, install the repository directly: 

```
pip install -e forum-dl
```

# Quick start

Download a Simple Machines Forum thread in JSONL format:

```
forum-dl "https://www.simplemachines.org/community/index.php?topic=584230.0"
```

Download an entire PhpBB board in JSONL format, write to stdout (`-o -`).

```
forum-dl -o - "https://www.phpbb.com/community/viewforum.php?f=696"
```

<sub>(due to current architecture limitations, `forum-dl` will shallowly scan the entire forum hierarchy before downloading the board. This will be fixed in future releases)</sub>

Download Hacker News top stories and write them to a Maildir directory `hn`:

```
forum-dl --textify --content-as-title -f maildir -o hn "https://news.ycombinator.com/news"
```

- `--textify` converts HTML to plaintext (useful for text-only mail clients),
- `--content-as-title` puts the beginning of each message's content in its title (useful for mail clients that don't display content in index view),
- `-f maildir` changes the output format to `maildir`,
- `-o hn` changes the output directory name to `hn`.

# What is supported

## Forum software

- Discourse
- Hacker News
- Hyperkitty
- Hypermail
- Invision Power Board
- PhpBB
- Pipermail
- Proboards
- Simple Machines Forum
- vBulletin
- Xenforo

## Output formats

- Babyl
- JSONL
- Maildir
- Mbox
- MH
- MMDF

# Usage

```
forum-dl [--help] [--version] [--list-extractors] [--list-output-formats] [--user-agent USER_AGENT] [-q] [-v] [-g] [-o FILE]
         [-f FORMAT] [--no-boards] [--no-threads] [--no-posts] [--textify] [--content-as-title]
```

## General Options:

```
  --help                Show this help message and exit
  --version             Print program version and exit
  --list-extractors     List all supported extractors and exit
  --list-output-formats
                        List all supported output formats and exit
  --user-agent USER_AGENT
                        User-Agent request header
```

## Output Options:

```
  -q, --quiet           Activate quiet mode
  -v, --verbose         Print various debugging information
  -g, --get-urls        Print URLs instead of downloading
  -o FILE, --output FILE
                        Output all results concatenated to FILE, or stdout if FILE is -
  -f FORMAT, --output-format FORMAT
                        Output format
  --no-boards           Do not write board objects
  --no-threads          Do not write thread objects
  --no-posts            Do not write post objects
  --textify             Lossily convert HTML content to plaintext
  --content-as-title    Write 98 initial characters of content in title field of each post
```
