# SMART BOARD AI - Backend

This is the complete backend for the SMART BOARD AI project. It handles keyword extraction using NLP (spaCy + KeyBERT) and fetches images from the web (DuckDuckGo, Bing, Unsplash) to serve to the frontend.

## Prerequisites

- Python 3.10 or higher
- Internet connection (for image scraping and model downloading)

## Installation

1.  **Create a Virtual Environment** (Recommended):
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Mac/Linux
    source venv/bin/activate
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Download spaCy Model**:
    ```bash
    python -m spacy download en_core_web_sm
    ```

## Running the Server

Start the Flask server:

```bash
python app.py
```

The server will start at `http://localhost:5000`.

## API Endpoints

### 1. Extract Keywords
**POST** `/api/extract-keywords`

Extracts relevant key phrases from a transcript.

**Request:**
```json
{
  "transcript": "The human evolution from ape ancestors to Homo sapiens involved walking on two legs and the discovery of fire."
}
```

**Response:**
```json
{
  "transcript": "...",
  "keywords": [
    {"phrase": "human evolution", "score": 0.85},
    {"phrase": "discovery of fire", "score": 0.78},
    ...
  ],
  "elapsed": 0.12
}
```

### 2. Get Image
**POST** `/api/get-image`

Fetches, downloads, and caches an image for a keyword.

**Request:**
```json
{
  "keyword": "human evolution"
}
```

**Response:**
```json
{
  "keyword": "human evolution",
  "image_url": "https://example.com/image.jpg",
  "local_path": "/saved_images/human_evolution_123456.jpg",
  "serve_url": "/images/human_evolution_123456.jpg",
  "cached": false,
  "elapsed": 1.5
}
```

### 3. Download Image
**POST** `/api/download-image`

Prepares an image for download.

**Request:**
```json
{
  "keyword": "human evolution"
}
```

**Response:**
```json
{
  "serve_url": "/images/human_evolution_123456.jpg",
  "download_url": "/download/human_evolution_123456.jpg"
}
```

## Directory Structure

- `app.py`: Main Flask application.
- `keyword_extractor.py`: NLP logic.
- `image_scraper.py`: Web scraping logic.
- `utils.py`: Helper functions.
- `saved_images/`: Directory where downloaded images are stored.
- `image_cache.json`: JSON file tracking cached images.
