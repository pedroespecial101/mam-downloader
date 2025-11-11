"""
BitTorrent downloader using libtorrent.
"""
import libtorrent as lt
import time
import os
from typing import Optional, Callable, Dict, List
from dataclasses import dataclass
from enum import Enum


class TorrentState(Enum):
    """Torrent download states."""
    QUEUED = "queued"
    CHECKING = "checking"
    DOWNLOADING = "downloading"
    SEEDING = "seeding"
    PAUSED = "paused"
    FINISHED = "finished"
    ERROR = "error"


@dataclass
class TorrentProgress:
    """Progress information for a torrent download."""
    name: str
    state: TorrentState
    progress: float  # 0.0 to 1.0
    download_rate: float  # bytes/sec
    upload_rate: float  # bytes/sec
    num_peers: int
    num_seeds: int
    total_size: int  # bytes
    downloaded: int  # bytes
    uploaded: int  # bytes
    ratio: float
    eta: int  # seconds, -1 if unknown


class TorrentDownloader:
    """Manages torrent downloads using libtorrent."""
    
    def __init__(
        self,
        download_dir: str = "storage/downloads",
        listen_port: int = 6881,
        max_upload_rate: int = 0,  # 0 = unlimited, KB/s
        max_download_rate: int = 0,  # 0 = unlimited, KB/s
    ):
        """Initialize torrent downloader.
        
        Args:
            download_dir: Directory to save downloaded files
            listen_port: Port for incoming connections
            max_upload_rate: Maximum upload rate in KB/s (0 = unlimited)
            max_download_rate: Maximum download rate in KB/s (0 = unlimited)
        """
        self.download_dir = os.path.abspath(download_dir)
        os.makedirs(self.download_dir, exist_ok=True)
        
        # Create libtorrent session
        self.session = lt.session()
        
        # Configure session settings
        settings = {
            'listen_interfaces': f'0.0.0.0:{listen_port}',
            'enable_dht': True,
            'enable_lsd': True,
            'enable_upnp': True,
            'enable_natpmp': True,
        }
        
        self.session.apply_settings(settings)
        
        # Set rate limits if specified
        if max_upload_rate > 0:
            self.session.set_upload_rate_limit(max_upload_rate * 1024)
        if max_download_rate > 0:
            self.session.set_download_rate_limit(max_download_rate * 1024)
        
        # Add DHT router nodes
        self.session.add_dht_router("router.bittorrent.com", 6881)
        self.session.add_dht_router("router.utorrent.com", 6881)
        self.session.add_dht_router("dht.transmissionbt.com", 6881)
        
        # Track active torrents
        self.handles: Dict[str, lt.torrent_handle] = {}
    
    def add_torrent(
        self,
        torrent_path: str,
        save_path: Optional[str] = None,
        seed_after_download: bool = True
    ) -> str:
        """Add a torrent to the download queue.
        
        Args:
            torrent_path: Path to .torrent file
            save_path: Directory to save the downloaded content (defaults to download_dir)
            seed_after_download: Whether to continue seeding after download completes
        
        Returns:
            Info hash of the added torrent
        """
        if save_path is None:
            save_path = self.download_dir
        
        # Load torrent file
        info = lt.torrent_info(torrent_path)
        
        # Create add_torrent_params
        params = {
            'ti': info,
            'save_path': save_path,
        }
        
        # Add torrent to session
        handle = self.session.add_torrent(params)
        
        # Store handle
        info_hash = str(info.info_hash())
        self.handles[info_hash] = handle
        
        print(f"Added torrent: {info.name()}")
        print(f"Info hash: {info_hash}")
        
        return info_hash
    
    def get_progress(self, info_hash: str) -> Optional[TorrentProgress]:
        """Get progress information for a torrent.
        
        Args:
            info_hash: Info hash of the torrent
        
        Returns:
            TorrentProgress object or None if torrent not found
        """
        if info_hash not in self.handles:
            return None
        
        handle = self.handles[info_hash]
        status = handle.status()
        
        # Map libtorrent state to our TorrentState
        state_map = {
            lt.torrent_status.checking_files: TorrentState.CHECKING,
            lt.torrent_status.downloading_metadata: TorrentState.DOWNLOADING,
            lt.torrent_status.downloading: TorrentState.DOWNLOADING,
            lt.torrent_status.finished: TorrentState.FINISHED,
            lt.torrent_status.seeding: TorrentState.SEEDING,
            lt.torrent_status.checking_resume_data: TorrentState.CHECKING,
        }
        
        state = state_map.get(status.state, TorrentState.DOWNLOADING)
        
        # Calculate ETA
        eta = -1
        if status.download_rate > 0:
            remaining = status.total_wanted - status.total_wanted_done
            eta = int(remaining / status.download_rate)
        
        # Calculate ratio
        ratio = 0.0
        if status.total_done > 0:
            ratio = status.all_time_upload / status.total_done
        
        return TorrentProgress(
            name=status.name,
            state=state,
            progress=status.progress,
            download_rate=status.download_rate,
            upload_rate=status.upload_rate,
            num_peers=status.num_peers,
            num_seeds=status.num_seeds,
            total_size=status.total_wanted,
            downloaded=status.total_wanted_done,
            uploaded=status.all_time_upload,
            ratio=ratio,
            eta=eta
        )
    
    def wait_for_completion(
        self,
        info_hash: str,
        callback: Optional[Callable[[TorrentProgress], None]] = None,
        update_interval: float = 1.0
    ) -> bool:
        """Wait for a torrent to complete downloading.
        
        Args:
            info_hash: Info hash of the torrent
            callback: Optional callback function called with progress updates
            update_interval: How often to check progress (seconds)
        
        Returns:
            True if completed successfully, False if error
        """
        if info_hash not in self.handles:
            return False
        
        handle = self.handles[info_hash]
        
        print(f"\nDownloading: {handle.status().name}")
        
        while not handle.status().is_seeding:
            status = handle.status()
            
            progress = self.get_progress(info_hash)
            if progress and callback:
                callback(progress)
            
            # Print progress
            self._print_progress(progress)
            
            # Check for errors
            if status.error:
                print(f"\nError: {status.error}")
                return False
            
            # Check if finished
            if status.is_finished:
                break
            
            time.sleep(update_interval)
        
        print(f"\n✓ Download complete: {handle.status().name}")
        return True
    
    def _print_progress(self, progress: TorrentProgress):
        """Print progress information to console."""
        if not progress:
            return
        
        # Format rates
        dl_rate = self._format_bytes(progress.download_rate) + "/s"
        ul_rate = self._format_bytes(progress.upload_rate) + "/s"
        downloaded = self._format_bytes(progress.downloaded)
        total = self._format_bytes(progress.total_size)
        
        # Format ETA
        eta_str = self._format_time(progress.eta) if progress.eta >= 0 else "∞"
        
        # Progress bar
        bar_width = 30
        filled = int(bar_width * progress.progress)
        bar = "█" * filled + "░" * (bar_width - filled)
        
        print(
            f"\r{progress.state.value.upper()} [{bar}] "
            f"{progress.progress*100:.1f}% "
            f"({downloaded}/{total}) "
            f"↓ {dl_rate} ↑ {ul_rate} "
            f"Peers: {progress.num_peers} Seeds: {progress.num_seeds} "
            f"ETA: {eta_str}",
            end="", flush=True
        )
    
    def _format_bytes(self, bytes: float) -> str:
        """Format bytes to human readable string."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes < 1024.0:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024.0
        return f"{bytes:.1f} PB"
    
    def _format_time(self, seconds: int) -> str:
        """Format seconds to human readable time string."""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds//60}m {seconds%60}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
    def pause_torrent(self, info_hash: str):
        """Pause a torrent download."""
        if info_hash in self.handles:
            self.handles[info_hash].pause()
    
    def resume_torrent(self, info_hash: str):
        """Resume a paused torrent."""
        if info_hash in self.handles:
            self.handles[info_hash].resume()
    
    def remove_torrent(self, info_hash: str, delete_files: bool = False):
        """Remove a torrent from the session.
        
        Args:
            info_hash: Info hash of the torrent
            delete_files: Whether to delete downloaded files
        """
        if info_hash in self.handles:
            handle = self.handles[info_hash]
            flags = lt.session.delete_files if delete_files else 0
            self.session.remove_torrent(handle, flags)
            del self.handles[info_hash]
    
    def get_all_torrents(self) -> List[str]:
        """Get list of all torrent info hashes in the session.
        
        Returns:
            List of info hashes
        """
        return list(self.handles.keys())
    
    def shutdown(self):
        """Shutdown the torrent session gracefully."""
        print("\nShutting down torrent session...")
        
        # Save resume data for all torrents
        for handle in self.handles.values():
            if handle.is_valid():
                handle.save_resume_data()
        
        # Wait a bit for resume data to be saved
        time.sleep(2)
        
        self.session = None
        self.handles.clear()
        print("Torrent session closed.")


def download_torrent(
    torrent_path: str,
    download_dir: str = "storage/downloads",
    seed_after: bool = False,
    seed_ratio: float = 1.0,
    seed_time: int = 3600  # seconds
) -> bool:
    """Simple function to download a single torrent and optionally seed.
    
    Args:
        torrent_path: Path to .torrent file
        download_dir: Directory to save downloaded content
        seed_after: Whether to seed after download
        seed_ratio: Minimum ratio to reach before stopping (if seed_after=True)
        seed_time: Minimum time to seed in seconds (if seed_after=True)
    
    Returns:
        True if successful, False otherwise
    """
    downloader = TorrentDownloader(download_dir=download_dir)
    
    try:
        info_hash = downloader.add_torrent(torrent_path, save_path=download_dir)
        success = downloader.wait_for_completion(info_hash)
        
        if success and seed_after:
            print(f"\nSeeding until ratio {seed_ratio} or {seed_time}s...")
            start_time = time.time()
            
            while True:
                progress = downloader.get_progress(info_hash)
                if not progress:
                    break
                
                downloader._print_progress(progress)
                
                # Check if seeding goals met
                elapsed = time.time() - start_time
                if progress.ratio >= seed_ratio or elapsed >= seed_time:
                    print(f"\n✓ Seeding goal reached (ratio: {progress.ratio:.2f}, time: {int(elapsed)}s)")
                    break
                
                time.sleep(1)
        
        return success
    
    finally:
        downloader.shutdown()
