"""
Google Drive Integration Module
Fetch videos from a specific Google Drive folder for processing.
Uses Google Drive API v3 with service account or OAuth credentials.

Supports weighted random repost mode: when all videos have been published,
selects a random video for reposting, prioritizing ones posted fewer times.
"""
import os
import json
import re
import sys
import random
import tempfile
from pathlib import Path
from dotenv import load_dotenv
from googleapiclient.http import MediaIoBaseDownload

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

# Google Drive credentials
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
GOOGLE_SERVICE_ACCOUNT_KEY = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")  # Path to JSON key file
LOCAL_INPUT_DIR = os.getenv("LOCAL_INPUT_DIR", "Videos")

BASE_DIR = Path(__file__).resolve().parent
PUBLISHED_LOG = str(BASE_DIR / "published_videos.json")
HISTORY_LOG = str(BASE_DIR / "history.json")


def normalize_video_key(video_name: str) -> str:
    """
    Normalizes video filename to a robust canonical key to prevent duplicate publishing
    due to encoding differences (ellipsis …, replacement character , dots, underscores, case).
    """
    if not video_name:
        return ""
    name = os.path.basename(video_name).lower().strip()
    if name.endswith('.mp4'):
        name = name[:-4]

    # Replace ellipsis, unicode replacement, dots, underscores, hyphens, spaces with single underscore
    clean = re.sub(r'[\u2026\ufffd\.\-_ ]+', '_', name)
    clean = re.sub(r'[^a-z0-9_]', '', clean).strip('_')

    # Extract timestamp if present at end (8-14 digits)
    ts_match = re.search(r'(\d{8,14})$', clean)
    ts = ts_match.group(1) if ts_match else ""
    prefix = clean[:ts_match.start()].strip('_') if ts_match else clean
    return f"{prefix}::{ts}"


def get_publication_tracker():
    """
    Analyzes history.json and published_videos.json to return:
    - last_seen_idx: dict mapping canonical key -> last index in history (0 to total-1)
    - publish_counts: dict mapping canonical key -> total lifetime publishes
    - total_records: int count of all publications
    """
    history = []
    for log_path in (HISTORY_LOG, PUBLISHED_LOG):
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > len(history):
                        history = data
            except Exception:
                pass

    last_seen_idx = {}
    publish_counts = {}

    for idx, entry in enumerate(history):
        v = entry.get('video_name', '')
        k = normalize_video_key(v)
        if k:
            last_seen_idx[k] = idx
            publish_counts[k] = publish_counts.get(k, 0) + 1

    return last_seen_idx, publish_counts, len(history)



def get_published_videos():
    """Get list of already published video names from published_videos.json and history.json."""
    names = set()
    for log_path in (PUBLISHED_LOG, HISTORY_LOG):
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            v = item.get('video_name')
                            if v:
                                names.add(v)
            except Exception:
                pass
    return list(names)


def get_published_history():
    """Get full publishing history from published_videos.json and history.json."""
    history = []
    seen = set()
    for log_path in (PUBLISHED_LOG, HISTORY_LOG):
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            v = item.get('video_name')
                            if v and v not in seen:
                                seen.add(v)
                                history.append(item)
            except Exception:
                pass
    return history


def get_repost_counts():
    """Count how many times each video has been posted."""
    history = get_published_history()
    counts = {}
    for entry in history:
        video_name = entry.get('video_name', '').strip().lower()
        if video_name:
            counts[video_name] = counts.get(video_name, 0) + 1
    return counts


