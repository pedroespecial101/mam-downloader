# MAM Downloader

A comprehensive tool for searching, downloading, and managing torrents from MyAnonaMouse (MAM). Features modular architecture with BitTorrent support via libtorrent.

## Features

- 🔍 **Search**: Fuzzy search by title and/or author
- 📥 **Download**: Get .torrent files and actual content
- 🌱 **Seeding**: Configurable seeding with ratio and time goals
- 🎯 **Interactive**: Choose from ranked search results
- 🔧 **Modular**: Clean architecture ready for MCP server conversion

## Project Structure

```
mam-downloader/
├── config.py              # Configuration (MAM_ID, settings)
├── mam_api.py            # MAM API client (search, download .torrent files)
├── torrent_downloader.py # BitTorrent download manager (using libtorrent)
├── main_new.py           # New CLI interface (recommended)
├── main.py               # Original script (legacy)
├── requirements.txt      # Python dependencies
└── storage/
    ├── data.json        # Cached API data
    ├── torrents/        # Downloaded .torrent files
    ├── downloads/       # Downloaded content
    └── books/           # Extracted books
```

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/pedroespecial101/mam-downloader.git
   cd mam-downloader
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure your MAM session**
   
   Edit `config.py` and set your `MAM_ID`:
   ```python
   MAM_ID = "your_session_id_here"
   ```
   
   Get your session ID from: https://www.myanonamouse.net/preferences/index.php?view=security

## Usage

### Quick Start

```bash
# Search for a book interactively
python main_new.py --title "Clean Code" --author "Robert Martin"

# Download just the .torrent file
python main_new.py --id 1234567

# Download the actual content via BitTorrent
python main_new.py --id 1234567 --download

# Download and seed with specific goals
python main_new.py --id 1234567 --download --seed --seed-ratio 2.0 --seed-time 7200
```

### Command Line Options

#### Search Options
- `--title` - Search by book title (fuzzy matching)
- `--author` - Search by author name (fuzzy matching)
- `--max-fetch` - Maximum search results to fetch (default: 100)

#### Download Options
- `--id` - Download specific torrent by ID
- `--download` - Download actual content via BitTorrent (not just .torrent file)
- `--torrent-only` - Only download .torrent file, skip content download

#### Seeding Options
- `--seed` - Continue seeding after download completes
- `--seed-ratio` - Target seed ratio before stopping (default: 1.0)
- `--seed-time` - Target seed time in seconds (default: 3600 = 1 hour)

#### Output Options
- `--output-dir` - Override download directory

### Examples

**1. Interactive search and download**
```bash
python main_new.py --title "Dune" --author "Herbert" --download --seed
```

**2. Download specific torrent and seed to 2.0 ratio**
```bash
python main_new.py --id 1197212 --download --seed --seed-ratio 2.0
```

**3. Just get the .torrent file (no content download)**
```bash
python main_new.py --id 1197212
```

**4. Search with custom output directory**
```bash
python main_new.py --title "Foundation" --output-dir ~/Books --download
```

## Module Documentation

### `mam_api.py` - MAM API Client

Handles all interactions with the MyAnonaMouse API:

```python
from mam_api import MAMClient

client = MAMClient(mam_id="your_session_id")

# Search for torrents
torrents = client.search_torrents(title="Clean Code", author="Martin", max_results=10)

# Rank results
ranked = client.rank_search_results(torrents, title="Clean Code", author="Martin")

# Download .torrent file
torrent_path = client.download_torrent_file("1234567")
```

**Key Methods:**
- `get_user_details()` - Get account information
- `search_torrents()` - Search MAM catalog
- `rank_search_results()` - Fuzzy rank search results
- `download_torrent_file()` - Download .torrent file
- `download_batch_torrents()` - Download multiple .torrent files

### `torrent_downloader.py` - BitTorrent Downloader

Manages actual torrent downloads using libtorrent:

```python
from torrent_downloader import TorrentDownloader

downloader = TorrentDownloader(download_dir="storage/downloads")

# Add torrent
info_hash = downloader.add_torrent("path/to/file.torrent")

# Wait for completion with progress updates
downloader.wait_for_completion(info_hash)

# Get progress information
progress = downloader.get_progress(info_hash)
print(f"Progress: {progress.progress*100:.1f}%")
print(f"Download rate: {progress.download_rate} B/s")

# Cleanup
downloader.shutdown()
```

