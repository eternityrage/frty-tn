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

PROCESSED_DIR = "Processed_Videos"
PUBLISHED_LOG = "published_videos.json"
YOUTUBE_STATE_FILE = "youtube_publish_state.json"


# ==============================================================================
# FRUIT & VEGETABLE KNOWLEDGE BASE (Guarantees 100% matched titles & descriptions)
# ==============================================================================

FRUIT_VEG_DATABASE = {
    "apple": {
        "name": "Apple",
        "type": "fruit",
        "emoji": "🍎",
        "nutrients": "quercetin, vitamin C, dietary pectin fiber, and polyphenols",
        "benefits": "supports cardiovascular wellness, optimizes gut microbiome health, and stabilizes daily energy levels",
        "titles": [
            "When the Apple Realizes It Actually Keeps the Doctor Away! 🍎🩺",
            "The Apple's Guide to Peak Daily Energy! 🍎✨",
            "Why the Apple is Quietly Winning at Life 🍎💪",
            "The Apple's Secret Power Doctors Don't Tell You! 🍎",
            "When You Crunch into Natural Superhero Fuel! 🍎🔥"
        ],
        "descriptions": [
            "Turns out an apple a day isn't just an old saying — the soluble pectin fiber and quercetin antioxidants genuinely give your heart and gut VIP treatment! Eat the crunch, skip the 3 PM sugar crash, and give your body clean natural fuel.\n\n👉 Tag a friend who needs more fruit in their life! 🍏\n💬 What's your go-to apple: Crisp Red or Granny Smith? Tell us below!\n\n#fruitytoon #apple #healthyeating #nutrition #fruits #animation #cartoon #funny #shorts #reels #wellness #foodfacts",
            "The apple is out here doing heavy lifting for your digestion and heart health while looking effortlessly delicious. High fiber, zero artificial nonsense, and all the crisp satisfaction you could ask for.\n\n👉 Share this with someone who forgets to eat their fruit!\n💬 Comment 🍎 if an apple is in your grocery cart every week!\n\n#fruitytoon #apple #healthyeating #nutrition #fruits #animation #cartoon #funny #shorts #reels #wellness #foodfacts"
        ]
    },
    "banana": {
        "name": "Banana",
        "type": "fruit",
        "emoji": "🍌",
        "nutrients": "potassium, vitamin B6, natural electrolytes, and prebiotic fiber",
        "benefits": "prevents painful muscle cramps, fuels brain function, and naturally boosts serotonin for good moods",
        "titles": [
            "The Banana's Secret Guide to Instant Happiness! 🍌⚡",
            "When the Banana Realizes It's 100% Pure Energy! 🍌💥",
            "Why the Banana is the Ultimate Pre-Workout Hero 🍌💪",
            "The Banana's Hilarious Truth About Muscle Cramps 🍌😂",
            "When You Need an Emergency Serotonin Boost! 🍌💛"
        ],
        "descriptions": [
            "The banana isn't just the easiest snack to peel — it's loaded with potassium and vitamin B6 to power your muscles and give your brain that natural feel-good serotonin boost! Next time you need instant stamina, grab the yellow superhero.\n\n👉 Tag someone who always gets hangry! 🍌\n💬 Do you prefer bananas slightly green or perfectly spotted? Let us know below!\n\n#fruitytoon #banana #healthyeating #nutrition #fruits #animation #cartoon #funny #shorts #reels #wellness #foodfacts",
            "Potassium, electrolytes, and instant smiles: the banana is practically nature's rechargeable battery pack! Keep your muscles relaxed, your digestion happy, and your mood high.\n\n👉 Share this with your favorite workout buddy!\n💬 Drop a 🍌 below if you love bananas!\n\n#fruitytoon #banana #healthyeating #nutrition #fruits #animation #cartoon #funny #shorts #reels #wellness #foodfacts"
        ]
    },
    "carrot": {
        "name": "Carrot",
        "type": "vegetable",
        "emoji": "🥕",
        "nutrients": "beta-carotene, vitamin A, lutein, and prebiotic fiber",
        "benefits": "protects eyesight, supports glowing skin, boosts immune resilience, and aids digestion",
        "titles": [
            "When the Carrot Finds Out What It Does for Your Eyes! 🥕👀",
            "The Carrot's Secret Plan to Outsmart Your Optometrist 🥕✨",
            "Why the Crunchy Carrot Refuses to Be Ignored! 🥕🔥",
            "The Carrot Explaining Its Visionary Superpowers! 🥕👓"
        ],
        "descriptions": [
            "Turns out the carrot wasn't bluffing — those beta-carotenes convert directly into vitamin A to keep your vision sharp and your immune defenses rock solid. Eat your crunchy veggies and quietly outsmart eye strain.\n\n👉 Tag a friend who stares at screens all day! 🥕\n💬 Raw carrots with dip or roasted? Drop your favorite way to eat them below!\n\n#fruitytoon #carrot #vegetables #healthyeating #nutrition #animation #cartoon #funny #shorts #reels #wellness #foodfacts",
            "Carrots are loaded with lutein and antioxidant carotenoids that love your eyes and give your skin a natural healthy glow. Crunch away the afternoon stress with zero guilt!\n\n👉 Share this with someone who needs more veggies!\n💬 Comment your favorite crunchy veggie below!\n\n#fruitytoon #carrot #vegetables #healthyeating #nutrition #animation #cartoon #funny #shorts #reels #wellness #foodfacts"
        ]
    },
    "tomato": {
        "name": "Tomato",
        "type": "fruit",
        "emoji": "🍅",
        "nutrients": "lycopene, vitamin C, potassium, and folate",
        "benefits": "protects cardiovascular health, shields cells against oxidative stress, and promotes healthy skin",
        "titles": [
            "The Tomato's Existential Crisis: Fruit or Vegetable? 🍅🤔",
            "When the Tomato Drops the Real Truth on Heart Health! 🍅❤️",
            "Why the Juicy Tomato is Actually a Superhero 🍅💥",
            "The Tomato's Fiery Rant on Why You Need Lycopene! 🍅🔥"
        ],
        "descriptions": [
            "The tomato has been in a lifelong identity crisis, but here's the science: it's overflowing with lycopene, an antioxidant that loves your heart and shields your cells. Fruit or veggie — call it whatever you want, just get it on your plate!\n\n👉 Send this to the friend who always picks fries over salad! 🍅\n💬 Is a tomato a fruit or a vegetable in your house? Debate below!\n\n#fruitytoon #tomato #fruits #vegetables #healthyeating #nutrition #animation #cartoon #funny #shorts #reels #wellness #foodfacts",
            "Lycopene in tomatoes actually gets stronger when cooked, making sauces, soups, and slices a total heart-health win. High in vitamin C and unbeatable flavor!\n\n👉 Tag someone who puts tomato on everything!\n💬 Drop a 🍅 if you love fresh tomatoes!\n\n#fruitytoon #tomato #fruits #healthyeating #nutrition #animation #cartoon #funny #shorts #reels #wellness #foodfacts"
        ]
    },
    "broccoli": {
        "name": "Broccoli",
        "type": "vegetable",
        "emoji": "🥦",
        "nutrients": "sulforaphane, vitamin C, vitamin K, calcium, and dietary fiber",
        "benefits": "defends cellular health, strengthens bones, supports liver detox pathways, and aids gut health",
        "titles": [
            "Broccoli Tries to Convince You It's Actually Delicious 🥦✨",
            "When the Little Tree Reveals Its True Superpowers! 🥦💪",
            "The Broccoli's Epic Defense Against Picky Eaters 🥦😂",
            "Why Broccoli is the Ultimate Cellular Bodyguard 🥦🛡️"
        ],
        "descriptions": [
            "Broccoli knows it gets a bad rap, but it's out here packed with sulforaphane, calcium, and more vitamin C than an orange! Respect the little green trees — they're your body's personal cellular bodyguards.\n\n👉 Comment your most hated veggie — we'll defend it! 🥦\n💬 Steamed, roasted with garlic, or raw with ranch? How do you eat your broccoli?\n\n#fruitytoon #broccoli #vegetables #healthyeating #nutrition #animation #cartoon #funny #shorts #reels #wellness #foodfacts",
            "Don't sleep on the little green trees! Broccoli is loaded with fiber to keep your digestion humming and antioxidants that support long-term wellness.\n\n👉 Tag a picky eater who needs to see this!\n💬 Leave a 🥦 if you actually enjoy broccoli!\n\n#fruitytoon #broccoli #vegetables #healthyeating #nutrition #animation #cartoon #funny #shorts #reels #wellness #foodfacts"
        ]
    },
    "strawberry": {
        "name": "Strawberry",
        "type": "fruit",
        "emoji": "🍓",
        "nutrients": "vitamin C, manganese, ellagic acid, and anthocyanins",
        "benefits": "supports cardiovascular wellness, boosts glowing skin, and helps control blood sugar spikes",
        "titles": [
            "The Strawberry's Sweet Talk About Heart Health! 🍓❤️",
            "When the Strawberry Proves It's a Heart-Shaped Vitamin! 🍓✨",
            "Why Strawberries Are Nature's Tastiest Miracle 🍓😍",
            "The Strawberry's Secret to Glowing Skin and Good Vibes 🍓💖"
        ],
        "descriptions": [
            "Strawberries are literally heart-shaped vitamins — loaded with anthocyanins, polyphenols, and vitamin C that keep your cardiovascular system running smooth. Sweet, juicy, and ridiculously good for you!\n\n👉 Drop a 🍓 in the comments if berries are your favorite snack!\n💬 What's better: strawberries or blueberries? Pick a side!\n\n#fruitytoon #strawberry #fruits #healthyeating #nutrition #animation #cartoon #funny #shorts #reels #wellness #foodfacts",
            "Sweet flavor with low glycemic impact: strawberries give you all the dessert vibes with none of the refined sugar crash. Packed with skin-loving vitamin C and natural goodness.\n\n👉 Tag someone who always orders strawberry everything!\n💬 Comment your favorite berry below!\n\n#fruitytoon #strawberry #fruits #healthyeating #nutrition #animation #cartoon #funny #shorts #reels #wellness #foodfacts"
        ]
    },
    "orange": {
        "name": "Orange",
        "type": "fruit",
        "emoji": "🍊",
        "nutrients": "vitamin C, hesperidin bioflavonoids, thiamine, and potassium",
        "benefits": "fuels white blood cell immunity, boosts collagen synthesis for healthy skin, and hydrates deeply",
        "titles": [
            "When the Orange Shows Off Its Vitamin C Superhero Cape! 🍊⚡",
            "The Orange's Juicy Guide to Bulletproof Immunity 🍊🛡️",
            "Why the Orange Refuses to Let You Catch a Cold! 🍊💪",
            "The Orange's Zesty Wake-Up Call for Tired Humans! 🍊☀️"
        ],
        "descriptions": [
            "The orange is flexing its vitamin C like a superhero cape — delivering immune support and collagen-boosting flavonoids in every juicy slice! Squeeze the day and give your immune system an instant upgrade.\n\n👉 Share this with someone who's feeling run down! 🍊\n💬 Fresh orange slices or fresh-squeezed juice? Let us know below!\n\n#fruitytoon #orange #fruits #healthyeating #nutrition #animation #cartoon #funny #shorts #reels #wellness #foodfacts",
            "Bright, zesty, and loaded with hesperidin to support optimal blood flow and heart health. Keep the sniffles away and your energy high with fresh citrus power.\n\n👉 Tag a citrus lover who needs a boost today!\n💬 Drop an 🍊 if oranges are always in your kitchen!\n\n#fruitytoon #orange #fruits #healthyeating #nutrition #animation #cartoon #funny #shorts #reels #wellness #foodfacts"
        ]
    },
    "watermelon": {
        "name": "Watermelon",
        "type": "fruit",
        "emoji": "🍉",
        "nutrients": "citrulline amino acids, lycopene, vitamin A, and potassium",
        "benefits": "delivers deep hydration, speeds post-workout muscle recovery, and refreshes blood circulation",
        "titles": [
            "The Watermelon's Hilarious Ted Talk on Pure Hydration 🍉💧",
            "When Watermelon Realizes It's 92% Delicious Water! 🍉✨",
            "Why Watermelon is the Ultimate Muscle Recovery Secret 🍉🏃",
            "The Watermelon's Refreshing Rant on Summer Vibes 🍉☀️"
        ],
        "descriptions": [
            "At 92% water and packed with citrulline and lycopene, watermelon is practically a tasty sports drink grown on a vine! Soothe sore muscles, hydrate every cell, and enjoy pure summer sweetness.\n\n👉 Tag your workout partner who needs to recover faster! 🍉\n💬 Do you eat your watermelon with a sprinkle of salt or plain? Tell us below!\n\n#fruitytoon #watermelon #fruits #healthyeating #nutrition #animation #cartoon #funny #shorts #reels #wellness #foodfacts"
        ]
    },
    "avocado": {
        "name": "Avocado",
        "type": "fruit",
        "emoji": "🥑",
        "nutrients": "monounsaturated oleic fats, potassium, lutein, and folate",
        "benefits": "supports heart health, powers brain cognition, keeps you full for hours, and aids nutrient absorption",
        "titles": [
            "The Avocado's Smooth Talk on Good Fats vs Bad Fats 🥑😎",
            "When the Avocado Explains Why It Belongs on Everything! 🥑🍞",
            "Why the Creamy Avocado is the Ultimate Brain Fuel 🥑🧠",
            "The Avocado's Funny Confession: Yes, I Am a Fruit! 🥑😂"
        ],
        "descriptions": [
            "Creamy, dreamy, and packed with oleic monounsaturated fatty acids: avocados prove that the right fats are actually your heart's best ally! Keep yourself full, your mind sharp, and your meals next level.\n\n👉 Tag an avocado toast addict! 🥑\n💬 Guacamole or sliced on toast? How do you love your avo?\n\n#fruitytoon #avocado #fruits #healthyeating #nutrition #animation #cartoon #funny #shorts #reels #wellness #foodfacts"
        ]
    },
    "blueberry": {
        "name": "Blueberry",
        "type": "fruit",
        "emoji": "🫐",
        "nutrients": "anthocyanins, pterostilbene, vitamin C, and manganese",
        "benefits": "shields brain neurons, sharpens memory recall, and fights oxidative inflammation",
        "titles": [
            "The Blueberry Brags About Being the Ultimate Brain Food 🫐🧠",
            "When the Tiny Blueberry Realizes It's an Antioxidant Bomb! 🫐💥",
            "Why Blueberries Are Secretly the Smartest Food on Earth 🫐✨"
        ],
        "descriptions": [
            "Small berry, colossal antioxidant firepower! Blueberries are packed with anthocyanins that cross the blood-brain barrier to sharpen memory and protect against cellular stress. Snack smart!\n\n👉 Tag someone who needs brain food for work or study! 🫐\n💬 Pancakes, oatmeal, or straight from the box? How do you eat them?\n\n#fruitytoon #blueberry #fruits #healthyeating #nutrition #animation #cartoon #funny #shorts #reels #wellness #foodfacts"
        ]
    },
    "spinach": {
        "name": "Spinach",
        "type": "vegetable",
        "emoji": "🥬",
        "nutrients": "plant iron, dietary nitrates, folate, and vitamins A, C, and K",
        "benefits": "fuels muscle contraction, enhances stamina, supports bone density, and powers natural energy",
        "titles": [
            "The Spinach Explains Why Popeye Was 100% Right! 🥬💪",
            "When the Spinach Leaves Show Off Their Iron Superpower! 🥬⚡",
            "Why Spinach Shrinks in the Pan but Expands Your Energy 🥬😂"
        ],
        "descriptions": [
            "Popeye was ahead of his time — spinach is stacked with iron, lutein, and dietary nitrates that support stamina and healthy blood pressure without the caffeine crash. Eat the greens, skip the drama!\n\n👉 Tag your gym buddy who needs more leafy greens! 🥬\n💬 Raw in salads or cooked with garlic? Vote below!\n\n#fruitytoon #spinach #vegetables #healthyeating #nutrition #animation #cartoon #funny #shorts #reels #wellness #foodfacts"
        ]
    },
    "cucumber": {
        "name": "Cucumber",
        "type": "vegetable",
        "emoji": "🥒",
        "nutrients": "silica, cucurbitacins, potassium, and vitamins K & C",
        "benefits": "cools body temperature, hydrates connective tissue, and promotes glowing, clear skin",
        "titles": [
            "The Cucumber's Chill Guide to Staying Cool Under Pressure 🥒❄️",
            "When the Cucumber Reveals Why It's 95% Hydration 🥒💧",
            "Why Being as Cool as a Cucumber is a Medical Fact! 🥒😎"
        ],
        "descriptions": [
            "Literally cool as a cucumber: with 95% structured water and skin-loving silica, this refreshing veggie keeps inflammation down and hydration all the way up. Crisp, calming, and deeply hydrating!\n\n👉 Share this with someone who needs to drink more water! 🥒\n💬 Pickles or fresh slices? What's your pick?\n\n#fruitytoon #cucumber #vegetables #healthyeating #nutrition #animation #cartoon #funny #shorts #reels #wellness #foodfacts"
        ]
    },
    "garlic": {
        "name": "Garlic",
        "type": "vegetable",
        "emoji": "🧄",
        "nutrients": "allicin, diallyl disulfide, sulfur compounds, and selenium",
        "benefits": "supercharges immune defenses, supports healthy blood pressure, and promotes heart health",
        "titles": [
            "Garlic Tries to Fix Your Immunity (and Your Love Life) 🧄😂",
            "When the Garlic Clove Declares War on Cold Season! 🧄🛡️",
            "Why Garlic is Nature's Most Powerful Herbal Bodyguard 🧄💥"
        ],
        "descriptions": [
            "Garlic might be intense on the breath, but its allicin sulfur compounds are legendary for defending immunity and supporting healthy cardiovascular blood flow. Flavorful, potent, and totally unbeatable!\n\n👉 Tag a garlic lover who measures with their heart! 🧄\n💬 How many cloves is 'too many'? The answer is never! Debate below!\n\n#fruitytoon #garlic #vegetables #healthyeating #nutrition #animation #cartoon #funny #shorts #reels #wellness #foodfacts"
        ]
    },
    "pineapple": {
        "name": "Pineapple",
        "type": "fruit",
        "emoji": "🍍",
        "nutrients": "bromelain digestive enzyme, vitamin C, and manganese",
        "benefits": "aids protein digestion, eases joint soreness, and delivers tropical immune energy",
        "titles": [
            "When the Pineapple Refuses to Be Just a Pizza Topping! 🍍👑",
            "The Pineapple's Sweet Guide to Fixing Your Digestion 🍍✨",
            "Why Pineapple Literally Digests Your Meals for You 🍍💪"
        ],
        "descriptions": [
            "Pineapple isn't just crowned for looks — it carries bromelain, a rare enzyme that breaks down proteins and soothes post-meal bloating and inflammation. Tropical, tangy, and amazing for your gut!\n\n👉 Tag someone who puts pineapple on pizza! 🍍\n💬 Does pineapple belong on pizza or should it be banned? Sound off below!\n\n#fruitytoon #pineapple #fruits #healthyeating #nutrition #animation #cartoon #funny #shorts #reels #wellness #foodfacts"
        ]
    },
    "beet": {
        "name": "Beet",
        "type": "vegetable",
        "emoji": "🔴",
        "nutrients": "dietary nitrates, betalains, folate, and potassium",
        "benefits": "boosts nitric oxide for blood flow, enhances athletic stamina, and supports liver health",
        "titles": [
            "The Beet Explains Its Incredible Blood-Pressure Magic! 🔴⚡",
            "When the Beetroot Unlocks Your Secret Stamina Gear! 🔴🏃",
            "Why the Humble Beet Can Outperform Energy Drinks 🔴💪"
        ],
        "descriptions": [
            "Dietary nitrates in beets convert straight into nitric oxide, opening up blood vessels to boost oxygen flow, stamina, and heart health. Earthy, vibrant, and pure endurance fuel!\n\n👉 Tag someone who needs an athletic edge! 🔴\n💬 Beet juice or roasted beets? What's your favorite?\n\n#fruitytoon #beet #vegetables #healthyeating #nutrition #animation #cartoon #funny #shorts #reels #wellness #foodfacts"
        ]
    },
    "lemon": {
        "name": "Lemon",
        "type": "fruit",
        "emoji": "🍋",
        "nutrients": "citric acid, vitamin C, limonene, and citrus bioflavonoids",
        "benefits": "stimulates digestive enzymes, supports kidney health, and delivers vibrant alkalinity",
        "titles": [
            "The Lemon's Sour Wake-Up Call for Tired Humans! 🍋☀️",
            "When the Lemon Drops the Real Truth on Digestion 🍋💧",
            "Why Starting Your Morning with Lemon Changes Everything! 🍋✨"
        ],
        "descriptions": [
            "Tart, zesty, and loaded with citric acid and vitamin C: lemons kickstart digestive enzymes and give your body an instant refreshing reset. Squeeze a little sunshine into your routine!\n\n👉 Share this with someone who needs morning motivation! 🍋\n💬 Warm lemon water in the morning: yes or no? Tell us below!\n\n#fruitytoon #lemon #fruits #healthyeating #nutrition #animation #cartoon #funny #shorts #reels #wellness #foodfacts"
        ]
    },
    "mango": {
        "name": "Mango",
        "type": "fruit",
        "emoji": "🥭",
        "nutrients": "mangiferin, vitamins A & C, digestive amylases, and fiber",
        "benefits": "supports immune resilience, protects eyesight, and aids smooth digestion",
        "titles": [
            "The King of Fruits Speaks: Why Mango is Pure Gold! 🥭👑",
            "When the Mango Proves It's as Healthy as It is Sweet 🥭✨",
            "The Mango's Tropical Guide to Glowing Skin and Good Health 🥭💛"
        ],
        "descriptions": [
            "They don't call mango the king of fruits for nothing! Packed with mangiferin antioxidants, digestive enzymes, and vitamin A, this sweet tropical wonder loves your skin and immune system.\n\n👉 Tag a certified mango lover! 🥭\n💬 What's your absolute favorite variety of mango? Drop it below!\n\n#fruitytoon #mango #fruits #healthyeating #nutrition #animation #cartoon #funny #shorts #reels #wellness #foodfacts"
        ]
    },
    "grapes": {
        "name": "Grapes",
        "type": "fruit",
        "emoji": "🍇",
        "nutrients": "resveratrol, polyphenols, vitamin K, and potassium",
        "benefits": "protects heart arteries, shields against oxidative aging, and hydrates cells",
        "titles": [
            "When Grapes Reveal Their Secret Resveratrol Superpower! 🍇❤️",
            "The Grapes' Hilarious Guide to Living Forever 🍇✨",
            "Why Grapes Are Tiny Superhero Spheres for Your Heart 🍇💪"
        ],
        "descriptions": [
            "Grapes carry resveratrol and heart-loving polyphenols in their skin, giving your blood vessels antioxidant protection with every pop! Bite-sized, sweet, and wonderfully good for you.\n\n👉 Tag someone who could finish a whole bunch of grapes in one sitting! 🍇\n💬 Green, red, or black grapes? Pick your winner below!\n\n#fruitytoon #grapes #fruits #healthyeating #nutrition #animation #cartoon #funny #shorts #reels #wellness #foodfacts"
        ]
    }
}


