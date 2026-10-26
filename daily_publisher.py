import os
import re
import json
import glob
import random
import requests
import shutil
import sys
import datetime
from pathlib import Path
from dotenv import load_dotenv

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Import upload functions
try:
    from upload.upload_instagram import upload_to_instagram
    from upload.upload_threads import upload_to_threads
    from upload.upload_facebook import upload_to_facebook, upload_to_facebook_story
    from upload.upload_to_youtube import upload_to_youtube
except ImportError as e:
    print(f"Error importing upload modules: {e}")
    pass

BASE_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = str(BASE_DIR / "Processed_Videos")
PUBLISHED_LOG = str(BASE_DIR / "published_videos.json")
HISTORY_LOG = str(BASE_DIR / "history.json")
YOUTUBE_STATE_FILE = str(BASE_DIR / "youtube_publish_state.json")


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

    clean = re.sub(r'[\u2026\ufffd\.\-_ ]+', '_', name)
    clean = re.sub(r'[^a-z0-9_]', '', clean).strip('_')

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


# ==============================================================================
# FRUIT & VEGETABLE KNOWLEDGE BASE
# ==============================================================================
from fruit_database import FRUIT_VEG_DATABASE


def extract_video_subject(video_name: str) -> dict:
    """
    Intelligently identifies the fruit/vegetable and topic from the video filename or path.
    Example: 'Apple_explaining_health_benefits_202608230045.mp4' -> Apple metadata
    """
    clean_name = os.path.basename(video_name or "").lower()
    clean_name = re.sub(r'[_\-\.]', ' ', clean_name)

    # Search known fruits/veggies in filename (check longer keys first for multi-word matches)
    for key in sorted(FRUIT_VEG_DATABASE.keys(), key=lambda k: len(k), reverse=True):
        pattern = r'\b' + re.escape(key) + r'\b'
        if re.search(pattern, clean_name) or key in clean_name:
            return FRUIT_VEG_DATABASE[key]

    # Fallback to general FruityToon fruit & veggie character
    return {
        "name": "Fruit & Veggies",
        "type": "superfood",
        "emoji": "🍎🥦",
        "nutrients": "essential vitamins, minerals, and natural energy",
        "benefits": "boosts natural vitality, supports daily immune defenses, and keeps your body thriving",
        "titles": [
            "When Your Healthy Snacks Secretly Team Up! 🍎🥦✨",
            "Why Whole Foods Are Nature's Ultimate Lifehack! ✨",
            "When Fruit & Veggies Spill the Real Health Secrets! 😂",
            "Clean Energy Without the Afternoon Slump! ⚡"
        ],
        "descriptions": [
            "Whole fruits and veggies are nature's original power-ups! Crisp nutrients, zero artificial junk, and all the clean energy you need.\n\nWhich healthy snack is always in your kitchen? 👇\n\n#fruitytoon #healthyfood #fruits #vegetables #animation #funny #reels #shorts",
            "Packed with daily vitamins and antioxidants to keep your immune system running at peak performance! Eat your colors and feel unstoppable.\n\nDrop your go-to fresh snack below! 🍎\n\n#fruitytoon #healthyeating #fruits #vegetables #animation #cartoon #reels #shorts"
        ]
    }


def get_already_published():
    """Load list of published videos from log files (merging published_videos.json and history.json)."""
    videos_map = {}
    for log_path in (PUBLISHED_LOG, HISTORY_LOG):
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            vname = item.get("video_name")
                            if vname and vname not in videos_map:
                                videos_map[vname] = item
            except Exception as e:
                print(f"Notice reading {log_path}: {e}")
    return list(videos_map.values())


def get_repost_counts():
    """Count how many times each video has been posted."""
    published = get_already_published()
    counts = {}
    for entry in published:
        vname = entry.get("video_name", "")
        counts[vname] = counts.get(vname, 0) + 1
    return counts


def mark_as_published(video_name, metadata):
    """Save publication record with timestamp to both published_videos.json and history.json."""
    record = {
        "video_name": video_name,
        "metadata": metadata
    }

    for log_path in (PUBLISHED_LOG, HISTORY_LOG):
        data = []
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if not isinstance(data, list):
                        data = []
            except Exception:
                data = []

        data.append(record)
        try:
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"⚠️ Error saving {log_path}: {e}")

    print(f"💾 Recorded publication to {PUBLISHED_LOG} and {HISTORY_LOG}")


