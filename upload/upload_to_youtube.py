"""
YouTube Upload Script for FruityToon Shorts
Uses OAuth 2.0 refresh token to upload Shorts to YouTube.
Supports credentials from .env, GitHub Secrets, or local token JSON files.
"""

import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)


def get_authenticated_service():
    """Authenticate using refresh token from environment or token JSON file."""
    # 1. Environment variables
    client_id = (os.getenv('YOUTUBE_CLIENT_ID') or os.getenv('YT_CLIENT_ID', '')).strip()
    client_secret = (os.getenv('YOUTUBE_CLIENT_SECRET') or os.getenv('YT_CLIENT_SECRET', '')).strip()
    refresh_token = (os.getenv('YOUTUBE_REFRESH_TOKEN') or os.getenv('YT_REFRESH_TOKEN', '')).strip()
    token_uri = os.getenv('YOUTUBE_TOKEN_URI', 'https://oauth2.googleapis.com/token').strip()

    # 2. Local token JSON files
    if not all([client_id, client_secret, refresh_token]) or "your_" in client_id.lower():
        possible_token_paths = [
            Path(__file__).parent / "token_fruitytoon ai.json",
            Path(__file__).parent.parent / "token_fruitytoon ai.json",
            Path(__file__).parent / "token_fruitytoonai.json",
            Path(__file__).parent.parent / "token_fruitytoonai.json",
            Path(r"C:\Users\kreg9\Downloads\kreggscode\open code\bots\youtube refresh tokens bot\token_fruitytoon ai.json"),
            Path(r"C:\Users\kreg9\Downloads\kreggscode\open code\bots\youtube refresh tokens bot\token_fruitytoonai.json"),
        ]
        for p in possible_token_paths:
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        client_id = data.get("client_id", "").strip()
                        client_secret = data.get("client_secret", "").strip()
                        refresh_token = data.get("refresh_token", "").strip()
                        token_uri = data.get("token_uri", token_uri).strip()
                        print(f"[youtube] Loaded credentials from: {p.name}")
                        break
                except Exception as e:
                    print(f"[youtube] Error reading {p}: {e}")

    # Debug info (masked)
    def mask(s): return f"{s[:4]}...{s[-4:]}" if s and len(s) > 8 else "MISSING"
    print(f"[youtube] Client ID: {mask(client_id)}")
    print(f"[youtube] Client Secret: {mask(client_secret)}")
    print(f"[youtube] Refresh Token: {mask(refresh_token)}")

    if not all([client_id, client_secret, refresh_token]):
        raise ValueError(
            "Missing credentials! Set YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN "
            "or place token_fruitytoon ai.json in the repository."
        )

    creds = Credentials(
        None,
        refresh_token=refresh_token,
        token_uri=token_uri,
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/youtube"]
    )

    try:
        creds.refresh(Request())
    except Exception as e:
        if "invalid_grant" in str(e).lower():
            print("\n❌ [youtube] AUTH ERROR: Refresh token has EXPIRED or been REVOKED.")
            print("💡 SOLUTION: Generate a new refresh token and update credentials.")
        raise

    return build('youtube', 'v3', credentials=creds)


