# MyAnonaMouse Downloader

A Python script to search and download torrents from MyAnonaMouse (MAM).

## Setup

1. Create a virtual environment and install dependencies:
```zsh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

2. Configure your MAM session in `config.py`:
   - Set `MAM_ID` to your session cookie from [MAM Security Settings](https://www.myanonamouse.net/preferences/index.php?view=security)
   - Optionally configure `AUTO_EXTRACT_DIR` for automatic extraction
   - Optionally set `DISCORD_WEBHOOK` for notifications

## Usage

### Search by Title and/or Author (Interactive)

Search for books with fuzzy matching on title and/or author, then interactively choose from the top 10 results:

```zsh
# Search by title only
python3 main.py --title "Harry Potter"

# Search by author only  
python3 main.py --author "Stephen King"

# Search by both title and author (more precise)
python3 main.py --title "1984" --author "Orwell"

# Override extraction directory for this download
python3 main.py --title "Dune" --extract-dir ~/Downloads/books

# Dry run (search and display results without downloading)
python3 main.py --title "Crime and Punishment" --dry-run
```

The script will:
1. Fetch search results from MAM
2. Score them by fuzzy matching against your search terms
3. Display the top 10 matches with title, author, and size
4. Prompt you to enter a number (1-10) to download, or Q to cancel

### Download by Torrent ID

If you already know the torrent ID:

```zsh
python3 main.py --id 12345
```

### Automatic Batch Download (Original Mode)

Run without arguments to use the original batch download mode based on your `config.py` settings:

```zsh
python3 main.py
```

This will:
- Check your unsaturated torrent limit
- Browse for torrents matching your search criteria in `config.SEARCH`
- Download torrents up to your limit
- Optionally extract to `AUTO_EXTRACT_DIR`

## Advanced Options

- `--max-fetch N` - Fetch up to N search results for matching (default: 500)
- `--extract-dir PATH` - Override extraction directory for this run
- `--dry-run` - Preview without downloading

## Configuration

Edit `config.py` to customize:

- **MAM_ID**: Your session cookie (required)
- **DISCORD_WEBHOOK**: Discord webhook URL for notifications
- **AUTO_EXTRACT_DIR**: Directory to extract downloaded torrents
- **AUTO_DEL_BATCH**: Delete zip files after extraction
- **SKIP**: Categories to skip in batch mode
- **SEARCH**: Default search criteria for batch mode

## Examples

```zsh
# Find and download a specific Harry Potter audiobook
python3 main.py --title "Harry Potter and the Philosopher's Stone" --author "J K Rowling"

# Search for any Dune book
python3 main.py --title "Dune"

# Preview Asimov books without downloading
python3 main.py --author "Asimov" --dry-run

# Download torrent by ID to specific directory
python3 main.py --id 992751 --extract-dir ~/Audiobooks
```

## How It Works

### Fuzzy Search
- The script fetches search results from MAM's API
- Uses Python's `difflib.SequenceMatcher` for fuzzy matching
- Exact substring matches score 1.0 (perfect)
- Partial matches score between 0.0 and 1.0
- When both title and author are provided, scores are weighted 70% title / 30% author

### MAM API
- Uses the official MAM `/tor/js/loadSearchJSONbasic.php` endpoint
- Searches across title and author fields
- Returns comprehensive torrent metadata including file sizes, authors, categories

## Troubleshooting

**"Invalid MyAnonaMouse session ID"**
- Your `MAM_ID` in `config.py` has expired or is incorrect
- Get a fresh session cookie from [MAM Security Settings](https://www.myanonamouse.net/preferences/index.php?view=security)

**"No search results returned"**
- Try a more general search term
- Check if the book exists on MAM by searching on the website
- Use `--dry-run` to test without downloading

**Search returns too many irrelevant results**
- Use both `--title` and `--author` for more precise matching
- The fuzzy matching will rank exact matches higher

## License

For personal use with MyAnonaMouse only. Respect MAM's rules and rate limits.
