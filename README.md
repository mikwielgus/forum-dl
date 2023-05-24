# forum-dl

Forum-dl is a scraper and archiver for forums, mailing lists, and news aggregators ([list](#forum-software)). It can be used to extract and archive all posts in individual threads and entire boards into a variety of [formats](#output-formats).

# Installation

You can install Forum-dl from [PIP](#pip) or directly from the [repository](#repository).

## PIP

Install the latest stable version of Forum-dl from PIP:

```
pip install forum-dl
```

## Repository 

Clone the repository and install it in editable mode:

```
git clone https://github.com/mikwielgus/forum-dl && pip install -e forum-dl
```

# Quick start

Download a Simple Machines Forum thread in JSONL format:

```
forum-dl "https://www.simplemachines.org/community/index.php?topic=584230.0"
```

Download an entire PhpBB board in JSONL format, write to stdout (`-o -`):

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
- WARC

# Usage

```
forum-dl [--help] [--version] [--list-extractors] [--list-output-formats] [-R RETRIES] [--retry-sleep RETRY_SLEEP]
         [--retry-sleep-multiplier RETRY_SLEEP_MULTIPLIER] [--user-agent USER_AGENT] [-q] [-v] [-g] [-o FILE] [-f FORMAT]
         [--warc-output FILE] [--no-boards] [--no-threads] [--no-posts] [--textify] [--content-as-title]
         [--author-as-addr-spec]
```

## General Options:

```
  --help                Show this help message and exit
  --version             Print program version and exit
  --list-extractors     List all supported extractors and exit
  --list-output-formats
                        List all supported output formats and exit
```

## Session Options:

```
  -R RETRIES, --retries RETRIES
                        Maximum number of retries for failed HTTP requests or -1 to retry infinitely (default: 4)
  --retry-sleep RETRY_SLEEP
                        Time to sleep between retries, in seconds (default: 1)
  --retry-sleep-multiplier RETRY_SLEEP_MULTIPLIER
                        A constant by which sleep time is multiplied on each retry (default: 2)
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
                        Output format. Use --list-output-formats for a list of possible arguments
  --warc-output FILE    Record HTTP requests, store them in FILE in WARC format
  --no-boards           Do not write board objects
  --no-threads          Do not write thread objects
  --no-posts            Do not write post objects
  --textify             Lossily convert HTML content to plaintext
  --content-as-title    Write 98 initial characters of content in title field of each post
  --author-as-addr-spec
                        Append author and domain as an addr-spec in the From header
```