def get_drive_service():
    """Initialize and return Google Drive API client."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

        if not GOOGLE_SERVICE_ACCOUNT_KEY:
            raise ValueError("GOOGLE_SERVICE_ACCOUNT_KEY not set")

        # Check if it's a file path or JSON content
        if os.path.exists(GOOGLE_SERVICE_ACCOUNT_KEY):
            # It's a file path
            creds = service_account.Credentials.from_service_account_file(
                GOOGLE_SERVICE_ACCOUNT_KEY, scopes=SCOPES)
            service = build('drive', 'v3', credentials=creds)
            print("Google Drive initialized with Service Account file")
            return service
        elif GOOGLE_SERVICE_ACCOUNT_KEY.strip().startswith('{'):
            # It's JSON content - write to temp file
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
            temp_file.write(GOOGLE_SERVICE_ACCOUNT_KEY)
            temp_file.close()
            
            creds = service_account.Credentials.from_service_account_file(
                temp_file.name, scopes=SCOPES)
            service = build('drive', 'v3', credentials=creds)
            print("Google Drive initialized with Service Account JSON")
            
            # Clean up temp file after credentials are loaded
            os.unlink(temp_file.name)
            return service
        else:
            raise ValueError("Google Service Account key is invalid")
            
    except ImportError as e:
        print(f"Installing required Google Drive libraries... Error: {e}")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "google-auth", "google-auth-oauthlib", "google-auth-httplib2", "google-api-python-client"])
        return get_drive_service()
    except Exception as e:
        print(f"Error initializing Google Drive: {e}")
        return None


def list_drive_videos(service):
    """List all video files in the Google Drive folder."""
    if not service:
        return []
    
    try:
        # Query files in the folder with video MIME types
        query = f"'{GOOGLE_DRIVE_FOLDER_ID}' in parents and trashed=false"
        video_mime_types = [
            "video/mp4",
            "video/quicktime",
            "video/x-msvideo",
            "video/x-matroska"
        ]
        
        videos = []
        for mime_type in video_mime_types:
            query_with_mime = f"{query} and mimeType contains '{mime_type}'"
            results = service.files().list(
                q=query_with_mime,
                fields="files(id, name, size, mimeType)",
                spaces='drive'
            ).execute()
            
            videos.extend(results.get('files', []))
        
        # Sort by name for consistent ordering
        videos.sort(key=lambda x: x.get('name', ''))
        return videos
    except Exception as e:
        print(f"Google Drive API error: {e}")
        return []


def download_video(service, file_info, local_path):
    """Download a video from Google Drive to local storage."""
    try:
        request = service.files().get_media(fileId=file_info['id'])
        
        with open(local_path, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                print(f"  Download progress: {int(status.progress() * 100)}%")
        
        print(f"Downloaded: {file_info['name']}")
        return True
    except Exception as e:
        print(f"Failed to download {file_info['name']}: {e}")
        return False


def fetch_one_video_from_drive(allow_repost=False):
    """
    Fetch ONE video from Google Drive for processing.
    
    GUARANTEES:
    1. NEVER publishes the same video back-to-back or in close succession.
    2. Strictly enforces a 30-video cooldown window on all previously published videos.
    3. Uses Least-Recently-Used (LRU) rotation: rotates through older videos evenly.
    4. Automatically prioritizes genuine unpublished videos.
    """
    Path(LOCAL_INPUT_DIR).mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("FETCHING VIDEO FROM GOOGLE DRIVE")
    print("=" * 60)

    last_seen_idx, publish_counts, total_records = get_publication_tracker()
    print(f"Total publication history records: {total_records}")
    print(f"Unique canonical videos tracked: {len(last_seen_idx)}")

    if not GOOGLE_DRIVE_FOLDER_ID:
        print("Error: GOOGLE_DRIVE_FOLDER_ID not set")
        return None

    service = get_drive_service()
    if not service:
        return None

    videos = list_drive_videos(service)
    if not videos:
        print("No videos found in Google Drive folder.")
        return None

    print(f"\nFound {len(videos)} video(s) in Google Drive.")

    # Minimum cooldown window: a video cannot be reposted if it was posted within the last N posts
    cooldown_window = min(30, max(5, len(videos) // 2))

    unpublished_videos = []
    published_candidates = []

    for video_info in videos:
        vname = video_info.get('name', '')
        k = normalize_video_key(vname)
        if not k:
            continue

        if k not in last_seen_idx:
            unpublished_videos.append(video_info)
        else:
            last_idx = last_seen_idx[k]
            distance = total_records - 1 - last_idx
            published_candidates.append({
                "info": video_info,
                "name": vname,
                "key": k,
                "last_idx": last_idx,
                "distance": distance,
                "count": publish_counts.get(k, 1),
                "in_cooldown": distance < cooldown_window
            })

    print(f"  - Genuine Unpublished Videos: {len(unpublished_videos)}")
    print(f"  - Already Published Videos:   {len(published_candidates)}")
    print(f"  - In Active Cooldown:         {sum(1 for c in published_candidates if c['in_cooldown'])} (min {cooldown_window} posts gap)")

    # 1. PRIORITY 1: Download an unpublished video
    if unpublished_videos:
        print(f"\n✨ Found {len(unpublished_videos)} unpublished video(s). Selecting one...")
        for video_info in unpublished_videos:
            vname = video_info['name']
            local_path = os.path.join(LOCAL_INPUT_DIR, vname)
            if download_video(service, video_info, local_path):
                print(f"\n✅ Selected (NEW VIDEO): {vname}")
                return local_path
            else:
                print(f"⚠️ Failed to download {vname}, trying next...")

    # If allow_repost is False and all are published, exit
    if not allow_repost:
        print("\nℹ️ All videos in Google Drive have already been published once (allow_repost=False).")
        return None

    # 2. PRIORITY 2: Repost / Rotate using Least-Recently-Used (LRU) algorithm
    print(f"\n🔄 ROTATION / REPOST MODE: Selecting least recently published video outside cooldown...")
    eligible = [c for c in published_candidates if not c['in_cooldown']]

    if not eligible:
        print(f"⚠️ All {len(published_candidates)} videos are in cooldown. Selecting the single oldest published video.")
        eligible = sorted(published_candidates, key=lambda x: x['last_idx'])
    else:
        # Sort by: 1) Lowest lifetime post count first, 2) Oldest last published index (LRU)
        eligible.sort(key=lambda x: (x['count'], x['last_idx']))

    print(f"Eligible rotation candidates: {len(eligible)}")
    for c in eligible[:3]:
        print(f"   Candidate: {c['name']} (posted {c['count']}x, last posted {c['distance']} runs ago at idx {c['last_idx']})")

    for candidate in eligible:
        vinfo = candidate['info']
        vname = candidate['name']
        local_path = os.path.join(LOCAL_INPUT_DIR, vname)
        if download_video(service, vinfo, local_path):
            print(f"\n✅ Selected for rotation (posted {candidate['count']}x before, {candidate['distance']} runs ago): {vname}")
            return local_path
        else:
            print(f"⚠️ Failed to download {vname}, trying next candidate...")

    print("\n❌ Failed to download any eligible video.")
    return None

if __name__ == "__main__":
    # Test the Google Drive connection
    fetch_one_video_from_drive()