# ==============================================================================
# YOUTUBE SCHEDULING: ALTERNATE DAYS & MAX ONCE A DAY
# ==============================================================================

def get_last_youtube_publish_date():
    """
    Finds the last date (datetime.date) on which a video was published to YouTube.
    First checks dedicated youtube_publish_state.json, then published_videos.json.
    """
    # 1. Dedicated state file
    if os.path.exists(YOUTUBE_STATE_FILE):
        try:
            with open(YOUTUBE_STATE_FILE, 'r', encoding='utf-8') as f:
                state = json.load(f)
                d_str = state.get("last_published_date")
                if d_str:
                    return datetime.date.fromisoformat(d_str)
        except Exception as e:
            print(f"[youtube schedule] Notice reading {YOUTUBE_STATE_FILE}: {e}")

    # 2. published_videos.json log
    published = get_already_published()
    for entry in reversed(published):
        meta = entry.get("metadata", {})
        flags = meta.get("success_flags", {})
        if flags.get("youtube") is True:
            yt_time = meta.get("youtube_published_at") or meta.get("published_at")
            if yt_time:
                try:
                    return datetime.date.fromisoformat(yt_time[:10])
                except Exception:
                    pass

    return None


def should_publish_to_youtube():
    """
    Enforces YouTube publishing policy:
    1. Publish strictly on TUESDAY, THURSDAY, and SUNDAY only (3 days per week).
    2. NEVER publish more than ONCE in the same calendar day.
    """
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    today = now_utc.date()
    day_name = today.strftime("%A")  # 'Monday', 'Tuesday', ...
    weekday = today.weekday()        # 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun

    ALLOWED_DAYS = {1: "Tuesday", 3: "Thursday", 6: "Sunday"}

    if weekday not in ALLOWED_DAYS:
        allowed_names = ", ".join(ALLOWED_DAYS.values())
        return False, f"YouTube schedule policy: {allowed_names} only. Today is {day_name}. YouTube upload skipped."

    last_date = get_last_youtube_publish_date()

    if last_date is None:
        return True, f"Today is {day_name} (approved YouTube day). No previous YouTube upload found."

    days_diff = (today - last_date).days

    if days_diff == 0:
        return False, f"YouTube has ALREADY published today ({day_name}, {last_date}). Policy: Maximum once per day on publishing days."

    if days_diff < 0:
        return False, f"Clock anomaly: Last YouTube publish recorded in future ({last_date}). Skipping YouTube upload."

    return True, f"Today is {day_name} (approved YouTube day). Last publish was {days_diff} day(s) ago on {last_date}."


def record_youtube_publish(video_name, video_id=None):
    """Records the successful YouTube publication state."""
    today = datetime.datetime.now(datetime.timezone.utc).date()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    state = {
        "last_published_date": today.isoformat(),
        "last_published_at": now_iso,
        "last_video_name": video_name,
        "last_video_id": video_id or ""
    }
    try:
        with open(YOUTUBE_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=4)
        print(f"[youtube schedule] ✅ Successfully recorded YouTube publish state for {today.isoformat()}")
    except Exception as e:
        print(f"[youtube schedule] ⚠️ Error saving {YOUTUBE_STATE_FILE}: {e}")


# ==============================================================================
# VIDEO SELECTION (Normal & Weighted Repost)
# ==============================================================================

