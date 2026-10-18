import os
import re
import hashlib
import json
import time
import shutil
from pathlib import Path

# Base Directory Resolution
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_FOLDER = os.path.join(BASE_DIR, 'saved_images')
CACHE_FILE = os.path.join(BASE_DIR, 'image_cache.json')
MAX_CACHE_SIZE = 500

def setup_directories():
    """Ensure necessary directories exist."""
    try:
        os.makedirs(IMAGE_FOLDER, exist_ok=True)
    except Exception as e:
        print(f"Warning: could not create image directory {IMAGE_FOLDER}: {e}")

def safe_filename(text):
    """Sanitize text to be safe for filenames."""
    s = re.sub(r'[^\w\s-]', '', text).strip().lower()
    s = re.sub(r'[-\s]+', '_', s)
    return s if s else 'image'

def get_file_hash(file_path, block_size=65536):
    """Calculate SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, 'rb') as f:
            for block in iter(lambda: f.read(block_size), b''):
                sha256.update(block)
        return sha256.hexdigest()
    except Exception:
        return None

def load_cache():
    """Load the image cache from JSON safely."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: could not load cache ({e}), initializing empty cache.")
            return {}
    return {}

def save_cache(cache_data):
    """Save the image cache to JSON safely."""
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2)
    except Exception as e:
        print(f"Warning: could not save cache: {e}")

def cleanup_old_images():
    """Keep only the most recent MAX_CACHE_SIZE images."""
    try:
        cache = load_cache()
        if len(cache) <= MAX_CACHE_SIZE:
            return

        sorted_items = sorted(cache.items(), key=lambda x: x[1].get('timestamp', 0))
        to_remove_count = len(cache) - MAX_CACHE_SIZE
        to_remove = sorted_items[:to_remove_count]

        for keyword, data in to_remove:
            local_path = data.get('local_path')
            if local_path:
                full_path = os.path.join(BASE_DIR, local_path.lstrip('/'))
                if os.path.exists(full_path):
                    try:
                        os.remove(full_path)
                    except OSError:
                        pass
            if keyword in cache:
                del cache[keyword]
        
        save_cache(cache)
    except Exception as e:
        print(f"Cleanup error: {e}")
