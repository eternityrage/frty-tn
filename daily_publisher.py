import os
import json
import glob
import random
import requests
import shutil
import sys
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
from pathlib import Path
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
    # Still want to proceed or stop?
    pass

PROCESSED_DIR = "Processed_Videos"
PUBLISHED_LOG = "published_videos.json"

def get_already_published():
    if os.path.exists(PUBLISHED_LOG):
        with open(PUBLISHED_LOG, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []


def get_repost_counts():
    """Count how many times each video has been posted."""
    published = get_already_published()
    counts = {}
    for entry in published:
        vname = entry.get("video_name", "")
        counts[vname] = counts.get(vname, 0) + 1
    return counts

def mark_as_published(video_name, metadata):
    published = get_already_published()
    published.append({
        "video_name": video_name,
        "metadata": metadata
    })
    with open(PUBLISHED_LOG, 'w', encoding='utf-8') as f:
        json.dump(published, f, indent=4)

def select_video(specific_video=None):
    published = [item["video_name"] for item in get_already_published()]
    all_videos = sorted(glob.glob(os.path.join(PROCESSED_DIR, "*.mp4")))

    if specific_video:
        # specific_video might be a full path or just a filename
        if os.path.exists(specific_video):
            # It's a full path
            vid_path = specific_video
            name = os.path.basename(specific_video)
        else:
            # It's just a filename, join with PROCESSED_DIR
            vid_path = os.path.join(PROCESSED_DIR, specific_video)
            name = specific_video

        if os.path.exists(vid_path):
            if name in published:
                post_count = sum(1 for p in published if p == name)
                print(f"🔄 Video {name} was already published ({post_count}x) - Re-publishing (recycling)")
            return vid_path, name
        else:
            print(f"❌ Error: Specific video {name} not found")
            return None, None

    # Find unpublished videos first
    unpublished = [(vid, os.path.basename(vid)) for vid in all_videos if os.path.basename(vid) not in published]

    if unpublished:
        vid, name = unpublished[0]
        return vid, name

    # All videos published - use weighted random selection (less posted = more likely)
    if all_videos:
        repost_counts = get_repost_counts()
        weights = []
        for vid in all_videos:
            name = os.path.basename(vid)
            count = repost_counts.get(name, 0)
            weight = max(1, 1000 // (3 ** min(count, 6)))
            weights.append(weight)

        selected_vid = random.choices(all_videos, weights=weights, k=1)[0]
        name = os.path.basename(selected_vid)
        post_count = repost_counts.get(name, 0)
        print(f"🎲 All videos published. Weighted random reuse (posted {post_count}x): {name}")
        return selected_vid, name

    return None, None

def generate_caption():
    import random
    import time

    api_key = os.getenv("POLLINATIONS_API_KEY")
    model = os.getenv("AI_MODEL", "openai")

    fallback_titles = [
        "When the Carrot Finds Out What It Does for Your Eyes 👀🥕",
        "The Tomato's Existential Crisis: Fruit or Vegetable? 🍅",
        "Broccoli Tries to Convince You It's Actually Delicious 🥦",
        "The Banana's Guide to Instant Happiness 🍌",
        "When the Apple Realizes It Keeps the Doctor Away 🍎",
        "The Spinach Explains Why Popeye Was Right 💪🌿",
        "The Strawberry's Sweet Talk About Heart Health 🍓",
        "When the Orange Shows Off Its Vitamin C Power 🍊",
        "The Avocado's Smooth Talk on Good Fats 🥑",
        "The Blueberry Brags About Being a Brain Food 🫐",
        "The Watermelon's Hydration Ted Talk 🍉",
        "The Garlic Tries to Fix Your Immunity (and Your Love Life) 🧄",
        "The Cucumber's Chill Guide to Staying Cool 🥒",
        "The Beet Explains Its Blood-Pressure Magic 🔴",
        "When the Pineapple Refuses to Be Just a Pizza Topping 🍍",
    ]

    fallback_descriptions = [
        "Turns out the carrot wasn't bluffing — those beta-carotenes are basically eye vitamins in disguise. Eat your veggies and quietly outsmart your optometrist. Tag the friend who still thinks carrots are just orange sticks! 😂🥕 #fruitytoon #funny #healthyeating #nutrition #animation #cartoon #vegetables #fruits #lol #shorts #wellness #comedy #foodfacts #drawing",
        "The tomato has been in a lifelong identity crisis, but here's the tea: it's packed with lycopene that's great for your heart. Tomato, tomato — call it whatever you want, just eat it. Send this to the friend who picks the fries over the salad! 🍅 #fruitytoon #funny #healthyeating #nutrition #animation #cartoon #vegetables #fruits #lol #shorts #wellness #comedy #foodfacts #drawing",
        "Broccoli knows it gets a bad rap, but it's out here loaded with vitamin C and fiber doing the most for your immune system. Respect the little trees. Comment your most hated veggie — we'll defend it! 🥦 #fruitytoon #funny #healthyeating #nutrition #animation #cartoon #vegetables #fruits #lol #shorts #wellness #comedy #foodfacts #drawing",
        "The banana isn't just a snack, it's a mood upgrade — potassium for your muscles and a hit of happy-making serotonin fuel. Peel into a better day. Share this with someone who needs a smile! 🍌 #fruitytoon #funny #healthyeating #nutrition #animation #cartoon #vegetables #fruits #lol #shorts #wellness #comedy #foodfacts #drawing",
        "An apple a day isn't just a cute saying — the fiber and antioxidants are genuinely doing your gut and heart a favor. The doctor can wait, the apple cannot. Follow FruityToon for daily funny food facts! 🍎 #fruitytoon #funny #healthyeating #nutrition #animation #cartoon #vegetables #fruits #lol #shorts #wellness #comedy #foodfacts #drawing",
        "Popeye was onto something — spinach is stacked with iron and vitamins that keep your energy up without the crash. Eat the greens, skip the drama. Tag your picky-eater friend! 💪🌿 #fruitytoon #funny #healthyeating #nutrition #animation #cartoon #cute #vegetables #fruits #lol #shorts #wellness #comedy #foodfacts #drawing",
        "Strawberries are basically heart-shaped vitamins — full of antioxidants that love your cardiovascular system. Cute AND good for you, rare combo. Drop a 🍓 if berries are your favorite! #fruitytoon #funny #healthyeating #nutrition #animation #cartoon #vegetables #fruits #lol #shorts #wellness #comedy #foodfacts #drawing",
        "The orange is out here flexing its vitamin C like a superhero cape — immune support in every juicy segment. Squeeze the day. Share with someone who's been sniffling! 🍊 #fruitytoon #funny #healthyeating #nutrition #animation #cartoon #vegetables #fruits #lol #shorts #wellness #comedy #foodfacts #drawing",
    ]

    if not api_key:
        chosen_title = random.choice(fallback_titles)
        chosen_desc = random.choice(fallback_descriptions)
        print("Warning: POLLINATIONS_API_KEY not found. Using fallback captions.")
        return chosen_title, chosen_desc

    vibes = [
        "silly but secretly educational — make people laugh while dropping a real food fact",
        "wholesome and playful — cute cartoon chaos with a healthy twist",
        "pun-filled and goofy — fruit and veggie wordplay that actually teaches something",
        "surprisingly informative — funny hook, then a genuine benefit of the food",
        "relatable and cheeky — poke fun at picky eaters while promoting healthy snacks",
        "bright and energetic — upbeat cartoon energy with a nutrition nugget",
        "deadpan and absurd — serious tone, ridiculous vegetable situation",
    ]
    chosen_vibe = random.choice(vibes)

    prompt = (
        f"Write a completely unique, hilarious, and captivating title and description for a short funny 3D CARTOON animation video "
        f"for the social media page 'FruityToon'. "
        f"The page posts funny 3D cartoon animations of fruits and vegetables talking about the real benefits of eating them — "
        f"healthy and educational, but delivered in a laugh-out-loud, entertaining way. "
        f"Make the vibe {chosen_vibe}. "
        f"The description should be FUNNY (4-6 sentences minimum) yet interesting — weave in a genuine, accurate benefit "
        f"of eating fruits or vegetables (vitamins, energy, heart health, digestion, immunity, etc.) so viewers actually learn something. "
        f"Include engagement calls-to-action such as: "
        f"- Tag a friend who needs more veggies in their life! 🥕 "
        f"- Comment your favorite fruit or veggie below! "
        f"- Share this with someone who hates eating healthy! "
        f"- Follow FruityToon for daily funny food facts! "
        f"Include relevant hashtags in ALL LOWERCASE such as #fruitytoon #funny #healthyeating #nutrition #animation #cartoon #vegetables #fruits #lol #shorts #wellness #comedy #foodfacts #drawing. "
        f"Return ONLY a valid JSON object in this format: {{\"title\": \"<title>\", \"description\": \"<description>\"}} "
        f"Do not include any other text or markdown block backticks."
    )

    url = "https://gen.pollinations.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.9,
        "seed": random.randint(1, 999999)
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        content = data.get('choices', [{}])[0].get('message', {}).get('content', '')

        content = content.replace("```json", "").replace("```", "").strip()
        result = json.loads(content)

        chosen_title = random.choice(fallback_titles)
        chosen_desc = random.choice(fallback_descriptions)
        return result.get("title", chosen_title), result.get("description", chosen_desc)
    except Exception as e:
        print(f"Error generating caption: {e}")
        return random.choice(fallback_titles), random.choice(fallback_descriptions)

def main():
    print("=" * 60)
    print("🚀 DAILY AUTOMATION STARTING")
    print("=" * 60)
    
    specific_video = sys.argv[1] if len(sys.argv) > 1 else None
    video_path, video_name = select_video(specific_video)
    if not video_path:
        print("✅ No new videos found to publish. Exiting.")
        return
        
    print(f"👉 Selected Video: {video_name}")
    print("🧠 Generating caption via Pollination AI...")
    title, description = generate_caption()
    
    print(f"📝 Title: {title}")
    print(f"📝 Description:\n{description}")
    
    # Combined caption for platforms that use a single text field
    combined_caption = f"{title}\n\n{description}"
    
    success_flags = {
        "instagram_reel": False,
        "instagram_story": False,
        "facebook_reel": False,
        "facebook_story": False,
        "threads": False,
        "youtube": False
    }
    
    # Instagram Reels
    try:
        result = upload_to_instagram(video_path, combined_caption, is_story=False)
        if result and result.get('status') == 'skipped':
            print(f"⚠️  Instagram Reel: Skipped ({result.get('reason', 'No credentials')})")
        else:
            success_flags["instagram_reel"] = True
    except Exception as e:
        print(f"❌ Instagram Reel upload failed: {e}")
        
    # Instagram Stories
    try:
        result = upload_to_instagram(video_path, combined_caption, is_story=True)
        if result and result.get('status') == 'skipped':
            print(f"⚠️  Instagram Story: Skipped ({result.get('reason', 'No credentials')})")
        else:
            success_flags["instagram_story"] = True
    except Exception as e:
        print(f"❌ Instagram Story upload failed: {e}")
        
    # Facebook Reels
    try:
        result = upload_to_facebook(video_path, description, title=title)
        if result and result.get('status') == 'skipped':
            print(f"⚠️  Facebook Reel: Skipped ({result.get('reason', 'No credentials')})")
        else:
            success_flags["facebook_reel"] = True
    except Exception as e:
        print(f"❌ Facebook Reel upload failed: {e}")
        
    # Facebook Stories
    try:
        result = upload_to_facebook_story(video_path)
        if result and result.get('status') == 'skipped':
            print(f"⚠️  Facebook Story: Skipped ({result.get('reason', 'No credentials')})")
        else:
            success_flags["facebook_story"] = True
    except Exception as e:
        print(f"❌ Facebook Story upload failed: {e}")
        
    # Threads
    try:
        result = upload_to_threads(video_path, combined_caption)
        if result and result.get('status') == 'skipped':
            print(f"⚠️  Threads: Skipped ({result.get('reason', 'No credentials')})")
        else:
            success_flags["threads"] = True
    except Exception as e:
        print(f"❌ Threads upload failed: {e}")
        
    # YouTube Shorts
    try:
        upload_to_youtube(video_path, title, description, tags=["fruitytoon", "funny", "healthyeating", "nutrition", "animation", "cartoon", "vegetables", "fruits", "shorts", "wellness", "comedy", "foodfacts", "drawing", "fyp"])
        success_flags["youtube"] = True
    except Exception as e:
        print(f"❌ YouTube upload failed: {e}")
        
    # Record as published regardless of partial success,
    # to avoid repeating the same video. Alternatively, only record if fully successful.
    print("\n✅ Marking video as published.")
    
    # Check if this is a recycled video (already in published_videos.json)
    published_list = get_already_published()
    is_recycled = any(item["video_name"] == video_name for item in published_list)
    
    if is_recycled:
        print(f"   🔄 This is a recycled video (re-publishing)")
    
    mark_as_published(video_name, {
        "title": title,
        "description": description,
        "success_flags": success_flags,
        "recycled": is_recycled
    })
    
    # Move the published video to Published_Videos folder
    published_dir = "Published_Videos"
    if not os.path.exists(published_dir):
        os.makedirs(published_dir)
        
    try:
        dest_path = os.path.join(published_dir, video_name)
        shutil.move(video_path, dest_path)
        print(f"📦 Moved published video to {dest_path}")
    except Exception as e:
        print(f"❌ Failed to move published video: {e}")
    
    print("🎉 DAILY AUTOMATION COMPLETE")

if __name__ == "__main__":
    main()