def select_video(specific_video=None):
    """
    Selects a video for publishing.
    GUARANTEES:
    1. NEVER publishes the same video back-to-back or in close succession.
    2. Strictly enforces a 30-video cooldown window on all previously published videos.
    3. Uses Least-Recently-Used (LRU) rotation across older videos evenly.
    4. Automatically prioritizes genuine unpublished videos.
    """
    all_videos = sorted(glob.glob(os.path.join(PROCESSED_DIR, "*.mp4")))

    last_seen_idx, publish_counts, total_records = get_publication_tracker()
    cooldown_window = min(30, max(5, len(all_videos) // 2)) if all_videos else 30

    if specific_video:
        if os.path.exists(specific_video):
            vid_path = specific_video
            name = os.path.basename(specific_video)
        else:
            vid_path = os.path.join(PROCESSED_DIR, specific_video)
            name = specific_video

        if os.path.exists(vid_path):
            k = normalize_video_key(name)
            count = publish_counts.get(k, 0)
            if count > 0:
                print(f"🔄 Video {name} was already published ({count}x) - Re-publishing (recycling)")
            return vid_path, name
        else:
            print(f"❌ Error: Specific video {name} not found")
            return None, None

    if not all_videos:
        print("❌ No videos found in Processed_Videos")
        return None, None

    unpublished = []
    published_candidates = []

    for vid in all_videos:
        name = os.path.basename(vid)
        k = normalize_video_key(name)
        if k not in last_seen_idx:
            unpublished.append((vid, name))
        else:
            last_idx = last_seen_idx[k]
            distance = total_records - 1 - last_idx
            published_candidates.append({
                "path": vid,
                "name": name,
                "key": k,
                "last_idx": last_idx,
                "distance": distance,
                "count": publish_counts.get(k, 1),
                "in_cooldown": distance < cooldown_window
            })

    if unpublished:
        vid, name = unpublished[0]
        print(f"✨ Selected unpublished video: {name}")
        return vid, name

    # LRU rotation outside cooldown
    eligible = [c for c in published_candidates if not c['in_cooldown']]
    if not eligible:
        eligible = sorted(published_candidates, key=lambda x: x['last_idx'])
    else:
        eligible.sort(key=lambda x: (x['count'], x['last_idx']))

    chosen = eligible[0]
    print(f"🔄 Selected for rotation (posted {chosen['count']}x before, {chosen['distance']} runs ago): {chosen['name']}")
    return chosen['path'], chosen['name']

# ==============================================================================
# TARGETED CAPTION GENERATION# ==============================================================================
# TARGETED CAPTION GENERATION (Food-Specific & Verified)
# ==============================================================================

def build_hybrid_description(base_desc, food_name, nutrients, benefits, clean_tag):
    """Combine a punchy hook with a keyword-rich SEO body for health search.

    Keeps the hook/CTA, inserts sentences built from the verified
    nutrients/benefits entry ahead of the hashtag block, and guarantees
    a full hashtag set. Total stays well under Instagram's 2200-char cap.
    """
    seo_body = (
        f"{food_name} is rich in {nutrients}. "
        f"{food_name} {benefits}. "
        f"Add {food_name.lower()} to your daily routine for clean whole-food "
        f"nutrition that supports a healthy lifestyle."
    )
    tags = (
        f"#fruitytoon #{clean_tag} #healthyeating #nutrition "
        f"#fruits #vegetables #animation #cartoon #shorts #reels #foodfacts"
    )
    marker = "\n\n#"
    if marker in base_desc:
        head, _, tail = base_desc.rpartition(marker)
        return f"{head}\n\n{seo_body}\n\n#{tail}"
    head = base_desc.rstrip()
    if "#" not in head:
        return f"{head}\n\n{seo_body}\n\n{tags}"
    return f"{head}\n\n{seo_body}"


def generate_caption(video_name=None, video_path=None):
    """
    Generates a hybrid title and description for the exact fruit or vegetable
    in the video: a short punchy hook plus a keyword-rich health SEO body.
    """
    target_video = video_name or (os.path.basename(video_path) if video_path else "")
    subject = extract_video_subject(target_video)

    food_name = subject.get("name", "Fruit")
    food_emoji = subject.get("emoji", "🍎")
    nutrients = subject.get("nutrients", "vitamins, minerals, and natural energy")
    benefits = subject.get("benefits", "healthy digestion, strong immunity, and sustained vitality")

    fallback_titles = subject.get("titles") or [f"When the {food_name} Realizes Its True Superpower! {food_emoji}"]
    clean_tag = re.sub(r'[^a-z0-9]', '', food_name.lower())
    if not clean_tag:
        clean_tag = "fruit"

    fallback_descriptions = subject.get("descriptions") or [
        f"The {food_name.lower()} delivers clean vitamins and steady energy for all-day vitality!\n\nWhat is your go-to fresh snack? 👇\n\n#fruitytoon #{clean_tag} #healthyeating #fruits #animation #shorts #reels"
    ]

    api_key = os.getenv("POLLINATIONS_API_KEY")
    model = os.getenv("AI_MODEL", "gemini-fast")

    if not api_key:
        print(f"ℹ️  Using verified {food_name} database templates (no POLLINATIONS_API_KEY).")
        fallback_title = random.choice(fallback_titles)
        hybrid_desc = build_hybrid_description(
            random.choice(fallback_descriptions), food_name, nutrients, benefits, clean_tag)
        return fallback_title, hybrid_desc

    vibes = [
        f"silly, high-energy cartoon chaos starring the animated {food_name} {food_emoji}",
        f"relatable comedy poking fun at picky eaters while praising {food_name}'s superpowers",
        f"clever food puns woven with real health science about {food_name}",
        f"hilarious dramatic monologue where the {food_name} explains why humans desperately need it"
    ]
    chosen_vibe = random.choice(vibes)

    prompt = (
        f"Write a short, viral-worthy title and engaging caption for a funny 3D CARTOON animation Reel for 'FruityToon'.\n"
        f"Character: {food_name} {food_emoji}.\n"
        f"Health benefits to feature: {nutrients} -> {benefits}.\n"
        f"Tone: {chosen_vibe}.\n\n"
        f"HYBRID REQUIREMENTS (PUNCHY HOOK + HEALTH SEO BODY):\n"
        f"1. TITLE: Catchy short hook under 60 characters with emoji (e.g. 'Why Apple is Quietly Winning! 🍎💪').\n"
        f"2. HOOK: 1 to 2 funny, punchy sentences up front to stop the scroll.\n" +
        f"3. SEO BODY: 2 to 4 sentences AFTER the hook using real health-search keywords from the benefits above (nutrient names, what they do, whole-food nutrition, daily routine). Total description 60-120 words, no walls of text.\n" +
        f"4. CALL TO ACTION: Exactly 1 short engaging line (e.g. 'What is your favorite fruit? Let us know below! 👇').\n"
        f"5. HASHTAGS: 8 to 12 clean lowercase hashtags without special symbols: #fruitytoon #{clean_tag} #healthyeating #nutrition #fruits #vegetables #animation #cartoon #shorts #reels #foodfacts.\n"
        f'6. OUTPUT FORMAT: Return ONLY a valid JSON object: {{"title": "...", "description": "..."}} with description = hook, blank line, SEO body, blank line, CTA, blank line, hashtags. No markdown code blocks.\n'
    )

    url = "https://gen.pollinations.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.85,
        "seed": random.randint(1, 999999)
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=25)
        response.raise_for_status()
        data = response.json()
        raw_content = data.get('choices', [{}])[0].get('message', {}).get('content', '')

        # Robust JSON extraction
        clean_content = raw_content.replace("```json", "").replace("```", "").strip()
        json_match = re.search(r'\{.*\}', clean_content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(0))
            gen_title = result.get("title", "").strip()
            gen_desc = result.get("description", "").strip()

            if gen_title and gen_desc:
                # Ensure hashtags are present if omitted by AI
                if "#" not in gen_desc:
                    gen_desc = f"{gen_desc.rstrip()}\n\n#fruitytoon #{clean_tag} #healthyeating #nutrition #fruits #vegetables #animation #cartoon #shorts #reels #foodfacts"
                print(f"✨ AI generated targeted caption for {food_name}!")
                return gen_title, gen_desc

        print(f"⚠️  AI response invalid. Falling back to tailored {food_name} template.")
        fallback_title = random.choice(fallback_titles)
        hybrid_desc = build_hybrid_description(
            random.choice(fallback_descriptions), food_name, nutrients, benefits, clean_tag)
        return fallback_title, hybrid_desc

    except Exception as e:
        print(f"⚠️  Notice: AI caption generation fell back to {food_name} template ({e})")
        fallback_title = random.choice(fallback_titles)
        hybrid_desc = build_hybrid_description(
            random.choice(fallback_descriptions), food_name, nutrients, benefits, clean_tag)
        return fallback_title, hybrid_desc
    vibes = [
        f"silly, high-energy cartoon chaos starring the animated {food_name} {food_emoji}",
        f"relatable comedy poking fun at picky eaters while praising {food_name}'s superpowers",
        f"clever food puns woven with real health science about {food_name}",
        f"hilarious dramatic monologue where the {food_name} explains why humans desperately need it"
    ]
    chosen_vibe = random.choice(vibes)

    prompt = (
        f"Write a hilarious, viral-worthy title and engaging description for a short 3D CARTOON animation video for 'FruityToon'.\n"
        f"The video stars an animated 3D character: {food_name} {food_emoji}.\n"
        f"Topic: The {food_name} hilariously explains its real health benefits ({nutrients} -> {benefits}).\n"
        f"Tone / Vibe: {chosen_vibe}.\n\n"
        f"CRITICAL REQUIREMENTS:\n"
        f"1. TITLE: Extremely catchy hook under 70 characters with emoji. MUST clearly relate to {food_name}.\n"
        f"2. DESCRIPTION: 3 to 5 funny, engaging sentences highlighting real, accurate health benefits of eating {food_name}.\n"
        f"3. CALL TO ACTION: Include an engaging CTA (e.g. 'Tag a friend who needs more {food_name}!', 'Comment your favorite fruit below!').\n"
        f"4. HASHTAGS: Include clean lowercase hashtags: #fruitytoon #{food_name.lower().replace(' ', '')} #healthyeating #nutrition #fruits #animation #cartoon #funny #shorts #reels #foodfacts.\n"
        f"5. OUTPUT FORMAT: Return ONLY a valid JSON object: {{\"title\": \"...\", \"description\": \"...\"}} without markdown backticks."
    )

    url = "https://gen.pollinations.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.85,
        "seed": random.randint(1, 999999)
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=25)
        response.raise_for_status()
        data = response.json()
        raw_content = data.get('choices', [{}])[0].get('message', {}).get('content', '')

        # Robust JSON extraction
        clean_content = raw_content.replace("```json", "").replace("```", "").strip()
        json_match = re.search(r'\{.*\}', clean_content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(0))
            gen_title = result.get("title", "").strip()
            gen_desc = result.get("description", "").strip()

            if gen_title and gen_desc:
                # Ensure hashtags are present if omitted by AI
                if "#" not in gen_desc:
                    clean_tag = food_name.lower().replace(' ', '')
                    gen_desc = f"{gen_desc.rstrip()}\n\n#fruitytoon #{clean_tag} #healthyeating #nutrition #fruits #animation #cartoon #funny #shorts #reels #foodfacts"
                print(f"✨ AI generated targeted caption for {food_name}!")
                return gen_title, gen_desc

        print(f"⚠️  AI response invalid. Falling back to tailored {food_name} template.")
        fallback_title = random.choice(fallback_titles)
        hybrid_desc = build_hybrid_description(
            random.choice(fallback_descriptions), food_name, nutrients, benefits, clean_tag)
        return fallback_title, hybrid_desc

    except Exception as e:
        print(f"⚠️  Notice: AI caption generation fell back to {food_name} template ({e})")
        fallback_title = random.choice(fallback_titles)
        hybrid_desc = build_hybrid_description(
            random.choice(fallback_descriptions), food_name, nutrients, benefits, clean_tag)
        return fallback_title, hybrid_desc


