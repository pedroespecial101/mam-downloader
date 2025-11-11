import requests
import config
import json
import copy
import os
import math
import time
import zipfile
import argparse

session = requests.Session()
headers = {}
freshLoad = True
base_url = "https://www.myanonamouse.net"
data_dir = "storage"
storage_path = "storage/data.json"
data = {}

# Create data dir
if not os.path.exists(data_dir):
    os.mkdir(data_dir)

# Load previously saved data
if os.path.exists(storage_path):
    with open(storage_path, 'rb') as f:
        data = json.loads(f.read())
        freshLoad = False

# Save data to prevent constant unneeded requests
def saveDataFile() -> bool:
    data['lastSaved'] = time.time()
    with open(storage_path, 'w') as f:
        json.dump(data, f)

def getUserDetails() -> dict:
    headers["cookie"] = f"mam_id={config.MAM_ID}"
    response = session.get(
            f"{base_url}/jsonLoad.php?snatch_summary", 
            headers=headers
        )

    # Invalid MAM_ID?
    if response.status_code != 200:
        return None

    return response.json()

def getSnatchListIds(user: dict, type: str = 'sSat') -> list:
    results = []
    iteration = 0
    keepGoing = True
    previous = None
    
    # Increment through snatched until no results
    while keepGoing:
        response = session.get(
            f"{base_url}/json/loadUserDetailsTorrents.php?uid={user['uid']}&type={type}&iteration={str(iteration)}",
            headers=headers
        )
        unix = time.time()

        cur = response.json()
        # No results remaining, or unsat (returns all at once) - not sure if this is the case for users with 200 limit?
        if not cur['rows']:
            keepGoing = False
            continue
        
        # Filter ids from results
        ids = []
        for row in cur['rows']:
            ids.append(row['id'])

        # Ensure its not the same as last result
        if ids == previous:
            keepGoing = False
            continue

        previous = ids
        results.extend(ids)
        iteration += 1

    return results

def getTorrents(snatched: list = [], amount: int = 100):
    keepGoing = True
    iteration = 0 
    results = []
    
    while keepGoing:
        config.SEARCH['perpage'] = 100
        config.SEARCH['tor']['startNumber'] = iteration

        # Use search endpoint
        response = session.post(
            f"{base_url}/tor/js/loadSearchJSONbasic.php", 
            headers=headers,
            json=config.SEARCH
        )

        cur = response.json()

        # Stop loop if error occurs
        if 'error' in cur:
            keepGoing = False
            continue

        page_amt = len(cur['data'])
        print(f"Checking torrents {iteration}-{iteration+page_amt}")

        # Sort through data
        for torrent in cur['data']:
            id = str(torrent['id'])

            # Check if snatched already
            if id in snatched or id in results:
                continue

            # Add if desired count hasn't been reached
            if len(results) < amount:
                results.append(id)

        iteration += page_amt

        # Stop search if desired count reached, <future> or no more results
        if len(results) >= amount:
            keepGoing = False

    return results

def fetchTorrents(snatched: list = [], max_results: int = 500, title: str = None, author: str = None):
    """Fetch full torrent objects from the search endpoint (not only ids).

    If title/author are provided, they will be injected into a copy of
    `config.SEARCH` (as tor.text and tor.srchIn) so the API performs a text
    search rather than returning nothing.
    """
    keepGoing = True
    iteration = 0
    results = []

    # If searching by title/author, use a clean search payload optimized for text search
    # Otherwise use the config.SEARCH settings
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
        
        # Create a minimal, clean payload for text search (don't inherit size filters from config)
        base_payload = {
            "tor": {
                "text": text,
                "srchIn": srch_in_fields,
                "searchType": "all",
                "sortType": "default",
                "searchIn": "torrents",
                "cat": ["0"],  # All categories
                "startNumber": 0
            }
        }
    else:
        # Use config settings for non-text searches
        base_payload = copy.deepcopy(config.SEARCH)

    while keepGoing:
        # Respect perpage and pagination on the working payload copy
        base_payload['perpage'] = 100
        base_payload.setdefault('tor', {})
        base_payload['tor']['startNumber'] = iteration

        response = session.post(
            f"{base_url}/tor/js/loadSearchJSONbasic.php",
            headers=headers,
            json=base_payload
        )

        cur = response.json()

        # Stop loop if error occurs
        if 'error' in cur:
            break

        page_amt = len(cur.get('data', []))

        for torrent in cur.get('data', []):
            tid = str(torrent.get('id'))
            if tid in snatched:
                continue
            results.append(torrent)
            if len(results) >= max_results:
                keepGoing = False
                break

        iteration += page_amt

        if page_amt == 0:
            break

    return results


