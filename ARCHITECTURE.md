# MAM Downloader Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface                           │
│                         (main_new.py)                            │
├─────────────────────────────────────────────────────────────────┤
│  • CLI argument parsing                                          │
│  • Interactive search workflow                                   │
│  • Orchestrates API + Downloader                                 │
└────────────────┬────────────────────────┬───────────────────────┘
                 │                        │
                 ▼                        ▼
    ┌────────────────────────┐  ┌────────────────────────┐
    │     MAM API Client     │  │  Torrent Downloader    │
    │     (mam_api.py)       │  │(torrent_downloader.py) │
    ├────────────────────────┤  ├────────────────────────┤
    │ • Search MAM           │  │ • BitTorrent downloads │
    │ • Rank results         │  │ • Progress tracking    │
    │ • Get .torrent files   │  │ • Seeding management   │
    │ • User authentication  │  │ • Rate limiting        │
    └────────────┬───────────┘  └───────────┬────────────┘
                 │                          │
                 ▼                          ▼
    ┌────────────────────────┐  ┌────────────────────────┐
    │   MAM API Server       │  │   BitTorrent Network   │
    │  (myanonamouse.net)    │  │   (DHT, Peers, Seeds)  │
    └────────────────────────┘  └────────────────────────┘
```

## Data Flow - Complete Workflow

```
User Input (CLI)
      │
      ├─→ --title "Book" --author "Author"
      │        │
      │        ▼
      │   [MAMClient.search_torrents()]
      │        │
      │        ├─→ POST to MAM API
      │        │   /tor/js/loadSearchJSONbasic.php
      │        │
      │        ├─→ Receive JSON results
      │        │
      │        ▼
      │   [MAMClient.rank_search_results()]
      │        │
      │        ├─→ Fuzzy match scoring
      │        │
      │        ▼
      │   Interactive Selection (Top 10)
      │        │
      │        ├─→ User chooses #3
      │        │
      │        ▼
      │   [MAMClient.download_torrent_file(id)]
      │        │
      │        ├─→ GET /tor/download.php?tid=12345
      │        │
      │        ├─→ Save .torrent file
      │        │   storage/torrents/book.torrent
      │        │
      │        ▼
      ├─→ --download flag set?
      │        │
      │        ├─→ YES
      │        │   │
      │        │   ▼
      │        │  [TorrentDownloader.add_torrent()]
      │        │   │
      │        │   ├─→ Parse .torrent file
      │        │   │
      │        │   ├─→ Connect to DHT/Peers
      │        │   │
      │        │   ▼
      │        │  [TorrentDownloader.wait_for_completion()]
      │        │   │
      │        │   ├─→ Download pieces
      │        │   │   ├─→ Progress: 0% → 100%
      │        │   │   ├─→ Real-time stats
      │        │   │   └─→ Peer connections
      │        │   │
      │        │   ▼
      │        │  Download Complete!
      │        │   │
      │        │   └─→ storage/downloads/book/
      │        │
      │        ├─→ --seed flag set?
      │        │   │
      │        │   ├─→ YES
      │        │   │   │
      │        │   │   ▼
      │        │   │  [Seeding Loop]
      │        │   │   │
      │        │   │   ├─→ Upload to peers
      │        │   │   ├─→ Monitor ratio
      │        │   │   └─→ Until goal reached
      │        │   │
      │        │   ▼
      │        │  Seeding Complete!
      │        │
      │        └─→ NO
      │            │
      │            ▼
      │         Just save .torrent file
      │
      ▼
    Success!
```

## Module Responsibilities

### 1. main_new.py (Interface Layer)
```
Responsibilities:
├─ Parse command line arguments
├─ Initialize MAMClient and TorrentDownloader
├─ Orchestrate search workflow
├─ Handle user interaction
├─ Error handling and logging
└─ Cleanup on exit

Key Functions:
├─ interactive_search()    → User selection UI
├─ download_workflow()     → Complete download flow
└─ main()                  → Entry point
```

### 2. mam_api.py (API Layer)
```
Responsibilities:
├─ MAM authentication
├─ API request management
├─ Search functionality
├─ Result ranking
├─ .torrent file downloads
└─ Data caching

