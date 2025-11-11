# Migration Guide: Old vs New Architecture

## Overview

The project has been refactored from a single monolithic script to a modular architecture with three main components:

1. **`mam_api.py`** - MAM API interactions
2. **`torrent_downloader.py`** - BitTorrent downloading
3. **`main_new.py`** - CLI orchestration

## File Comparison

### Old Structure
```
main.py (490 lines)
├── MAM API calls
├── Search logic
├── Download logic
└── CLI interface
```

### New Structure
```
mam_api.py (350+ lines)
├── MAMClient class
├── Search methods
└── .torrent file download

torrent_downloader.py (400+ lines)
├── TorrentDownloader class
├── Progress tracking
└── Seeding management

main_new.py (300+ lines)
├── CLI argument parsing
├── Interactive search
└── Workflow orchestration
```

## Key Changes

### 1. MAM API is Now a Class

**Old (main.py):**
```python
def getUserDetails():
    response = session.get(...)
    return response.json()

def fetchTorrents(snatched, max_results, title, author):
    # ... complex logic with globals
    return results
```

**New (mam_api.py):**
```python
class MAMClient:
    def __init__(self, mam_id: str):
        self.mam_id = mam_id
        self.session = requests.Session()
    
    def get_user_details(self) -> Optional[dict]:
        response = self.session.get(...)
        return response.json()
    
    def search_torrents(self, title=None, author=None, ...):
        # Clean, self-contained logic
        return results
```

### 2. Separated Concerns

**Old Approach:**
- `downloadBatch()` downloaded .zip files containing .torrent files
- Extracted them automatically
- No way to actually download the content via BitTorrent

**New Approach:**
- `MAMClient.download_torrent_file()` downloads individual .torrent files
- `TorrentDownloader` handles actual BitTorrent downloads
- `download_workflow()` orchestrates both steps
- Clear separation between getting .torrent files and downloading content

### 3. BitTorrent Support

**New Feature:**
```python
from torrent_downloader import TorrentDownloader

downloader = TorrentDownloader(download_dir="storage/downloads")
info_hash = downloader.add_torrent("path/to/file.torrent")
downloader.wait_for_completion(info_hash)
```

This was not possible in the old architecture.

### 4. CLI Interface

**Old (main.py):**
```bash
# Search and auto-download
python main.py --title "Book" --author "Author"

# Download by ID
python main.py --id 12345
```

**New (main_new.py):**
```bash
# Search only (interactive choice, downloads .torrent file)
python main_new.py --title "Book" --author "Author"

# Search and download content
python main_new.py --title "Book" --author "Author" --download

# Download by ID (just .torrent file)
python main_new.py --id 12345

# Download by ID with content
python main_new.py --id 12345 --download

# Download and seed
python main_new.py --id 12345 --download --seed --seed-ratio 2.0
```

## Migration Steps

### Step 1: Install New Dependencies

```bash
pip install -r requirements.txt
```

This adds `python-libtorrent` for BitTorrent support.

### Step 2: Test Your Configuration

```bash
python test_modules.py
```

This will verify:
- Your MAM_ID works
- You can search
- libtorrent is installed correctly

### Step 3: Try the New CLI

Start with a simple search:
```bash
python main_new.py --title "Python" --author "Lutz"
```

This will:
1. Search MAM
2. Show top 10 ranked results
3. Let you choose one
4. Download the .torrent file

### Step 4: Try Content Download

Once comfortable, try downloading actual content:
```bash
python main_new.py --id 1234567 --download
```

### Step 5: Configure Seeding

Enable seeding to maintain your ratio:
```bash
python main_new.py --id 1234567 --download --seed --seed-ratio 1.5 --seed-time 3600
```

## Feature Comparison