def fuzzy_score(query: str, target) -> float:
    """Simple fuzzy scoring using SequenceMatcher; returns 0..1."""
    from difflib import SequenceMatcher
    if not query or not target:
        return 0.0
    # Convert target to string in case it's a number
    q = str(query).lower().strip()
    t = str(target).lower().strip()
    # exact substring gives boost
    if q in t:
        return 1.0
    return SequenceMatcher(None, q, t).ratio()


def choose_from_search(title: str = None, author: str = None, snatched: list = None, max_fetch: int = 500) -> str:
    """Search for torrents matching title/author and prompt the user to pick one.

    Returns the chosen torrent id as a string, or None if cancelled.
    """
    snatched = snatched or []
    print(f"Searching for title={title!r} author={author!r} (fetching up to {max_fetch} results)")
    torrents = fetchTorrents(snatched, max_fetch, title=title, author=author)
    if not torrents:
        print("No search results returned from server.")
        return None

    scored = []
    for t in torrents:
        # MAM API uses 'title' for the torrent title
        t_title = t.get('title', '')
        
        # MAM API has 'author_info' as a JSON string like {"8234": "Kerrelyn Sparks"}
        # Parse it and concatenate author names
        t_author = ''
        author_info_str = t.get('author_info', '')
        if author_info_str:
            try:
                author_dict = json.loads(author_info_str)
                t_author = ' '.join(author_dict.values())
            except:
                pass
        
        # Also check owner_name as fallback
        if not t_author:
            t_author = t.get('owner_name', '')

        title_score = fuzzy_score(title, t_title) if title else 0
        author_score = fuzzy_score(author, t_author) if author else 0

        if title and author:
            score = title_score * 0.7 + author_score * 0.3
        else:
            score = max(title_score, author_score)

        scored.append((score, t))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [item for item in scored if item[0] > 0][:10]

    if not top:
        print("No close matches found.")
        return None

    print("\nTop results:")
    for idx, (score, t) in enumerate(top, start=1):
        tid = t.get('id')
        title_str = t.get('title', '<no title>')
        
        # Extract author names from author_info JSON
        author_names = ''
        author_info_str = t.get('author_info', '')
        if author_info_str:
            try:
                author_dict = json.loads(author_info_str)
                author_names = ', '.join(author_dict.values())
            except:
                pass
        
        # Format size nicely (it comes as bytes string)
        size_bytes = t.get('size', '')
        size_str = ''
        if size_bytes:
            try:
                size_gb = int(size_bytes) / (1024**3)
                size_str = f"{size_gb:.2f} GB"
            except:
                size_str = size_bytes
        
        author_part = f" by {author_names}" if author_names else ""
        size_part = f" ({size_str})" if size_str else ""
        print(f"{idx}. [{tid}] {title_str}{author_part}{size_part} [score: {score:.2f}]")

    while True:
        choice = input("Enter number to download, or Q to cancel: ").strip()
        if not choice:
            continue
        if choice.lower() == 'q':
            return None
        if choice.isdigit():
            n = int(choice)
            if 1 <= n <= len(top):
                selected = top[n-1][1]
                return str(selected.get('id'))
        print("Invalid choice, try again.")

def downloadBatch(ids: list):
    # Download in batches, the site only allows 100 at a time
    for i in range(0, len(ids), 100):
        batch = ids[i:i + 100]
        tids = '&'.join([f'tids[]={id}' for id in batch])

        response = session.get(
            f"{base_url}/DownloadZips.php?type=batch&{tids}", 
            headers={**headers, "Content-Type": "application/x-zip"},
            timeout=30
        )

        # Write result to zip file
        path = os.path.join(data_dir, f"batch_{time.time()}.zip")
        with open(path, 'wb') as f:
            f.write(response.content) 

        # Extract to specified dir
        if config.AUTO_EXTRACT_DIR:
            print(f"Extracting {path} to {config.AUTO_EXTRACT_DIR}")
            with zipfile.ZipFile(path, 'r') as f:
                f.extractall(config.AUTO_EXTRACT_DIR)
            if config.AUTO_DEL_BATCH:
                os.remove(path)

        time.sleep(5)