Key Classes/Methods:
MAMClient
├─ get_user_details()      → Account info
├─ search_torrents()       → Query MAM
├─ rank_search_results()   → Fuzzy matching
├─ download_torrent_file() → Get .torrent
└─ save_data()             → Cache results
```

### 3. torrent_downloader.py (Download Layer)
```
Responsibilities:
├─ BitTorrent protocol handling
├─ Progress tracking
├─ Seeding management
├─ Rate limiting
├─ DHT/PEX/UPnP configuration
└─ Session management

Key Classes/Methods:
TorrentDownloader
├─ add_torrent()              → Queue download
├─ wait_for_completion()      → Blocking wait
├─ get_progress()             → Stats snapshot
├─ pause/resume/remove()      → Control
└─ shutdown()                 → Cleanup

TorrentProgress (dataclass)
├─ state                      → Current state
├─ progress                   → 0.0 to 1.0
├─ download_rate             → bytes/sec
├─ upload_rate               → bytes/sec
├─ num_peers/seeds           → Connections
└─ eta                       → Time remaining
```

## State Machine - Download States

```
   ┌─────────┐
   │ QUEUED  │ ◀─── add_torrent()
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │CHECKING │ (Verifying existing data)
   └────┬────┘
        │
        ▼
   ┌───────────┐
   │DOWNLOADING│ ◀─── resume_torrent()
   └─────┬─────┘
        │├──────► PAUSED (pause_torrent())
        ││
        │▼
        │┌─────────┐
        ││ SEEDING │ (Completed download)
        │└────┬────┘
        │     │
        │     ├──────► Stop (ratio/time met)
        │     │
        ▼     ▼
   ┌─────────┐
   │FINISHED │
   └─────────┘
        │
        ├──────► REMOVED (remove_torrent())
        │
        ▼
   ┌─────────┐
   │  ERROR  │ (If download fails)
   └─────────┘
```

## File System Layout

```
mam-downloader/
│
├── Python Modules
│   ├── config.py              # Configuration
│   ├── mam_api.py            # MAM API client
│   ├── torrent_downloader.py # BitTorrent client
│   ├── main_new.py           # New CLI
│   ├── main.py               # Legacy CLI
│   └── test_modules.py       # Test suite
│
├── Documentation
│   ├── README_NEW.md         # Main docs
│   ├── MIGRATION.md          # Migration guide
│   ├── SUMMARY.md            # Refactor summary
│   ├── ARCHITECTURE.md       # This file
│   └── README.md             # Original readme
│
├── Configuration
│   ├── requirements.txt      # Dependencies
│   ├── setup.sh             # Setup script
│   └── .gitignore           # Git exclusions
│
└── Storage (gitignored)
    ├── data.json            # API cache
    ├── torrents/            # .torrent files
    │   └── [ID]_title.torrent
    ├── downloads/           # Downloaded content
    │   └── book_title/
    │       └── book.epub
    └── books/               # Legacy extraction dir
        └── [ID]_title.torrent
```

## API Interaction Flow

### MAM API Endpoints Used

```
1. Authentication Check
   GET /jsonLoad.php?snatch_summary
   ├─ Headers: Cookie: mam_id=<session>
   └─ Returns: User details, ratio, stats

2. Search
   POST /tor/js/loadSearchJSONbasic.php
   ├─ Body: JSON search parameters
   │   {
   │     "tor": {
   │       "text": "search query",
   │       "srchIn": ["title", "author"],
   │       "searchType": "all",
   │       "startNumber": 0
   │     },
   │     "perpage": 100
   │   }
   └─ Returns: Array of torrent objects

3. Download .torrent
   GET /tor/download.php?tid=<torrent_id>
   ├─ Headers: Cookie: mam_id=<session>
   └─ Returns: Binary .torrent file
