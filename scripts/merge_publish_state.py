"""
Helper script to safely merge local and backup/remote publication state logs.
Ensures no published video records are lost even if multiple jobs run or git conflicts occur.
"""
import os
import sys
import json
import shutil
from pathlib import Path

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent

def merge_logs(target_name, backup_dir):
    target_path = BASE_DIR / target_name
    backup_path = Path(backup_dir) / target_name

    records = []
    seen = set()

    for p in (target_path, backup_path):
        if p.exists():
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            try:
                                key = json.dumps(item, sort_keys=True)
                            except Exception:
                                key = str(item)
                            if key not in seen:
                                seen.add(key)
                                records.append(item)
            except Exception as e:
                print(f"Notice reading {p}: {e}")

    if records:
        with open(target_path, 'w', encoding='utf-8') as f:
            json.dump(records, f, indent=4)
        print(f"Preserved and merged {len(records)} publication events into {target_name}")


def main():
    backup_dir = sys.argv[1] if len(sys.argv) > 1 else "/tmp/state_backup"
    
    merge_logs("published_videos.json", backup_dir)
    merge_logs("history.json", backup_dir)

    yt_backup = Path(backup_dir) / "youtube_publish_state.json"
    yt_target = BASE_DIR / "youtube_publish_state.json"
    if yt_backup.exists():
        try:
            shutil.copy(yt_backup, yt_target)
            print("Restored youtube_publish_state.json")
        except Exception as e:
            print(f"Notice restoring youtube state: {e}")


if __name__ == "__main__":
    main()