| Feature | Old (main.py) | New (main_new.py) |
|---------|---------------|-------------------|
| MAM Search | ✅ | ✅ |
| Fuzzy Matching | ✅ | ✅ |
| Interactive Selection | ✅ | ✅ |
| Download .torrent files | ✅ (batch zips) | ✅ (individual) |
| BitTorrent Download | ❌ | ✅ |
| Seeding | ❌ | ✅ |
| Progress Tracking | ❌ | ✅ |
| Modular API | ❌ | ✅ |
| Type Hints | ❌ | ✅ |
| Documentation | Minimal | Comprehensive |

## Code Examples

### Using MAMClient Directly

```python
from mam_api import MAMClient
import config

client = MAMClient(config.MAM_ID)

# Search
results = client.search_torrents(title="Foundation", author="Asimov")

# Rank results
ranked = client.rank_search_results(results, title="Foundation", author="Asimov")

# Download .torrent file
for score, torrent in ranked[:3]:
    torrent_id = str(torrent['id'])
    path = client.download_torrent_file(torrent_id)
    print(f"Downloaded: {path}")
```

### Using TorrentDownloader Directly

```python
from torrent_downloader import download_torrent

success = download_torrent(
    torrent_path="storage/torrents/book.torrent",
    download_dir="storage/downloads",
    seed_after=True,
    seed_ratio=1.5,
    seed_time=3600
)

if success:
    print("Download complete!")
```

### Complete Workflow

```python
from mam_api import MAMClient
from torrent_downloader import TorrentDownloader
import config

# Initialize
client = MAMClient(config.MAM_ID)
downloader = TorrentDownloader(download_dir="storage/downloads")

# Search
results = client.search_torrents(title="Clean Code")
ranked = client.rank_search_results(results, title="Clean Code")

# Download first result
torrent_id = str(ranked[0][1]['id'])
torrent_path = client.download_torrent_file(torrent_id)

# Download content
info_hash = downloader.add_torrent(torrent_path)
success = downloader.wait_for_completion(info_hash)

# Cleanup
downloader.shutdown()
```

## Benefits of New Architecture

1. **Modularity**: Each component has a single responsibility
2. **Testability**: Easy to test each module independently
3. **Reusability**: Use `MAMClient` or `TorrentDownloader` in other projects
4. **Type Safety**: Type hints throughout for better IDE support
5. **Documentation**: Comprehensive docstrings and README
6. **MCP Ready**: Easy to convert to Model Context Protocol server
7. **BitTorrent Support**: Actually download content, not just .torrent files
8. **Progress Tracking**: Real-time download progress and statistics
9. **Seeding**: Maintain ratio with configurable seeding goals

## Backward Compatibility

The old `main.py` still works and is preserved. You can continue using it if needed:

```bash
python main.py --title "Book" --author "Author"
```

However, it won't have the new features:
- BitTorrent downloading
- Progress tracking
- Seeding
- Modular API access

## Next Steps

1. **Test the new system**: Run `python test_modules.py`
2. **Try some searches**: Use `main_new.py` for interactive searches
3. **Download content**: Test BitTorrent downloading with `--download`
4. **Configure seeding**: Maintain your ratio with `--seed`
5. **Build on the API**: Use the modules in your own scripts
6. **MCP Server**: Coming soon - control via AI agents!

## Need Help?

- Check `README_NEW.md` for comprehensive documentation
- Run `python main_new.py --help` for CLI options
- Look at `test_modules.py` for usage examples
- Original `main.py` is still there as reference

## Questions?

**Q: Should I delete the old main.py?**
A: Keep it for now as a reference. Once you're comfortable with the new system, you can remove it or rename it to `main_legacy.py`.

**Q: Do I need to change my config.py?**
A: No changes required! The new system uses the same config.

**Q: What if I just want .torrent files, not full downloads?**
A: That's the default! Just don't pass `--download` flag.

**Q: How much upload/download bandwidth will this use?**
A: You can configure rate limits in `TorrentDownloader()` constructor. Default is unlimited.

**Q: Can I use this programmatically?**
A: Yes! Import `MAMClient` and `TorrentDownloader` in your own scripts.