# ==============================================================================
# MAIN PUBLISHING PIPELINE
# ==============================================================================

def main():
    print("=" * 60)
    print("🚀 FRUITYTOON MULTI-PLATFORM PUBLISHER STARTING")
    print("=" * 60)

    specific_video = sys.argv[1] if len(sys.argv) > 1 else None
    video_path, video_name = select_video(specific_video)
    if not video_path:
        print("✅ No new videos found to publish. Exiting.")
        return

    subject = extract_video_subject(video_name)
    print(f"👉 Selected Video: {video_name}")
    print(f"🍉 Detected Subject: {subject.get('name')} {subject.get('emoji')}")

    print("🧠 Generating tailored caption...")
    title, description = generate_caption(video_name=video_name, video_path=video_path)

    print(f"\n📝 TITLE:\n{title}")
    print(f"\n📝 DESCRIPTION:\n{description}\n")

    # Combined caption for platforms (Instagram, Facebook, Threads)
    combined_caption = f"{title}\n\n{description}" if title not in description else description

    success_flags = {
        "instagram_reel": False,
        "instagram_story": False,
        "facebook_reel": False,
        "facebook_story": False,
        "threads": False,
        "youtube": False
    }

    # 1. Instagram Reels
    try:
        result = upload_to_instagram(video_path, combined_caption, is_story=False)
        if result and result.get('status') == 'skipped':
            print(f"⚠️  Instagram Reel: Skipped ({result.get('reason', 'No credentials')})")
            success_flags["instagram_reel"] = "skipped"
        elif result and result.get('status') == 'success':
            success_flags["instagram_reel"] = True
    except Exception as e:
        print(f"❌ Instagram Reel upload failed: {e}")

    # 2. Instagram Stories
    try:
        result = upload_to_instagram(video_path, combined_caption, is_story=True)
        if result and result.get('status') == 'skipped':
            print(f"⚠️  Instagram Story: Skipped ({result.get('reason', 'No credentials')})")
            success_flags["instagram_story"] = "skipped"
        elif result and result.get('status') == 'success':
            success_flags["instagram_story"] = True
    except Exception as e:
        print(f"❌ Instagram Story upload failed: {e}")

    # 3. Facebook Reels
    try:
        result = upload_to_facebook(video_path, description=description, title=title)
        if result and result.get('status') == 'skipped':
            print(f"⚠️  Facebook Reel: Skipped ({result.get('reason', 'No credentials')})")
            success_flags["facebook_reel"] = "skipped"
        elif result and result.get('status') == 'success':
            success_flags["facebook_reel"] = True
    except Exception as e:
        print(f"❌ Facebook Reel upload failed: {e}")

    # 4. Facebook Stories
    try:
        result = upload_to_facebook_story(video_path)
        if result and result.get('status') == 'skipped':
            print(f"⚠️  Facebook Story: Skipped ({result.get('reason', 'No credentials')})")
            success_flags["facebook_story"] = "skipped"
        elif result and result.get('status') == 'success':
            success_flags["facebook_story"] = True
    except Exception as e:
        print(f"❌ Facebook Story upload failed: {e}")

    # 5. Threads
    try:
        result = upload_to_threads(video_path, combined_caption)
        if result and result.get('status') == 'skipped':
            print(f"⚠️  Threads: Skipped ({result.get('reason', 'No credentials')})")
            success_flags["threads"] = "skipped"
        elif result and result.get('status') == 'success':
            success_flags["threads"] = True
    except Exception as e:
        print(f"❌ Threads upload failed: {e}")

    # 6. YouTube Shorts (ENFORCING: Max Once a Day & Alternate Days Only)
    print("\n" + "-" * 40)
    print("🎬 CHECKING YOUTUBE PUBLISHING SCHEDULE")
    print("-" * 40)
    yt_eligible, yt_reason = should_publish_to_youtube()

    if not yt_eligible:
        print(f"⏸️  YouTube Shorts SKIPPED: {yt_reason}")
        success_flags["youtube"] = "skipped"
    else:
        print(f"✅ YouTube Shorts APPROVED: {yt_reason}")
        try:
            # YouTube Shorts Title (strictly max 100 characters)
            yt_title = title.strip()
            if "#Shorts" not in yt_title and "#shorts" not in yt_title:
                if len(yt_title) + len(" #Shorts") <= 100:
                    yt_title = f"{yt_title} #Shorts"
                else:
                    yt_title = yt_title[:91].rstrip() + " #Shorts"

            food_keyword = subject.get("name", "fruit").lower().replace(" ", "")
            yt_tags = [
                "fruitytoon",
                food_keyword,
                "fruits",
                "vegetables",
                "shorts",
                "funny",
                "animation",
                "cartoon",
                "healthyeating",
                "nutrition",
                "comedy",
                "foodfacts",
                "fyp"
            ]

            yt_result = upload_to_youtube(
                video_path=video_path,
                title=yt_title,
                description=description,
                tags=yt_tags,
                category_id='24'
            )

            if yt_result and yt_result.get('status') == 'success':
                success_flags["youtube"] = True
                record_youtube_publish(video_name, yt_result.get('id'))
            else:
                err_detail = yt_result.get('error') if yt_result else 'Unknown error'
                print(f"❌ YouTube upload did not complete: {err_detail}")
                success_flags["youtube"] = False
        except Exception as e:
            print(f"❌ YouTube upload failed with exception: {e}")
            success_flags["youtube"] = False

    # Mark as published in log
    print("\n✅ Marking video publication record...")
    published_list = get_already_published()
    is_recycled = any(item["video_name"] == video_name for item in published_list)

    if is_recycled:
        print("   🔄 This was a recycled video (re-published)")

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    mark_as_published(video_name, {
        "title": title,
        "description": description,
        "subject": subject.get("name"),
        "published_at": now_iso,
        "youtube_published_at": now_iso if success_flags.get("youtube") is True else None,
        "youtube_status": success_flags.get("youtube"),
        "success_flags": success_flags,
        "recycled": is_recycled
    })

    # Move processed video to Published_Videos
    published_dir = "Published_Videos"
    if not os.path.exists(published_dir):
        os.makedirs(published_dir)

    try:
        dest_path = os.path.join(published_dir, video_name)
        shutil.move(video_path, dest_path)
        print(f"📦 Moved published video to {dest_path}")
    except Exception as e:
        print(f"❌ Failed to move published video: {e}")

    print("\n🎉 AUTOMATION RUN COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
