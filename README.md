# SMART BOARD AI — Speech-Driven Visual Assistant for Classrooms

SMART BOARD AI is a real-time, voice-activated presentation and learning assistant. It captures live spoken audio in the classroom, extracts salient topic phrases using spaCy NLP, and dynamically searches, caches, and projects relevant educational visuals.

---

## Architecture Overview

* **Frontend**:
  * `index.html` — Dual-panel interactive whiteboard interface.
  * `css/styles.css` — Modern glassmorphism UI with responsive animations.
  * `js/script.js` — Web Speech API integration, real-time transcription, keyword tag management, and multi-tier image retrieval.
* **Backend**:
  * `app.py` — Production Flask application serving the web app, static assets, and REST APIs.
  * `keyword_extractor.py` — NLP engine using spaCy (`en_core_web_sm`) noun chunking, named entity recognition (NER), and relevance scoring.
  * `image_scraper.py` — Multi-source image search pipeline (DuckDuckGo/`ddgs`, Bing Image Scraper, Unsplash, Pollinations AI).
  * `utils.py` — File hashing, caching, absolute path resolution, and automated storage management.

---

## Deployment on Render

This repository includes a `render.yaml` Blueprint for zero-configuration deployment on [Render](https://render.com).

### Render Service Settings

* **Environment**: `Python`
* **Python Version**: `3.11.10` (configured in `.python-version` and `render.yaml`)
* **Build Command**:
  ```bash
  pip install --upgrade pip && pip install -r requirements.txt && python -m spacy download en_core_web_sm
  ```
* **Start Command**:
  ```bash
  gunicorn app:app -b 0.0.0.0:$PORT -w 2 --timeout 120
  ```

---

## Local Development Setup

### 1. Create a Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 3. Run Locally

```bash
python app.py
```

The application will be accessible at `http://localhost:5000`.

---

## API Endpoints

### 1. Extract Keywords
* **POST** `/api/extract-keywords`
* **Payload**: `{"transcript": "The solar system consists of the Sun and eight planets orbiting it."}`
* **Response**:
  ```json
  {
    "transcript": "...",
    "keywords": [
      {"phrase": "solar system", "score": 0.85},
      {"phrase": "eight planets", "score": 0.82}
    ],
    "elapsed": 0.02
  }
  ```

### 2. Retrieve Image
* **POST** `/api/get-image`
* **Payload**: `{"keyword": "solar system"}`
* **Response**:
  ```json
  {
    "keyword": "solar system",
    "image_url": "https://example.com/image.jpg",
    "serve_url": "/images/solar_system_123456.jpg",
    "source": "Bing",
    "cached": false,
    "elapsed": 1.2
  }
  ```

### 3. Download Image
* **POST** `/api/download-image`
* **Payload**: `{"keyword": "solar system"}` or `{"image_url": "https://..."}`
* **Response**: `{"serve_url": "...", "download_url": "/download/..."}`
