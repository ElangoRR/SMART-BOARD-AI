import os
import time
import random
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from keyword_extractor import KeywordExtractor
from image_scraper import ImageScraper
from utils import setup_directories, load_cache, save_cache, cleanup_old_images, IMAGE_FOLDER, BASE_DIR

app = Flask(__name__)
# Enable CORS for API routes
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Initialize core components
setup_directories()
extractor = KeywordExtractor()
scraper = ImageScraper()

@app.route('/')
def index():
    """Serve the main frontend application."""
    return send_file(os.path.join(BASE_DIR, 'index.html'))

@app.route('/css/<path:filename>')
def serve_css(filename):
    """Serve CSS stylesheets."""
    return send_from_directory(os.path.join(BASE_DIR, 'css'), filename)

@app.route('/js/<path:filename>')
def serve_js(filename):
    """Serve JavaScript files."""
    return send_from_directory(os.path.join(BASE_DIR, 'js'), filename)

@app.route('/images/<path:filename>')
def serve_image(filename):
    """Serve cached or saved images."""
    return send_from_directory(IMAGE_FOLDER, filename)

@app.route('/api/extract-keywords', methods=['POST'])
def extract_keywords():
    """Extract key educational phrases from input transcript."""
    data = request.get_json(silent=True) or {}
    transcript = data.get('transcript', '')

    if not transcript:
        return jsonify({"error": "No transcript provided"}), 400

    start_time = time.time()
    keywords = extractor.extract(transcript)
    elapsed = time.time() - start_time

    return jsonify({
        "transcript": transcript,
        "keywords": keywords,
        "elapsed": round(elapsed, 3)
    })

@app.route('/api/get-image', methods=['POST'])
def get_image():
    """Retrieve an image URL for a given keyword, caching when possible."""
    data = request.get_json(silent=True) or {}
    keyword = data.get('keyword', '').strip()

    if not keyword:
        return jsonify({"error": "No keyword provided"}), 400

    start_time = time.time()

    # 1. Check Cache
    cache = load_cache()
    if keyword in cache:
        cached_data = cache[keyword]
        local_rel = cached_data.get('local_path', '').lstrip('/')
        full_cached_path = os.path.join(BASE_DIR, local_rel)
        if os.path.exists(full_cached_path):
            cached_data['cached'] = True
            cached_data['elapsed'] = round(time.time() - start_time, 3)
            return jsonify(cached_data)
        elif cached_data.get('image_url'):
            # Local file disappeared, but cached remote URL still usable
            cached_data['cached'] = True
            cached_data['serve_url'] = cached_data['image_url']
            cached_data['elapsed'] = round(time.time() - start_time, 3)
            return jsonify(cached_data)

    # 2. Scrape/Search Image URL
    image_url, source = scraper.get_image_url(keyword)

    if not image_url:
        return jsonify({"error": "no_image_found", "keyword": keyword}), 404

    # 3. Attempt Local Download & Cache
    filename, error = scraper.download_image(image_url, keyword)

    if filename:
        local_path = f"/saved_images/{filename}"
        serve_url = f"/images/{filename}"
    else:
        # Fallback to direct external URL if local file save fails (e.g. read-only container)
        local_path = None
        serve_url = image_url

    result = {
        "keyword": keyword,
        "image_url": image_url,
        "local_path": local_path,
        "serve_url": serve_url,
        "source": source,
        "timestamp": time.time(),
        "cached": False,
        "elapsed": round(time.time() - start_time, 3)
    }

    cache[keyword] = result
    save_cache(cache)

    # 10% chance to trigger cache cleanup
    if random.random() < 0.1:
        cleanup_old_images()

    return jsonify(result)

@app.route('/api/download-image', methods=['POST'])
def download_image_endpoint():
    """Prepare an image for client download."""
    data = request.get_json(silent=True) or {}

    if 'keyword' in data:
        with app.test_request_context(json={'keyword': data['keyword']}):
            res = get_image()
            if res.status_code != 200:
                return res
            json_data = res.get_json()
            serve_url = json_data.get('serve_url', '')
            if serve_url.startswith('/images/'):
                filename = os.path.basename(serve_url)
                return jsonify({
                    "serve_url": serve_url,
                    "download_url": f"/download/{filename}"
                })
            else:
                return jsonify({
                    "serve_url": serve_url,
                    "download_url": serve_url
                })

    if 'image_url' in data:
        url = data['image_url']
        filename, error = scraper.download_image(url, "downloaded_image")
        if filename:
            return jsonify({
                "serve_url": f"/images/{filename}",
                "download_url": f"/download/{filename}"
            })
        else:
            return jsonify({
                "serve_url": url,
                "download_url": url
            })

    return jsonify({"error": "Missing keyword or image_url"}), 400

@app.route('/download/<filename>')
def download_file(filename):
    """Serve image as attachment for direct download."""
    return send_from_directory(IMAGE_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)