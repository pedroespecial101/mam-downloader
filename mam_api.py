"""
MyAnonaMouse API client for searching and downloading torrent files.
"""
import requests
import json
import time
import os
from typing import Optional, List, Dict, Tuple


class MAMClient:
    """Client for interacting with MyAnonaMouse API."""
    
    def __init__(self, mam_id: str, data_dir: str = "storage"):
        """Initialize MAM client.
        
        Args:
            mam_id: MyAnonaMouse session ID
            data_dir: Directory for storing data files
        """
        self.mam_id = mam_id
        self.data_dir = data_dir
        self.base_url = "https://www.myanonamouse.net"
        self.session = requests.Session()
        self.headers = {"cookie": f"mam_id={self.mam_id}"}
        self.storage_path = os.path.join(data_dir, "data.json")
        self.data = {}
        
        # Create data dir if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)
        
        # Load previously saved data
        if os.path.exists(self.storage_path):
            with open(self.storage_path, 'rb') as f:
                self.data = json.loads(f.read())
    
    def save_data(self) -> None:
        """Save data to prevent constant unneeded requests."""
        self.data['lastSaved'] = time.time()
        with open(self.storage_path, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def get_user_details(self) -> Optional[dict]:
        """Get user details from MAM.
        
        Returns:
            User details dict or None if request fails
        """
        response = self.session.get(
            f"{self.base_url}/jsonLoad.php?snatch_summary",
            headers=self.headers
        )
        
        if response.status_code != 200:
            return None
        
        return response.json()
    
    def get_snatch_list_ids(self, user: dict, list_type: str = 'sSat') -> List[str]:
        """Get list of torrent IDs from a user's snatch list.
        
        Args:
            user: User details dict
            list_type: Type of list (sSat, unsat, etc.)
        
        Returns:
            List of torrent IDs
        """
        results = []
        iteration = 0
        keep_going = True
        previous = None
        
        while keep_going:
            response = self.session.get(
                f"{self.base_url}/json/loadUserDetailsTorrents.php?uid={user['uid']}&type={list_type}&iteration={iteration}",
                headers=self.headers
            )
            
            cur = response.json()
            if not cur.get('rows'):
                break
            
            ids = [row['id'] for row in cur['rows']]
            
            if ids == previous:
                break
            
            previous = ids
            results.extend(ids)
            iteration += 1
        
        return results
    
    def search_torrents(
        self,
        title: Optional[str] = None,
        author: Optional[str] = None,
        search_config: Optional[dict] = None,
        max_results: int = 100,
        snatched_ids: Optional[List[str]] = None
    ) -> List[dict]:
        """Search for torrents on MAM.
        
        Args:
            title: Title to search for
            author: Author to search for
            search_config: Custom search configuration
            max_results: Maximum number of results to return
            snatched_ids: List of already snatched torrent IDs to exclude
        
        Returns:
            List of torrent dicts
        """
        snatched_ids = snatched_ids or []
        results = []
        iteration = 0
        
        # Build search payload
        if title or author:
            text_parts = []
            srch_in_fields = []
            
            if title:
                text_parts.append(title)
                srch_in_fields.append('title')
            if author:
                text_parts.append(author)
                srch_in_fields.append('author')
            
            text = ' '.join(text_parts)
            
            payload = {
                "tor": {
                    "text": text,
                    "srchIn": srch_in_fields,
                    "searchType": "all",
                    "sortType": "default",
                    "searchIn": "torrents",
                    "cat": ["0"],
                    "startNumber": 0
                }
            }
        else:
            payload = search_config or {
                "tor": {
                    "searchType": "all",
                    "startNumber": 0
                }
            }
        
        while len(results) < max_results:
            payload['perpage'] = 100
            payload['tor']['startNumber'] = iteration
            
            response = self.session.post(
                f"{self.base_url}/tor/js/loadSearchJSONbasic.php",
                headers=self.headers,
                json=payload
            )
            
            cur = response.json()
            
            if 'error' in cur or not cur.get('data'):
                break
            
            for torrent in cur['data']:
                tid = str(torrent.get('id'))
                if tid not in snatched_ids:
                    results.append(torrent)
                    if len(results) >= max_results:
                        break
            
            iteration += len(cur['data'])
            
            if len(cur['data']) == 0:
                break
        
        return results
    
    def fuzzy_score(self, query: str, target: str) -> float:
        """Calculate fuzzy match score between query and target.
        
        Args:
            query: Search query
            target: Target string to match against
        
        Returns:
            Score between 0 and 1
        """
        from difflib import SequenceMatcher
        
        if not query or not target:
            return 0.0
        
        q = str(query).lower().strip()
        t = str(target).lower().strip()
        
        if q in t:
            return 1.0
        
        return SequenceMatcher(None, q, t).ratio()
    
    def rank_search_results(
        self,
        torrents: List[dict],
        title: Optional[str] = None,
        author: Optional[str] = None,
        top_n: int = 10
    ) -> List[Tuple[float, dict]]:
        """Rank search results by relevance.
        
        Args:
            torrents: List of torrent dicts
            title: Title to match against
            author: Author to match against
            top_n: Number of top results to return
        
        Returns:
            List of (score, torrent) tuples, sorted by score
        """
        scored = []
        
        for t in torrents:
            t_title = t.get('title', '')
            
            # Parse author info
            t_author = ''
            author_info_str = t.get('author_info', '')
            if author_info_str:
                try:
                    author_dict = json.loads(author_info_str)
                    t_author = ' '.join(author_dict.values())
                except:
                    pass
            
            if not t_author:
                t_author = t.get('owner_name', '')
            
            title_score = self.fuzzy_score(title, t_title) if title else 0
            author_score = self.fuzzy_score(author, t_author) if author else 0
            
            if title and author:
                score = title_score * 0.7 + author_score * 0.3
            else:
                score = max(title_score, author_score)
            
            scored.append((score, t))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for item in scored if item[0] > 0][:top_n]
    
    def download_torrent_file(self, torrent_id: str, output_dir: str = None) -> str:
        """Download a .torrent file from MAM.
        
        Args:
            torrent_id: ID of the torrent to download
            output_dir: Directory to save the torrent file (defaults to storage/torrents)
        
        Returns:
            Path to the downloaded torrent file
        """
        if output_dir is None:
            output_dir = os.path.join(self.data_dir, "torrents")
        
        os.makedirs(output_dir, exist_ok=True)
        
        response = self.session.get(
            f"{self.base_url}/tor/download.php?tid={torrent_id}",
            headers=self.headers
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to download torrent {torrent_id}: {response.status_code}")
        
        # Try to get filename from Content-Disposition header
        filename = None
        if 'Content-Disposition' in response.headers:
            content_disp = response.headers['Content-Disposition']
            if 'filename=' in content_disp:
                filename = content_disp.split('filename=')[1].strip('"')
        
        if not filename:
            filename = f"{torrent_id}.torrent"
        
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        print(f"Downloaded torrent file: {filepath}")
        return filepath
    
    def download_batch_torrents(self, torrent_ids: List[str], output_dir: str = None) -> List[str]:
        """Download multiple torrent files.
        
        Args:
            torrent_ids: List of torrent IDs to download
            output_dir: Directory to save torrent files
        
        Returns:
            List of paths to downloaded torrent files
        """
        paths = []
        for tid in torrent_ids:
            try:
                path = self.download_torrent_file(tid, output_dir)
                paths.append(path)
                time.sleep(1)  # Be nice to the server
            except Exception as e:
                print(f"Error downloading torrent {tid}: {e}")
        
        return paths