def extract_video_subject(video_name: str) -> dict:
    """
    Intelligently identifies the fruit/vegetable and topic from the video filename or path.
    Example: 'Apple_explaining_health_benefits_202608230045.mp4' -> Apple metadata
    """
    clean_name = os.path.basename(video_name or "").lower()
    clean_name = re.sub(r'[_\-\.]', ' ', clean_name)

    # Search known fruits/veggies in filename
    for key, data in FRUIT_VEG_DATABASE.items():
        pattern = r'\b' + re.escape(key) + r'\b'
        if re.search(pattern, clean_name) or key in clean_name:
            return data

    # Fallback to general FruityToon fruit & veggie character
    return {
        "name": "Fruit & Veggies",
        "type": "superfood",
        "emoji": "🍎🥦",
        "nutrients": "essential vitamins, minerals, and dietary antioxidants",
        "benefits": "boosts natural vitality, supports daily immune defenses, and keeps your body thriving",
        "titles": [
            "When Your Healthy Snacks Secretly Team Up! 🍎🥦✨",
            "The FruityToon Guide to Eating Clean Without the Boredom! 🥕🍌",
            "Why Whole Foods Are Nature's Ultimate Lifehack! 🍓🥑💪",
            "The Hilarious Truth About Why We Need More Greens! 🥬🍎😂"
        ],
        "descriptions": [
            "Eating whole fruits and veggies isn't about boring diets — it's about giving your body the clean, cellular energy it needs to thrive every single day! Fill your plate with color, ditch the artificial slump, and feel the difference.\n\n👉 Tag a friend who needs more fruits and veggies! 🥕\n💬 What's the one healthy food you could eat every single day? Tell us below!\n\n#fruitytoon #healthyeating #nutrition #fruits #vegetables #animation #cartoon #funny #shorts #reels #wellness #foodfacts"
        ]
    }


