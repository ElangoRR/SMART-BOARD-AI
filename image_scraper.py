import requests
import os
import time
import random
from bs4 import BeautifulSoup
from utils import safe_filename, IMAGE_FOLDER

# Dual import for ddgs / duckduckgo_search
try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None

class ImageScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def get_image_url(self, keyword):
        """
        Try to retrieve an image URL across multiple search strategies.
        Returns: (url, source_name) or (None, None)
        """
        # 1. DuckDuckGo / ddgs
        try:
            url = self._scrape_duckduckgo(keyword)
            if url:
                return url, "DuckDuckGo"
        except Exception as e:
            print(f"DuckDuckGo search error for '{keyword}': {e}")

        # 2. Bing Images Scraper
        try:
            url = self._scrape_bing(keyword)
            if url:
                return url, "Bing"
        except Exception as e:
            print(f"Bing search error for '{keyword}': {e}")

        # 3. Unsplash Fallback
        try:
            url = self._scrape_unsplash_fallback(keyword)
            if url:
                return url, "Unsplash"
        except Exception as e:
            print(f"Unsplash search error for '{keyword}': {e}")

        # 4. Open CDN / Pollinations Fallback
        try:
            url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(keyword)}?width=1280&height=720&nologo=true"
            return url, "Pollinations AI"
        except Exception:
            pass

        return None, None

    def _scrape_duckduckgo(self, keyword):
        """Query DuckDuckGo using ddgs or duckduckgo_search."""
        if DDGS is None:
            return None
        with DDGS() as ddgs:
            results = list(ddgs.images(keyword, max_results=1))
            if results and len(results) > 0:
                return results[0].get('image')
        return None

    def _scrape_bing(self, keyword):
        """Scrape Bing Images for a direct image URL."""
        import json
        url = f"https://www.bing.com/images/search?q={requests.utils.quote(keyword)}&first=1"
        res = self.session.get(url, timeout=5)
        if res.status_code != 200:
            return None

        soup = BeautifulSoup(res.text, 'html.parser')
        for a in soup.find_all('a', class_='iusc'):
            try:
                m = json.loads(a.get('m', '{}'))
                if 'murl' in m and m['murl'].startswith('http'):
                    return m['murl']
            except Exception:
                continue

        # Thumbnail fallback if full image not parsed
        for img in soup.find_all('img', class_='mimg'):
            src = img.get('src') or img.get('data-src')
            if src and src.startswith('http'):
                return src

        return None

    def _scrape_unsplash_fallback(self, keyword):
        """Scrape Unsplash photos search page."""
        url = f"https://unsplash.com/s/photos/{requests.utils.quote(keyword)}"
        res = self.session.get(url, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for img in soup.find_all('img'):
                src = img.get('src', '')
                if 'images.unsplash.com' in src and 'profile' not in src:
                    return src.split('?')[0] + "?w=1080&q=80"
        return None

    def download_image(self, url, keyword):
        """
        Download image from URL and save to IMAGE_FOLDER.
        Returns: (local_filename, error_message)
        """
        try:
            os.makedirs(IMAGE_FOLDER, exist_ok=True)
            res = self.session.get(url, stream=True, timeout=8)
            if res.status_code != 200:
                return None, f"HTTP status {res.status_code}"

            content_type = res.headers.get('Content-Type', '').lower()
            ext = 'jpg'
            if 'png' in content_type:
                ext = 'png'
            elif 'gif' in content_type:
                ext = 'gif'
            elif 'webp' in content_type:
                ext = 'webp'

            filename = f"{safe_filename(keyword)}_{int(time.time())}.{ext}"
            save_path = os.path.join(IMAGE_FOLDER, filename)

            with open(save_path, 'wb') as f:
                for chunk in res.iter_content(chunk_size=4096):
                    if chunk:
                        f.write(chunk)

            return filename, None
        except Exception as e:
            return None, str(e)