**Simple one-shot download:**
```python
from torrent_downloader import download_torrent

success = download_torrent(
    "path/to/file.torrent",
    download_dir="storage/downloads",
    seed_after=True,
    seed_ratio=1.5,
    seed_time=3600
)
```

**Key Features:**
- Real-time progress tracking
- Configurable upload/download rate limits
- DHT, PEX, and UPnP support
- Pause/resume functionality
- Automatic seeding management

## Configuration

Edit `config.py` to customize behavior:

```python
# MAM Session ID (required)
MAM_ID = "your_session_id"

# Download directory
AUTO_EXTRACT_DIR = "storage/books"

# Search filters
SKIP = ['sSat', 'unsat']  # Lists to exclude from search
SEARCH = {
    "tor": {
        "searchType": "fl-VIP",  # fl-VIP, fl, all, etc.
        "minSize": 0,
        "maxSize": 0,
        "unit": 1048576  # MiB
    }
}

# Webhooks (optional)
DISCORD_WEBHOOK = ""  # Discord webhook for notifications
```

## Workflow Overview

The complete download process follows these stages:

1. **Search** - User searches by title/author
2. **Select** - User chooses from ranked results
3. **Download .torrent** - Fetch .torrent file from MAM
4. **Download Content** - Download actual files via BitTorrent
5. **Seed** (optional) - Seed to configured ratio/time goals

```
┌─────────┐     ┌──────────┐     ┌───────────┐     ┌──────────┐
│ Search  │────▶│  Select  │────▶│ Get .torr │────▶│ Download │
│ MAM API │     │  Result  │     │ent file   │     │ Content  │
└─────────┘     └──────────┘     └───────────┘     └──────────┘
                                                           │
                                                           ▼
                                                    ┌──────────┐
                                                    │   Seed   │
                                                    │ (optional)│
                                                    └──────────┘
```

## Future Plans

### MCP Server Integration

This project is being prepared for Model Context Protocol (MCP) server conversion, which will allow:

- 🤖 **AI Agent Integration** - Control via Claude, ChatGPT, or other AI clients
- 🔌 **Tool Functions** - Expose search/download as MCP tools
- 📡 **Remote Access** - Access your MAM library from anywhere
- 🎛️ **Automation** - Build workflows with AI assistance

**Planned MCP Tools:**
```typescript
- search_mam(title: string, author?: string) → SearchResults
- download_torrent(id: string, download_content: boolean) → DownloadStatus  
- get_download_progress(info_hash: string) → ProgressInfo
- manage_seeding(info_hash: string, action: 'pause' | 'resume' | 'stop')
```

## Troubleshooting

### libtorrent Installation Issues

If you have trouble installing `python-libtorrent`, try:

**macOS:**
```bash
brew install libtorrent-rasterbar
pip install python-libtorrent
```

**Ubuntu/Debian:**
```bash
sudo apt-get install python3-libtorrent
```

**From source:**
```bash
pip install libtorrent
```

### Connection Issues

- Verify your `MAM_ID` is current (sessions can expire)
- Check firewall settings for BitTorrent ports (default: 6881)
- Enable UPnP/NAT-PMP on your router for better connectivity

### Downloads Stalling

- Increase `max_fetch` to get more search results
- Check your ratio - MAM may limit downloads if ratio is low
- Try different search terms or use direct torrent ID

## Contributing

Contributions welcome! Areas for improvement:

- [ ] Resume partial downloads
- [ ] Batch download queue
- [ ] Web UI
- [ ] MCP server implementation
- [ ] Better error handling
- [ ] Rate limiting for API calls
- [ ] Statistics tracking
- [ ] Notification system improvements

## License

This project is for personal use. Respect MyAnonaMouse's terms of service and maintain your ratio!

## Credits

Built with:
- [libtorrent](https://www.libtorrent.org/) - BitTorrent implementation
- [requests](https://requests.readthedocs.io/) - HTTP library
- [MyAnonaMouse](https://www.myanonamouse.net/) - Private tracker

---

**Note:** This tool requires a valid MyAnonaMouse account. Maintain your ratio and follow site rules!
