"""
MyAnonaMouse Downloader - Main CLI interface
Orchestrates search, torrent file download, and BitTorrent downloading.
"""
import argparse
import os
import sys
from typing import Optional, List

import config
from mam_api import MAMClient
from torrent_downloader import TorrentDownloader, download_torrent


def interactive_search(client: MAMClient, title: str = None, author: str = None, max_fetch: int = 100) -> Optional[str]:
    """Interactive search that lets user choose from results.
    
    Args:
        client: MAM API client
        title: Title to search for
        author: Author to search for
        max_fetch: Maximum results to fetch
    
    Returns:
        Selected torrent ID or None
    """
    print(f"\nSearching for: title={title!r} author={author!r}")
    
    # Get user details to exclude already snatched torrents
    user = client.get_user_details()
    snatched_ids = []
    
    if user:
        for list_type in config.SKIP:
            if list_type in client.data:
                snatched_ids.extend(client.data[list_type])
    
    # Search for torrents
    torrents = client.search_torrents(
        title=title,
        author=author,
        max_results=max_fetch,
        snatched_ids=snatched_ids
    )
    
    if not torrents:
        print("No results found.")
        return None
    
    # Rank results
    ranked = client.rank_search_results(torrents, title=title, author=author, top_n=10)
    
    if not ranked:
        print("No close matches found.")
        return None
    
    # Display results
    print(f"\nFound {len(torrents)} results, showing top {len(ranked)}:\n")
    
    for idx, (score, torrent) in enumerate(ranked, start=1):
        tid = torrent.get('id')
        title_str = torrent.get('title', '<no title>')
        
        # Parse author info
        import json
        author_names = ''
        author_info_str = torrent.get('author_info', '')
        if author_info_str:
            try:
                author_dict = json.loads(author_info_str)
                author_names = ', '.join(author_dict.values())
            except:
                pass
        
        # Format size
        size_str = ''
        size_bytes = torrent.get('size', '')
        if size_bytes:
            try:
                size_gb = int(size_bytes) / (1024**3)
                size_str = f"{size_gb:.2f} GB"
            except:
                size_str = size_bytes
        
        author_part = f" by {author_names}" if author_names else ""
        size_part = f" ({size_str})" if size_str else ""
        
        print(f"  {idx:2d}. [{tid}] {title_str}{author_part}{size_part}")
        print(f"      Match score: {score:.2f}")
    
    # Get user choice
    print()
    while True:
        choice = input("Select number to download (or 'q' to cancel): ").strip()
        
        if not choice:
            continue
        
        if choice.lower() == 'q':
            return None
        
        if choice.isdigit():
            n = int(choice)
            if 1 <= n <= len(ranked):
                selected = ranked[n-1][1]
                return str(selected.get('id'))
        
        print("Invalid choice, try again.")


