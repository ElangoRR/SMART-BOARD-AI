import os
import re
import hashlib
import json
import time
import shutil
from pathlib import Path

# Configuration
IMAGE_FOLDER = 'saved_images'
CACHE_FILE = 'image_cache.json'
MAX_CACHE_SIZE = 500

def setup_directories():
    """Ensure necessary directories exist."""
    if not os.path.exists(IMAGE_FOLDER):
        os.makedirs(IMAGE_FOLDER)

def safe_filename(text):
    """Sanitize text to be safe for filenames."""
    # Remove non-alphanumeric characters except spaces, hyphens, underscores
    s = re.sub(r'[^\w\s-]', '', text).strip().lower()
    # Replace spaces with underscores
    s = re.sub(r'[-\s]+', '_', s)
    return s if s else 'image'

def get_file_hash(file_path, block_size=65536):
    """Calculate SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'rb') as f:
        for block in iter(lambda: f.read(block_size), b''):
            sha256.update(block)
    return sha256.hexdigest()

def load_cache():
    """Load the image cache from JSON."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_cache(cache_data):
    """Save the image cache to JSON."""
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f, indent=2)
    except Exception as e:
        print(f"Error saving cache: {e}")

def cleanup_old_images():
    """Keep only the most recent MAX_CACHE_SIZE images."""
    cache = load_cache()
    if len(cache) <= MAX_CACHE_SIZE:
        return

    # Sort by timestamp (oldest first)
    sorted_items = sorted(cache.items(), key=lambda x: x[1].get('timestamp', 0))
    
    # Items to remove
    to_remove_count = len(cache) - MAX_CACHE_SIZE
    to_remove = sorted_items[:to_remove_count]

    for keyword, data in to_remove:
        local_path = data.get('local_path')
        # Remove file
        if local_path and os.path.exists(local_path.lstrip('/')):
             try:
                 os.remove(local_path.lstrip('/'))
             except OSError:
                 pass
        # Remove from cache
        del cache[keyword]
    
    save_cache(cache)
