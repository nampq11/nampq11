import feedparser
import pathlib
import re

root = pathlib.Path(__file__).parent.resolve()
FEED_URL = 'https://nampq11.github.io/rss.xml'


def marker_pattern(marker):
    escaped_marker = re.escape(marker)
    return re.compile(
        rf'<!\-\- {escaped_marker} starts \-\->.*?<!\-\- {escaped_marker} ends \-\->',
        re.DOTALL,
    )


def replace_writing(content, marker, chunk, inline=False):
    r = marker_pattern(marker)
    matches = r.findall(content)
    if len(matches) != 1:
        raise ValueError(
            f'Expected exactly one README marker block for {marker!r}, found {len(matches)}. '
            f'Add <!-- {marker} starts --> and <!-- {marker} ends --> markers.'
        )

    if not inline:
        chunk = '\n{}\n'.format(chunk)
    chunk = '<!-- {} starts -->{}<!-- {} ends -->'.format(marker, chunk, marker)
    return r.sub(chunk, content)


def validate_feed(parsed_feed):
    status = parsed_feed.get('status')
    if status is not None and not (200 <= status < 300):
        raise RuntimeError(f'Failed to fetch RSS feed {FEED_URL}: HTTP {status}')

    if parsed_feed.get('bozo'):
        raise RuntimeError(
            f'Failed to parse RSS feed {FEED_URL}: {parsed_feed.get("bozo_exception")}'
        )

    entries = parsed_feed.get('entries')
    if not entries:
        raise RuntimeError(f'RSS feed {FEED_URL} returned no entries')

    return entries


def format_published_date(published):
    match = re.findall(r'(.*?)\s00:00', published)
    if not match:
        raise ValueError(f'Could not parse published date from RSS entry: {published!r}')
    return match[0]


def fetch_writing():
    parsed_feed = feedparser.parse(FEED_URL)
    entries = validate_feed(parsed_feed)
    top5_entries = entries[:5]
    entry_count = len(entries)
    formatted_entries = []

    for entry in top5_entries:
        missing_fields = [
            field for field in ('title', 'link', 'published') if field not in entry
        ]
        if missing_fields:
            raise ValueError(
                f'RSS entry is missing required field(s): {", ".join(missing_fields)}'
            )

        formatted_entries.append(
            {
                'title': entry['title'],
                'url': entry['link'].split('#')[0],
                'published': format_published_date(entry['published']),
            }
        )

    return formatted_entries, entry_count


if __name__ == '__main__':
    readme_path = root / 'README.md'
    readme = readme_path.read_text(encoding='utf-8')
    entries, entry_count = fetch_writing()
    print(f'Recent 5: {entries}, total: {entry_count}')
    entries_md = '\n'.join(
        ['* [{title}]({url}) - {published}'.format(**entry) for entry in entries]
    )

    rewritten_entries = replace_writing(readme, 'writing', entries_md)
    rewritten_count = replace_writing(
        rewritten_entries,
        'writing_count',
        str(entry_count),
        inline=True,
    )
    readme_path.write_text(rewritten_count, encoding='utf-8')