def upload_to_youtube(video_path, title, description, tags=None, category_id='24', privacy_status='public'):
    """
    Upload video to YouTube as a Short.
    Category 24 = Entertainment (great for cartoon shorts)
    """
    print("\n" + "=" * 60)
    print("🎬 YOUTUBE SHORTS UPLOAD STARTING")
    print("=" * 60)

    video_path_obj = Path(video_path)
    if not video_path_obj.exists():
        error_msg = f"❌ Video file not found: {video_path}"
        print(f"[youtube] {error_msg}")
        return {'status': 'failed', 'error': error_msg, 'platform': 'youtube'}

    # Format title: ensure under 100 chars, append #Shorts if room
    clean_title = title.strip() if title else "FruityToon Daily"
    if "#Shorts" not in clean_title and "#shorts" not in clean_title:
        if len(clean_title) + len(" #Shorts") <= 100:
            clean_title = f"{clean_title} #Shorts"
        else:
            clean_title = clean_title[:91].rstrip() + " #Shorts"
    elif len(clean_title) > 100:
        clean_title = clean_title[:97].rstrip() + "..."

    # Format description: ensure #Shorts is present
    clean_desc = description.strip() if description else ""
    if "#Shorts" not in clean_desc and "#shorts" not in clean_desc:
        clean_desc = f"{clean_desc}\n\n#Shorts #FruityToon #Funny #Animation"

    if tags is None:
        tags = [
            'fruitytoon', 'shorts', 'funny', 'animation', 'cartoon',
            'fruits', 'vegetables', 'healthyeating', 'nutrition', 'comedy',
            'foodfacts', 'fyp'
        ]

    try:
        youtube = get_authenticated_service()
    except Exception as auth_err:
        print(f"[youtube] ❌ Authentication failed: {auth_err}")
        return {'status': 'failed', 'error': str(auth_err), 'platform': 'youtube'}

    body = {
        'snippet': {
            'title': clean_title,
            'description': clean_desc,
            'tags': tags,
            'categoryId': category_id
        },
        'status': {
            'privacyStatus': privacy_status,
            'selfDeclaredMadeForKids': False,
        }
    }

    media = MediaFileUpload(
        str(video_path_obj),
        chunksize=10 * 1024 * 1024,
        resumable=True,
        mimetype='video/mp4'
    )

    print(f"[youtube] 🚀 Uploading: {clean_title}")
    try:
        request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )

        response = None
        retry_count = 0
        max_retries = 5
        while response is None:
            try:
                status, response = request.next_chunk()
                if status:
                    print(f"[youtube] Progress: {int(status.progress() * 100)}%")
                retry_count = 0
            except HttpError as e:
                if e.resp.status in [500, 502, 503, 504] and retry_count < max_retries:
                    retry_count += 1
                    sleep_sec = 2 ** retry_count
                    print(f"[youtube] ⚠️ Transient server error ({e.resp.status}). Retrying chunk in {sleep_sec}s (attempt {retry_count}/{max_retries})...")
                    time.sleep(sleep_sec)
                else:
                    err_msg = e.content.decode('utf-8', errors='ignore') if hasattr(e, 'content') else str(e)
                    print(f"[youtube] ❌ HTTP Error during upload ({e.resp.status}): {err_msg}")
                    return {'status': 'failed', 'error': f"HTTP {e.resp.status}: {err_msg}", 'platform': 'youtube'}
            except (IOError, OSError) as net_err:
                if retry_count < max_retries:
                    retry_count += 1
                    sleep_sec = 2 ** retry_count
                    print(f"[youtube] ⚠️ Network glitch ({net_err}). Retrying chunk in {sleep_sec}s (attempt {retry_count}/{max_retries})...")
                    time.sleep(sleep_sec)
                else:
                    print(f"[youtube] ❌ Network error: {net_err}")
                    return {'status': 'failed', 'error': str(net_err), 'platform': 'youtube'}

        video_id = response.get('id')
        if not video_id:
            print(f"[youtube] ❌ No video ID in response: {response}")
            return {'status': 'failed', 'error': 'No video ID in response', 'platform': 'youtube'}

        print(f"[youtube] ✅ SUCCESS! Uploaded to YouTube!")
        print(f"[youtube] Video ID: {video_id}")
        print(f"[youtube] URL: https://youtube.com/shorts/{video_id}")
        print("=" * 60)

        return {
            'status': 'success',
            'id': video_id,
            'platform': 'youtube',
            'url': f'https://youtube.com/shorts/{video_id}',
            'title': clean_title
        }

    except Exception as e:
        print(f"[youtube] ❌ Unexpected upload error: {e}")
        return {'status': 'failed', 'error': str(e), 'platform': 'youtube'}


def main():
    """Test authentication or upload test."""
    print("Testing YouTube Authentication...")
    try:
        service = get_authenticated_service()
        r = service.channels().list(part='snippet', mine=True).execute()
        title = r.get('items', [{}])[0].get('snippet', {}).get('title', 'Unknown')
        print(f"✅ Successfully authenticated with channel: {title}")
    except Exception as e:
        print(f"❌ YouTube auth test failed: {e}")


if __name__ == '__main__':
    main()