def download_workflow(
    torrent_id: str,
    client: MAMClient,
    downloader: Optional[TorrentDownloader] = None,
    download_content: bool = True,
    seed_after: bool = False,
    seed_ratio: float = 1.0,
    seed_time: int = 3600
) -> bool:
    """Complete workflow: download .torrent file, then download content.
    
    Args:
        torrent_id: ID of torrent to download
        client: MAM API client
        downloader: Optional TorrentDownloader instance (creates one if not provided)
        download_content: Whether to actually download the content via BitTorrent
        seed_after: Whether to seed after download
        seed_ratio: Target seed ratio
        seed_time: Target seed time in seconds
    
    Returns:
        True if successful
    """
    try:
        # Step 1: Download .torrent file from MAM
        print(f"\n{'='*60}")
        print(f"Step 1: Downloading .torrent file for ID {torrent_id}")
        print(f"{'='*60}")
        
        torrent_path = client.download_torrent_file(torrent_id)
        
        if not download_content:
            print(f"\n✓ Torrent file saved to: {torrent_path}")
            print("  (Skipping content download)")
            return True
        
        # Step 2: Download actual content via BitTorrent
        print(f"\n{'='*60}")
        print(f"Step 2: Downloading content via BitTorrent")
        print(f"{'='*60}")
        
        if downloader:
            # Use provided downloader (allows managing multiple torrents)
            info_hash = downloader.add_torrent(torrent_path)
            success = downloader.wait_for_completion(info_hash)
            
            if success and seed_after:
                print(f"\nSeeding until ratio {seed_ratio} or {seed_time}s...")
                import time
                start_time = time.time()
                
                while True:
                    progress = downloader.get_progress(info_hash)
                    if not progress:
                        break
                    
                    downloader._print_progress(progress)
                    
                    elapsed = time.time() - start_time
                    if progress.ratio >= seed_ratio or elapsed >= seed_time:
                        print(f"\n✓ Seeding goal reached (ratio: {progress.ratio:.2f}, time: {int(elapsed)}s)")
                        break
                    
                    time.sleep(1)
            
            return success
        else:
            # Simple one-shot download
            return download_torrent(
                torrent_path,
                download_dir=config.AUTO_EXTRACT_DIR or "storage/downloads",
                seed_after=seed_after,
                seed_ratio=seed_ratio,
                seed_time=seed_time
            )
    
    except Exception as e:
        print(f"Error during download: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="MyAnonaMouse Search & Download Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search and choose interactively
  python main.py --title "Clean Code" --author "Robert Martin"
  
  # Download specific torrent (torrent file only)
  python main.py --id 1234567
  
  # Download and get the actual content via BitTorrent
  python main.py --id 1234567 --download
  
  # Download and seed with specific ratio/time goals
  python main.py --id 1234567 --download --seed --seed-ratio 2.0 --seed-time 7200
        """
    )
    
    # Search options
    parser.add_argument("--title", help="Search by title")
    parser.add_argument("--author", help="Search by author")
    parser.add_argument("--max-fetch", type=int, default=100, help="Max search results to fetch (default: 100)")
    
    # Direct download options
    parser.add_argument("--id", help="Download specific torrent by ID")
    
    # Download options
    parser.add_argument("--download", action="store_true", 
                       help="Download actual content via BitTorrent (not just .torrent file)")
    parser.add_argument("--torrent-only", action="store_true",
                       help="Only download .torrent file, don't download content")
    
    # Seeding options
    parser.add_argument("--seed", action="store_true", 
                       help="Seed after download completes")
    parser.add_argument("--seed-ratio", type=float, default=1.0,
                       help="Target seed ratio (default: 1.0)")
    parser.add_argument("--seed-time", type=int, default=3600,
                       help="Target seed time in seconds (default: 3600)")
    
    # Output options
    parser.add_argument("--output-dir", help="Override download directory")
    
    args = parser.parse_args()
    
    # Validate config
    if not config.MAM_ID:
        print("Error: MAM_ID not set in config.py")
        print("Get your session ID from: https://www.myanonamouse.net/preferences/index.php?view=security")
        return 1
    
    # Initialize MAM client
    client = MAMClient(config.MAM_ID)
    
    # Test connection
    user = client.get_user_details()
    if not user:
        print("Error: Could not connect to MAM. Check your MAM_ID in config.py")
        return 1
    
    print(f"✓ Connected to MAM as: {user.get('username', 'Unknown')}")
    print(f"  Ratio: {user.get('ratio', 'N/A')}")
    print(f"  Bonus: {user.get('bonus', 'N/A')} points")
    
    # Determine download directory
    download_dir = args.output_dir or config.AUTO_EXTRACT_DIR or "storage/downloads"
    os.makedirs(download_dir, exist_ok=True)
    
    # Initialize torrent downloader if needed
    downloader = None
    if args.download and not args.torrent_only:
        downloader = TorrentDownloader(download_dir=download_dir)
    
    try:
        # Mode 1: Direct download by ID
        if args.id:
            success = download_workflow(
                args.id,
                client,
                downloader=downloader,
                download_content=(args.download and not args.torrent_only),
                seed_after=args.seed,
                seed_ratio=args.seed_ratio,
                seed_time=args.seed_time
            )
            
            return 0 if success else 1
        
        # Mode 2: Interactive search
        if args.title or args.author:
            torrent_id = interactive_search(
                client,
                title=args.title,
                author=args.author,
                max_fetch=args.max_fetch
            )
            
            if not torrent_id:
                print("\nNo torrent selected.")
                return 0
            
            success = download_workflow(
                torrent_id,
                client,
                downloader=downloader,
                download_content=(args.download and not args.torrent_only),
                seed_after=args.seed,
                seed_ratio=args.seed_ratio,
                seed_time=args.seed_time
            )
            
            return 0 if success else 1
        
        # No action specified
        parser.print_help()
        return 1
    
    finally:
        if downloader:
            downloader.shutdown()


if __name__ == "__main__":
    sys.exit(main())
