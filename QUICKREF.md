# Quick Reference Card

## Installation

```bash
./setup.sh
# OR
pip install -r requirements.txt
```

Edit `config.py` → Set your `MAM_ID`

## Basic Commands

### Search
```bash
python main_new.py --title "Foundation" --author "Asimov"
```

### Download .torrent file only
```bash
python main_new.py --id 1234567
```

### Download content via BitTorrent
```bash
python main_new.py --id 1234567 --download
```

### Download + Seed
```bash
python main_new.py --id 1234567 --download --seed --seed-ratio 2.0
```

## CLI Options

| Option | Description |
|--------|-------------|
| `--title` | Search by book title |
| `--author` | Search by author |
| `--id` | Download by torrent ID |
| `--download` | Download actual content (not just .torrent) |
| `--seed` | Seed after download |
| `--seed-ratio` | Target ratio (default: 1.0) |
| `--seed-time` | Target seed time in seconds (default: 3600) |
| `--output-dir` | Override download directory |
| `--max-fetch` | Max search results (default: 100) |

## Programmatic Usage

### MAM API
```python
from mam_api import MAMClient

client = MAMClient("your_mam_id")
results = client.search_torrents(title="Python")
path = client.download_torrent_file("1234567")
```

### BitTorrent
```python
from torrent_downloader import download_torrent

download_torrent(
    "file.torrent",
    download_dir="downloads",
    seed_after=True,
    seed_ratio=1.5
)
```

## File Structure

```
mam_api.py              # MAM API client
torrent_downloader.py   # BitTorrent downloader
main_new.py            # CLI interface
config.py              # Configuration
storage/
  ├── torrents/        # .torrent files
  └── downloads/       # Downloaded content
```

## Common Workflows

**1. Find and download a book**
```bash
python main_new.py --title "Clean Code" --download
```

**2. Download and seed to maintain ratio**
```bash
python main_new.py --id 1234567 --download --seed
```

**3. Just get .torrent files**
```bash
python main_new.py --title "Python" --max-fetch 50
```

## Testing

```bash
python test_modules.py
```

## Help

```bash
python main_new.py --help
```

## Documentation

- `README_NEW.md` - Full documentation
- `MIGRATION.md` - Old vs new comparison
- `ARCHITECTURE.md` - System design
- `SUMMARY.md` - Refactoring summary

## Quick Tips

✅ Use `--download` to get actual content  
✅ Use `--seed` to maintain your ratio  
✅ Check progress with real-time stats  
✅ Use `--output-dir` for custom locations  
✅ Run `test_modules.py` to verify setup