def sendWebhook(content: str = None, fields: dict = None):
    """Send a Discord webhook using a plain HTTP POST (no discord.py required).

    This keeps the script lightweight and avoids importing audio-related
    modules from `discord.py` which can fail in some Python builds.
    """
    url = config.DISCORD_WEBHOOK
    # Skip if no url set in configuration
    if not url:
        return

    embed = {
        "title": "MyAnonaMouse Helper",
        "description": content or "",
        "color": 14858496,
        "thumbnail": {"url": "https://i.imgur.com/unDUs13.png"},
        "fields": []
    }

    if fields:
        for name, value in fields.items():
            embed["fields"].append({"name": str(name), "value": str(value), "inline": True})

    payload = {"embeds": [embed]}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        # Don't crash the main flow just because webhook failed
        print(f"Failed to send webhook: {e}")

def main():
    parser = argparse.ArgumentParser(description="MyAnonaMouse downloader helper")
    parser.add_argument("--id", dest="torrent_id", help="Download a single torrent by id and exit")
    parser.add_argument("--title", dest="title", help="Fuzzy title search")
    parser.add_argument("--author", dest="author", help="Fuzzy author search")
    parser.add_argument("--extract-dir", dest="extract_dir", help="Override extract directory for this run")
    parser.add_argument("--max-fetch", dest="max_fetch", type=int, default=500, help="How many search results to fetch for matching (default: 500)")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="Do everything except write/download files")
    args = parser.parse_args()

    # Check if we can get user details correctly
    user = getUserDetails()
    if not user:
        print("Invalid MyAnonaMouse session ID provided, set this value in config.py")
        return
    # If a specific torrent id was passed, download it and exit
    if args.torrent_id:
        tid = str(args.torrent_id)
        print(f"Downloading single torrent id {tid}")
        if args.dry_run:
            print("Dry run enabled - not performing actual download")
            return
        downloadBatch([tid])
        return
        
    # Check if anything should be done 
    unsat = user['unsat']['count'] 
    limit = user['unsat']['limit']

    # Create data file with base data if doesn't exist
    if not data:
        data["lastDonate"] = 0
        data["statsLastSend"] = 0
        saveDataFile()

    # Send a webhook containing stats
    if config.STATS_NOTIFICATION_INTERVAL:
        elapsed = time.time() - data["statsLastSend"]
        if elapsed > config.STATS_NOTIFICATION_INTERVAL:
            # Calculate their ratio
            uploaded = user["uploaded_bytes"]
            downloaded =  user["downloaded_bytes"]
            ratio =  math.inf if downloaded == 0 else uploaded / downloaded

            sendWebhook(fields={
                "Uploaded": user['uploaded'],
                "Downloaded": user['downloaded'],
                "Ratio": f"{ratio:.2f}"
            })

            data["statsLastSend"] = time.time()
            saveDataFile()

    # Spend free bonus points
    if config.AUTO_SPEND_POINTS:
        r = session.get(
            f"{base_url}/json/bonusBuy.php/?spendtype=upload&amount=Max Affordable ", 
            headers=headers
        ).json()

        # Extract results and send to webhook
        if r["success"]:
            sendWebhook(content="{} GB upload credit purchased.".format(r["amount"]))

    # Skip if no more torrents should be added
    if unsat >= limit:
        print(f"You've reached your unsaturated torrent limit, not continuing.")
        return
    
    # Create a list which we can check ids against to avoid duplicates
    skip_ids = []
    for value in config.SKIP:
        count = user[value]['count']
        # Do the check if not saved or saved count differs from last check
        if value not in data or count != len(data[value]):
            print(f"Storing {count} items from {value} list")
            data[value] = getSnatchListIds(user, value)
            saveDataFile()
        skip_ids.extend(data[value])
    
    skip_ids = list(set(skip_ids))

    # If user asked to search by title/author, present interactive choices
    if args.title or args.author:
        chosen_id = choose_from_search(title=args.title, author=args.author, snatched=skip_ids, max_fetch=args.max_fetch)
        if not chosen_id:
            print("No selection made, exiting.")
            return

        print(f"Downloading selected torrent id {chosen_id}")
        if args.dry_run:
            print("Dry run enabled - not performing actual download")
            return

        # Override extract dir if provided for this run
        old_extract = config.AUTO_EXTRACT_DIR
        if args.extract_dir:
            config.AUTO_EXTRACT_DIR = args.extract_dir
            os.makedirs(config.AUTO_EXTRACT_DIR, exist_ok=True)

        downloadBatch([chosen_id])

        # restore
        config.AUTO_EXTRACT_DIR = old_extract
        return

    # Browse for torrents
    amount = limit - unsat
    print(f"Grabbing {amount} torrents with specified criteria")
    ids = getTorrents(skip_ids, amount)
    
    # Download grabbed torrents
    if ids:
        print(f"Downloading batch of {len(ids)} torrents")
        downloadBatch(ids)

if __name__ == "__main__":
    main()
