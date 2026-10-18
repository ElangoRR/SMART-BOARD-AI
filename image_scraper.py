import requests
import os
import time
import random
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from utils import safe_filename, IMAGE_FOLDER

class ImageScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })

    def get_image_url(self, keyword):
        """
        Try to get an image URL from multiple sources in priority order.
        Returns: (url, source_name) or (None, None)
        """
        # 1. DuckDuckGo
        try:
            url = self._scrape_duckduckgo(keyword)
            if url: return url, "DuckDuckGo"
        except Exception as e:
            print(f"DDG failed for {keyword}: {e}")

        # 2. Bing
        try:
            url = self._scrape_bing(keyword)
            if url: return url, "Bing"
        except Exception as e:
            print(f"Bing failed for {keyword}: {e}")

        # 3. Unsplash Fallback
        try:
            url = self._scrape_unsplash_fallback(keyword)
            if url: return url, "Unsplash"
        except Exception as e:
            print(f"Unsplash failed for {keyword}: {e}")

        return None, None

    def _scrape_duckduckgo(self, keyword):
        """Use duckduckgo_search library."""
        with DDGS() as ddgs:
            # max_results=1 to get the first one
            results = list(ddgs.images(keyword, max_results=1))
            if results:
                return results[0].get('image')
        return None

    def _scrape_bing(self, keyword):
        """Scrape Bing Images HTML."""
        url = f"https://www.bing.com/images/search?q={keyword}&first=1"
        res = self.session.get(url, timeout=3)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Bing stores image URLs in murl inside a.iusc attribute (JSON string)
        # Or simpler: look for img tags with class 'mimg' (thumbnails) or 'iusc'
        # Parsing 'iusc' is more reliable for full images
        import json
        
        for a in soup.find_all('a', class_='iusc'):
            try:
                m = json.loads(a['m'])
                if 'murl' in m:
                    return m['murl']
            except:
                continue
        return None

    def _scrape_unsplash_fallback(self, keyword):
        """
        Unsplash source is deprecated but we can try the search URL 
        or a direct redirect service if available.
        Using a known working redirect pattern or scraping the search page.
        """
        # Method A: Scrape Unsplash Search
        url = f"https://unsplash.com/s/photos/{keyword}"
        res = self.session.get(url, timeout=3)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            # Find first image in the grid
            # Unsplash structure changes, but usually img with specific classes or in figure
            # Look for images with 'images.unsplash.com' in src
            for img in soup.find_all('img'):
                src = img.get('src', '')
                if 'images.unsplash.com' in src and 'profile' not in src:
                    # Get a larger version by manipulating URL parameters if needed
                    # usually they have ?w=...
                    return src.split('?')[0] + "?w=1080&q=80"
        return None

    def download_image(self, url, keyword):
        """
        Download image from URL and save to disk.
        Returns: (local_filename, error_message)
        """
        try:
            # Head request first to check content type/size if possible
            try:
                head = self.session.head(url, timeout=3, allow_redirects=True)
                if 'image' not in head.headers.get('Content-Type', ''):
                    # Some servers don't support HEAD or return wrong type, proceed with caution
                    pass
                if int(head.headers.get('Content-Length', 0)) > 5 * 1024 * 1024: # 5MB limit
                    return None, "Image too large"
            except:
                pass

            # GET request
            res = self.session.get(url, stream=True, timeout=5)
            if res.status_code != 200:
                return None, f"Status {res.status_code}"

            # Determine extension
            content_type = res.headers.get('Content-Type', '')
            ext = 'jpg'
            if 'png' in content_type: ext = 'png'
            elif 'gif' in content_type: ext = 'gif'
            elif 'webp' in content_type: ext = 'webp'
            elif 'jpeg' in content_type: ext = 'jpg'

            filename = f"{safe_filename(keyword)}_{int(time.time())}.{ext}"
            save_path = os.path.join(IMAGE_FOLDER, filename)

            with open(save_path, 'wb') as f:
                for chunk in res.iter_content(1024):
                    f.write(chunk)
            
            return filename, None

        except Exception as e:
            return None, str(e)
