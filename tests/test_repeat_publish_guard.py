"""Regression guards against re-publishing the same video every run.

Covers the Oct 2026 incident where the pipeline posted one video for
8+ consecutive days because (a) the state log never persisted and
(b) exact filename matching missed Unicode ellipsis variants.

Run with:  python -m unittest discover -s tests -v
Requires only the standard library.
"""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import daily_publisher
import google_drive_fetch
from upload import upload_facebook


def load_merge_module():
    spec = importlib.util.spec_from_file_location(
        "merge_publish_state",
        REPO_ROOT / "scripts" / "merge_publish_state.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_log(path, names):
    with open(path, "w", encoding="utf-8") as f:
        json.dump([{"video_name": n, "metadata": {}} for n in names], f)


class TestCanonicalKeys(unittest.TestCase):
    def test_ellipsis_variants_map_to_same_key(self):
        variants = [
            "Animated_fruit_characters_speaki\u2026_20261023171439.mp4",  # … U+2026
            "Animated_fruit_characters_speaki�_20261023171439.mp4",  # U+FFFD
            "Animated_fruit_characters_speaki._20261023171439.mp4",  # ascii dot
            "animated_fruit_characters_speaki___20261023171439.MP4",  # case + separators
        ]
        keys = {daily_publisher.normalize_video_key(v) for v in variants}
        self.assertEqual(len(keys), 1, f"variants diverged: {keys}")

    def test_distinct_videos_have_distinct_keys(self):
        a = daily_publisher.normalize_video_key(
            "Animated_fruit_characters_talkin\u2026_20261016222124.mp4")
        b = daily_publisher.normalize_video_key(
            "Animated_fruit_characters_speaki\u2026_20261023171439.mp4")
        self.assertNotEqual(a, b)

    def test_fetch_and_publisher_agree(self):
        name = "Animated_fruit_characters_speaki\u2026_20261023171439.mp4"
        self.assertEqual(
            daily_publisher.normalize_video_key(name),
            google_drive_fetch.normalize_video_key(name),
        )


class TestSelectionCooldown(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.videos_dir = Path(self.tmp.name) / "Processed_Videos"
        self.videos_dir.mkdir()
        self.files = [
            "Apple_explaining_health_benefits_202608230045.mp4",
            "Banana_dancing_20261001010101.mp4",
            "Cherry_singing_20261002020202.mp4",
        ]
        for name in self.files:
            (self.videos_dir / name).write_bytes(b"\x00")
        self.history = Path(self.tmp.name) / "history.json"
        self.published = Path(self.tmp.name) / "published_videos.json"

        self._orig = (
            daily_publisher.PROCESSED_DIR,
            daily_publisher.HISTORY_LOG,
            daily_publisher.PUBLISHED_LOG,
        )
        daily_publisher.PROCESSED_DIR = str(self.videos_dir)
        daily_publisher.HISTORY_LOG = str(self.history)
        daily_publisher.PUBLISHED_LOG = str(self.published)
        self.addCleanup(self._restore)

    def _restore(self):
        (daily_publisher.PROCESSED_DIR,
         daily_publisher.HISTORY_LOG,
         daily_publisher.PUBLISHED_LOG) = self._orig

    def test_does_not_repick_just_published_video(self):
        # Newest record is Cherry (just published); it must not be picked again.
        write_log(self.history, [self.files[0], self.files[1], self.files[2]])
        write_log(self.published, [self.files[0], self.files[1], self.files[2]])
        _, name = daily_publisher.select_video()
        self.assertNotEqual(name, self.files[2])
        # All three inside cooldown -> oldest (Apple) wins the LRU fallback.
        self.assertEqual(name, self.files[0])

    def test_unpublished_video_wins(self):
        write_log(self.history, [self.files[0]])
        write_log(self.published, [self.files[0]])
        _, name = daily_publisher.select_video()
        self.assertEqual(name, self.files[1])  # first unpublished, sorted


class TestStateMerge(unittest.TestCase):
    def test_merge_keeps_local_and_remote_records(self):
        # Local run record ("b.mp4") must survive a pull that brought
        # a remote record; neither side may be dropped (Oct 2026 state loss).
        merge = load_merge_module()
        with tempfile.TemporaryDirectory() as tmp:
            merge.BASE_DIR = Path(tmp)
            backup = Path(tmp) / "backup"
            backup.mkdir()
            write_log(Path(tmp) / "published_videos.json", ["b.mp4"])
            write_log(backup / "published_videos.json", ["a.mp4", "b.mp4"])
            merge.merge_logs("published_videos.json", str(backup))
            merged = json.loads(
                (Path(tmp) / "published_videos.json").read_text(encoding="utf-8"))
            names = sorted(r["video_name"] for r in merged)
            self.assertEqual(names, ["a.mp4", "b.mp4"])


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


RATE_LIMIT_BODY = {
    "error": {
        "message": "(#4) Application request limit reached",
        "type": "OAuthException",
        "code": 4,
    }
}


class TestFacebookTransientRetry(unittest.TestCase):
    def test_start_phase_rate_limit_is_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "clip.mp4"
            video.write_bytes(b"\x00" * 1024)
            calls = []

            def fake_post(url, data=None, headers=None, timeout=None, **kwargs):
                calls.append(url)
                if "video_reels" in url and data and data.get("upload_phase") == "start":
                    if len([c for c in calls if c == url]) == 1:
                        return FakeResponse(400, RATE_LIMIT_BODY)
                    return FakeResponse(200, {
                        "video_id": "vid1", "upload_url": "https://fb.upload/x"})
                if url == "https://fb.upload/x":
                    return FakeResponse(200, {})
                return FakeResponse(200, {"success": True})

            env = {"FACEBOOK_ACCESS_TOKEN": "token1234567890",
                   "FACEBOOK_PAGE_ID": "page1"}
            with mock.patch.dict(os.environ, env), \
                 mock.patch.object(upload_facebook.requests, "post", side_effect=fake_post), \
                 mock.patch.object(upload_facebook.time, "sleep", return_value=None):
                result = upload_facebook.upload_to_facebook(
                    str(video), description="desc", title="title")
            self.assertEqual(result["status"], "success")
            starts = [c for c in calls if "video_reels" in c]
            self.assertGreaterEqual(len(starts), 2,
                                    "rate-limited start phase was not retried")


class TestHybridCaption(unittest.TestCase):
    def test_fallback_caption_carries_seo_keywords(self):
        with mock.patch.dict(os.environ, {"POLLINATIONS_API_KEY": ""}):
            title, desc = daily_publisher.generate_caption(
                video_name="Apple_crunch_20261001010101.mp4")
        self.assertTrue(title and len(title) <= 70)
        self.assertIn("vitamin C", desc)        # nutrient keyword
        self.assertIn("heart wellness", desc)   # benefit keyword
        self.assertIn("#fruitytoon #apple", desc)
        self.assertLessEqual(len(desc), 2200)

    def test_seo_body_inserted_before_hashtags(self):
        out = daily_publisher.build_hybrid_description(
            "Hook line!\n\nCTA here? \U0001F447\n\n#fruitytoon #apple #shorts",
            "Apple", "vitamin C", "supports heart wellness", "apple")
        first_hash = out.index("#")
        self.assertIn("supports heart wellness", out[:first_hash])
        self.assertTrue(out.rstrip().endswith("#shorts"))

    def test_hybrid_builder_adds_tags_when_missing(self):
        out = daily_publisher.build_hybrid_description(
            "Just a hook, no tags.", "Banana", "potassium",
            "supports muscles", "banana")
        self.assertIn("#fruitytoon #banana", out)
        self.assertIn("potassium", out)


if __name__ == "__main__":
    unittest.main()
