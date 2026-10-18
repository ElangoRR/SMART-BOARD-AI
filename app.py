import os
import time
import random
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from keyword_extractor import KeywordExtractor
from image_scraper import ImageScraper
from utils import setup_directories, load_cache, save_cache, cleanup_old_images, IMAGE_FOLDER

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Initialize components
setup_directories()
extractor = KeywordExtractor()
scraper = ImageScraper()

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory('css', filename)

@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory('js', filename)

@app.route('/api/extract-keywords', methods=['POST'])
def extract_keywords():
    data = request.json
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
    data = request.json
    keyword = data.get('keyword', '').strip()
    
    if not keyword:
        return jsonify({"error": "No keyword provided"}), 400

    start_time = time.time()
    
    # 1. Check Cache
    cache = load_cache()
    if keyword in cache:
        cached_data = cache[keyword]
        # Verify file exists
        if os.path.exists(cached_data['local_path'].lstrip('/')):
            cached_data['cached'] = True
            cached_data['elapsed'] = round(time.time() - start_time, 3)
            return jsonify(cached_data)
        else:
            # Invalid cache entry
            del cache[keyword]

    # 2. Scrape URL
    image_url, source = scraper.get_image_url(keyword)
    
    if not image_url:
        return jsonify({"error": "no_image_found", "keyword": keyword}), 404

    # 3. Download Image
    filename, error = scraper.download_image(image_url, keyword)
    
    if error:
        return jsonify({"error": f"Download failed: {error}", "keyword": keyword}), 500

    # 4. Save to Cache
    local_path = f"/{IMAGE_FOLDER}/{filename}"
    serve_url = f"/images/{filename}"
    
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
    
    # Cleanup old images periodically
    if random.random() < 0.1: # 10% chance
        cleanup_old_images()

    return jsonify(result)

@app.route('/images/<filename>')
def serve_image(filename):
    return send_from_directory(IMAGE_FOLDER, filename)

@app.route('/api/download-image', methods=['POST'])
def download_image_endpoint():
    data = request.json
    
    # If keyword provided, run get-image flow first
    if 'keyword' in data:
        # We can reuse the logic by calling the function internally or just redirecting logic
        # For simplicity, let's assume the frontend calls get-image first and passes the serve_url or filename here
        # But the requirement says: "if keyword given, call get-image flow"
        
        # Mock request for internal call
        with app.test_request_context(json={'keyword': data['keyword']}):
            res = get_image()
            if res.status_code != 200:
                return res
            json_data = res.get_json()
            filename = os.path.basename(json_data['serve_url'])
            return jsonify({
                "serve_url": json_data['serve_url'],
                "download_url": f"/download/{filename}"
            })

    # If image_url provided (external), we need to download it first
    if 'image_url' in data:
        url = data['image_url']
        # Generate a temp keyword or name
        filename, error = scraper.download_image(url, "downloaded_image")
        if error:
            return jsonify({"error": error}), 500
        return jsonify({
            "serve_url": f"/images/{filename}",
            "download_url": f"/download/{filename}"
        })

    return jsonify({"error": "Missing keyword or image_url"}), 400

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(IMAGE_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)