"""
Tải model face-api.js về local để dùng nhận diện khuôn mặt offline.
Chạy: python download_models.py
"""
import urllib.request
import os

SAVE_DIR = os.path.join("static", "models")
os.makedirs(SAVE_DIR, exist_ok=True)

BASE = "https://raw.githubusercontent.com/justadudewhohacks/face-api.js/master/weights/"

FILES = [
    "ssd_mobilenetv1_model-weights_manifest.json",
    "ssd_mobilenetv1_model-shard1",
    "face_landmark_68_model-weights_manifest.json",
    "face_landmark_68_model-shard1",
    "face_recognition_model-weights_manifest.json",
    "face_recognition_model-shard1",
    "face_recognition_model-shard2",
]

print(f"[*] Dang tai {len(FILES)} file model ve {SAVE_DIR}/")
print("[*] Kich thuoc: ~18MB, vui long cho...")

for i, filename in enumerate(FILES, 1):
    dest = os.path.join(SAVE_DIR, filename)
    if os.path.exists(dest):
        print(f"  [{i}/{len(FILES)}] Da co: {filename}")
        continue
    url = BASE + filename
    print(f"  [{i}/{len(FILES)}] Dang tai: {filename} ...", end="", flush=True)
    try:
        urllib.request.urlretrieve(url, dest)
        size_kb = os.path.getsize(dest) // 1024
        print(f" OK ({size_kb}KB)")
    except Exception as e:
        print(f" THAT BAI: {e}")

print("\n[DONE] Tat ca model da san sang!")
print(f"[*] Thu muc: {os.path.abspath(SAVE_DIR)}")
