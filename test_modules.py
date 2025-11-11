#!/usr/bin/env python3
"""
Test script to verify the new modular architecture works correctly.
Run this to test the API client and torrent downloader separately.
"""
import os
import sys

def test_mam_api():
    """Test MAM API client."""
    print("="*60)
    print("Testing MAM API Client")
    print("="*60)
    
    try:
        import config
        from mam_api import MAMClient
        
        if not config.MAM_ID:
            print("❌ MAM_ID not set in config.py")
            return False
        
        client = MAMClient(config.MAM_ID)
        
        # Test user details
        print("\n1. Testing user authentication...")
        user = client.get_user_details()
        
        if not user:
            print("❌ Failed to authenticate")
            return False
        
        print(f"✓ Authenticated as: {user.get('username', 'Unknown')}")
        print(f"  Ratio: {user.get('ratio', 'N/A')}")
        print(f"  Bonus: {user.get('bonus', 'N/A')} points")
        
        # Test search
        print("\n2. Testing search functionality...")
        torrents = client.search_torrents(title="python", max_results=5)
        print(f"✓ Found {len(torrents)} results for 'python'")
        
        if torrents:
            print("\n  First result:")
            t = torrents[0]
            print(f"  - ID: {t.get('id')}")
            print(f"  - Title: {t.get('title', 'N/A')}")
        
        # Test ranking
        print("\n3. Testing search ranking...")
        ranked = client.rank_search_results(torrents, title="python programming", top_n=3)
        print(f"✓ Ranked {len(ranked)} results")
        
        print("\n✅ MAM API tests passed!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure to run: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_torrent_downloader():
    """Test torrent downloader (basic functionality only)."""
    print("\n" + "="*60)
    print("Testing Torrent Downloader")
    print("="*60)
    
    try:
        from torrent_downloader import TorrentDownloader
        
        print("\n1. Testing TorrentDownloader initialization...")
        downloader = TorrentDownloader(download_dir="storage/test_downloads")
        print("✓ TorrentDownloader initialized")
        
        print("\n2. Testing session configuration...")
        # Just verify we can access session info
        torrents = downloader.get_all_torrents()
        print(f"✓ Session active with {len(torrents)} torrents")
        
        print("\n3. Shutting down...")
        downloader.shutdown()
        print("✓ Session closed cleanly")
        
        print("\n✅ Torrent Downloader tests passed!")
        print("   Note: Full download test requires a .torrent file")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure libtorrent is installed:")
        print("   - macOS: brew install libtorrent-rasterbar")
        print("   - Ubuntu: sudo apt-get install python3-libtorrent")
        print("   - pip: pip install python-libtorrent")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """Test integration between components."""
    print("\n" + "="*60)
    print("Testing Integration")
    print("="*60)
    
    try:
        import config
        from mam_api import MAMClient
        from torrent_downloader import TorrentDownloader
        
        print("\n1. Testing complete workflow (without actual download)...")
        
        client = MAMClient(config.MAM_ID)
        
        # Search for something
        print("   - Searching MAM...")
        torrents = client.search_torrents(title="test", max_results=1)
        
        if not torrents:
            print("   - No results (that's ok)")
            print("\n✅ Integration test passed!")
            return True
        
        torrent_id = str(torrents[0].get('id'))
        print(f"   - Found torrent ID: {torrent_id}")
        
        # Download .torrent file
        print("   - Downloading .torrent file...")
        torrent_path = client.download_torrent_file(torrent_id, output_dir="storage/test_torrents")
        print(f"   - Saved to: {torrent_path}")
        
        # Initialize downloader (but don't actually download)
        print("   - Initializing downloader...")
        downloader = TorrentDownloader(download_dir="storage/test_downloads")
        
        print("   - Adding torrent to session (not downloading)...")
        info_hash = downloader.add_torrent(torrent_path)
        print(f"   - Info hash: {info_hash}")
        
        # Get progress once
        progress = downloader.get_progress(info_hash)
        if progress:
            print(f"   - Torrent name: {progress.name}")
        
        # Remove it
        print("   - Removing torrent...")
        downloader.remove_torrent(info_hash, delete_files=True)
        
        # Cleanup
        downloader.shutdown()
        os.remove(torrent_path)
        
        print("\n✅ Integration test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("MAM Downloader - Test Suite")
    print("="*60)
    print()
    
    results = []
    
    # Test MAM API
    results.append(("MAM API", test_mam_api()))
    
    # Test Torrent Downloader
    results.append(("Torrent Downloader", test_torrent_downloader()))
    
    # Test Integration
    results.append(("Integration", test_integration()))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