```

## BitTorrent Protocol Flow

```
1. Parse .torrent file
   ├─ Extract announce URLs
   ├─ Extract info hash
   ├─ Extract piece information
   └─ Extract file metadata

2. Connect to Network
   ├─ DHT bootstrap
   │   ├─ router.bittorrent.com:6881
   │   ├─ router.utorrent.com:6881
   │   └─ dht.transmissionbt.com:6881
   │
   ├─ Announce to trackers
   │
   └─ Enable peer exchange (PEX)

3. Download Pieces
   ├─ Request pieces from peers
   ├─ Verify piece hashes
   ├─ Write to disk
   └─ Update progress

4. Seed (if enabled)
   ├─ Continue as seed
   ├─ Upload to peers
   ├─ Monitor ratio
   └─ Stop when goals met
```

## Future: MCP Server Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      AI Client                               │
│              (Claude, ChatGPT, etc.)                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ MCP Protocol (JSON-RPC)
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   MCP Server                                 │
│                (mcp_server.py)                               │
├─────────────────────────────────────────────────────────────┤
│  Tools:                                                      │
│  ├─ search_mam(title, author)                               │
│  ├─ download_torrent(id, download_content)                  │
│  ├─ get_progress(info_hash)                                 │
│  ├─ manage_seeding(info_hash, action)                       │
│  └─ get_user_stats()                                        │
└────────────┬──────────────────────┬─────────────────────────┘
             │                      │
             ▼                      ▼
    ┌────────────────┐    ┌────────────────────┐
    │  MAMClient     │    │ TorrentDownloader  │
    │  (mam_api.py)  │    │(torrent_down...py) │
    └────────────────┘    └────────────────────┘
```

### MCP Tool Definitions

```typescript
{
  "name": "search_mam",
  "description": "Search MyAnonaMouse for books by title and/or author",
  "inputSchema": {
    "type": "object",
    "properties": {
      "title": { "type": "string", "description": "Book title" },
      "author": { "type": "string", "description": "Author name" },
      "max_results": { "type": "number", "default": 10 }
    }
  }
}

{
  "name": "download_torrent",
  "description": "Download a torrent by ID with optional content download",
  "inputSchema": {
    "type": "object",
    "properties": {
      "torrent_id": { "type": "string", "required": true },
      "download_content": { "type": "boolean", "default": false },
      "seed_after": { "type": "boolean", "default": false },
      "seed_ratio": { "type": "number", "default": 1.0 }
    }
  }
}
```

## Performance Considerations

### Caching Strategy
```
├─ data.json caches:
│  ├─ User snatch lists (sSat, unsat, etc.)
│  ├─ Last update timestamp
│  └─ Bonus point purchase history
│
└─ Cache invalidation:
   ├─ On user request (--force-refresh)
   └─ After 24 hours
```

### Rate Limiting
```
├─ MAM API: 1 request per second (recommended)
├─ BitTorrent: Configurable upload/download limits
└─ DHT queries: Handled by libtorrent
```

### Resource Usage
```
├─ Memory: ~50-100MB per active torrent
├─ Disk I/O: Depends on download speed
├─ Network: Configurable rate limits
└─ CPU: Minimal (libtorrent handles heavy lifting)
```

## Error Handling Strategy

```
Layer 1: MAM API (mam_api.py)
├─ Connection errors → Retry with backoff
├─ Invalid session → Clear error message
├─ API rate limit → Wait and retry
└─ Parse errors → Log and skip

Layer 2: Torrent Download (torrent_downloader.py)
├─ Connection timeout → Retry with more peers
├─ Invalid .torrent → Abort with clear error
├─ Disk full → Pause and notify
└─ Piece verification fails → Re-download piece

Layer 3: Interface (main_new.py)
├─ Catch all exceptions
├─ Display user-friendly messages
├─ Log technical details
└─ Graceful cleanup
```

---

This modular architecture provides:
- ✅ Clear separation of concerns
- ✅ Easy testing and debugging
- ✅ Reusable components
- ✅ MCP server ready
- ✅ Extensible design