def get_already_published():
    """Load list of published videos from log file."""
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
    """Save publication record with timestamp to JSON."""
    published = get_already_published()
    published.append({
        "video_name": video_name,
        "metadata": metadata
    })
    with open(PUBLISHED_LOG, 'w', encoding='utf-8') as f:
        json.dump(published, f, indent=4)


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
    Enforces strict publishing policy for YouTube:
    1. NEVER publish more than ONCE a day.
    2. Publish ONLY on ALTERNATE DAYS (every 2 days: >= 2 days gap since last publish).
    """
    today = datetime.datetime.now(datetime.timezone.utc).date()
    last_date = get_last_youtube_publish_date()

    if last_date is None:
        return True, "No previous YouTube upload found. Eligible to publish today."

    days_diff = (today - last_date).days

    if days_diff == 0:
        return False, f"YouTube has ALREADY published today ({last_date}). Policy: Maximum once a day."

    if days_diff == 1:
        next_date = last_date + datetime.timedelta(days=2)
        return False, f"YouTube published yesterday ({last_date}). Policy: Alternate days only (every 2 days). Next publish on or after {next_date}."

    if days_diff < 0:
        return False, f"Clock anomaly: Last YouTube publish recorded in future ({last_date}). Skipping YouTube upload."

    return True, f"Last YouTube publish was {days_diff} days ago ({last_date}). Alternate day requirement satisfied."


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
    published = [item["video_name"] for item in get_already_published()]
    all_videos = sorted(glob.glob(os.path.join(PROCESSED_DIR, "*.mp4")))

    if specific_video:
        if os.path.exists(specific_video):
            vid_path = specific_video
            name = os.path.basename(specific_video)
        else:
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


# ==============================================================================
# TARGETED CAPTION GENERATION (Food-Specific & Verified)
# ==============================================================================

def generate_caption(video_name=None, video_path=None):
    """
    Generates a properly matched, high-converting title and description
    based on the exact fruit or vegetable in the video.
    """
    target_video = video_name or (os.path.basename(video_path) if video_path else "")
    subject = extract_video_subject(target_video)

    food_name = subject.get("name", "Fruit")
    food_emoji = subject.get("emoji", "🍎")
    nutrients = subject.get("nutrients", "vitamins, minerals, and antioxidants")
    benefits = subject.get("benefits", "healthy digestion, strong immunity, and sustained clean energy")

    fallback_titles = subject.get("titles") or [f"When the {food_name} Realizes Its True Superpower! {food_emoji}"]
    fallback_descriptions = subject.get("descriptions") or [
        f"The {food_name.lower()} is out here delivering clean vitamins and natural energy for your daily wellness. Eat your colors and feel amazing!\n\n👉 Tag a friend who needs more fruits and veggies!\n💬 Comment your favorite healthy snack below!\n\n#fruitytoon #{food_name.lower()} #healthyeating #nutrition #fruits #animation #cartoon #funny #shorts #reels #wellness"
    ]

    api_key = os.getenv("POLLINATIONS_API_KEY")
    model = os.getenv("AI_MODEL", "gemini-fast")

    if not api_key:
        print(f"ℹ️  Using verified {food_name} database templates (no POLLINATIONS_API_KEY).")
        return random.choice(fallback_titles), random.choice(fallback_descriptions)

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
        return random.choice(fallback_titles), random.choice(fallback_descriptions)

    except Exception as e:
        print(f"⚠️  Notice: AI caption generation fell back to {food_name} template ({e})")
        return random.choice(fallback_titles), random.choice(fallback_descriptions)


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
